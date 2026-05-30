"""AppTimer v2 原生窗口版：pywebview + WebView2"""

import sys
import os
import json
import time
import ctypes
import threading
from pathlib import Path
import webview

from .tracker import UsageTracker, fmt_duration, get_desktop_path
from .startup import add_to_startup, remove_from_startup, is_startup_enabled


class _Api:
    """暴露给 pywebview JS 的 API"""

    def __init__(self, tracker):
        self.tracker = tracker

    def get_snapshot(self):
        return self.tracker.get_snapshot()

    def get_trend(self, app, days=7):
        t = self.tracker.get_trend_data(app, days)
        return [{"date": d, "seconds": s} for d, s in t]

    def get_all_dates(self):
        return self.tracker.get_all_dates()

    def get_history(self, date_str):
        return {"report": self.tracker.get_history_report(date_str)}

    def get_category_stats(self):
        return self.tracker.get_category_stats()

    def get_startup_status(self):
        return {"enabled": is_startup_enabled()}

    def save_settings(self, settings):
        self.tracker.save_settings(settings)
        return {"ok": True}

    def save_categories(self, categories):
        self.tracker.save_categories(categories)
        return {"ok": True}

    def save_goals(self, goals):
        self.tracker.save_goals(goals)
        return {"ok": True}

    def set_startup(self, data):
        enabled = data.get("enabled", False)
        ok, err = add_to_startup() if enabled else remove_from_startup()
        return {"ok": ok, "error": err}

    def open_folder(self):
        os.startfile(str(self.tracker.data_dir))
        return {"ok": True}

    def export_pdf(self):
        try:
            path = self.tracker.export_pdf()
            return {"ok": True, "path": path}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def export_csv(self):
        try:
            path = self.tracker.export_csv()
            return {"ok": True, "path": path}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def export_cumulative_csv(self):
        try:
            path = self.tracker.export_cumulative_csv()
            return {"ok": True, "path": path}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def quit(self):
        self.tracker.close()
        os._exit(0)

    def uninstall(self, delete_data=False):
        try:
            ok, err = remove_from_startup()
            if delete_data:
                import shutil
                data_dir = str(self.tracker.data_dir)
                try:
                    shutil.rmtree(data_dir)
                except Exception as e:
                    pass
            self.tracker.close()
            os._exit(0)
        except Exception as e:
            return {"ok": False, "error": str(e)}


_g_mutex = None    # 保持 mutex handle 不被 GC
_g_window = None   # pywebview 窗口引用
_g_tray = None     # pystray Icon 引用


def _make_tray_icon():
    """白色极简时钟图标 — 圆框撑满，细长指针"""
    from PIL import Image, ImageDraw
    sz = 64
    img = Image.new('RGBA', (sz, sz), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = sz // 2, sz // 2
    # 圆框
    draw.ellipse([4, 4, 60, 60], outline=(255, 255, 255, 230), width=2)
    # 时针（12点方向，长细）
    draw.line([cx, cy, cx, 14], fill=(255, 255, 255, 230), width=2)
    # 分针（2点方向，长细）
    draw.line([cx, cy, 49, 23], fill=(255, 255, 255, 210), width=2)
    # 中心点
    draw.ellipse([30, 30, 34, 34], fill=(255, 255, 255, 230))
    return img


def _tray_show(icon=None, item=None):
    """托盘 → 显示窗口（用 Windows API 恢复，不依赖 pywebview）"""
    import ctypes
    hwnd = _find_existing_window()
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    elif _g_window:
        try:
            _g_window.show()
            _g_window.restore()
        except Exception:
            pass


def _tray_exit(icon=None, item=None):
    """托盘 → 退出"""
    global _g_tray
    try:
        _g_tray.stop()
    except Exception:
        pass
    try:
        tracker_global.close()
    except Exception:
        pass
    os._exit(0)


def _init_tray():
    """初始化系统托盘 — 主线程创建，子线程 run，确保图标存活"""
    global _g_tray
    try:
        import pystray
        _g_tray = pystray.Icon(
            'AppTimer',
            _make_tray_icon(),
            '程序使用时间追踪',
            menu=pystray.Menu(
                pystray.MenuItem('显示窗口', _tray_show, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem('退出', _tray_exit),
            )
        )
        # 非 daemon 线程 — 进程退出前一直存活
        t = threading.Thread(target=_g_tray.run, daemon=False)
        t.start()
        time.sleep(0.5)  # 等待图标注册完成
    except Exception:
        import logging
        logging.warning("托盘图标初始化失败")


def _get_frontend_path():
    if getattr(sys, "frozen", False):
        return str(Path(sys._MEIPASS) / "frontend")
    return str(Path(__file__).parent.parent / "frontend" / "dist")


def _find_existing_window():
    """枚举所有窗口找到已有的 AppTimer（包括隐藏窗口）"""
    import ctypes
    result = []
    def enum_cb(hwnd, _):
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            if buf.value == "程序使用时间追踪器 v2.0":
                result.append(hwnd)
        return True
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
    ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    return result[0] if result else None


def _is_duplicate_instance():
    global _g_mutex
    _g_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\AppTimer_SingleInstance")
    if ctypes.windll.kernel32.GetLastError() != 183:
        return False
    # 已有 mutex → 检查是否有活跃窗口
    hwnd = _find_existing_window()
    if hwnd:
        # 找到旧窗口 → 恢复它，当前进程退出
        ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        return True
    # mutex 存在但窗口已死（僵尸进程）→ 强杀后接管
    import subprocess
    my_pid = os.getpid()
    try:
        subprocess.run(
            ["taskkill", "/f", "/im", "AppTimer.exe", "/fi", f"PID ne {my_pid}"],
            capture_output=True, timeout=10)
    except Exception:
        pass
    time.sleep(0.5)
    _g_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\AppTimer_SingleInstance")
    return ctypes.windll.kernel32.GetLastError() == 183


def _call_api(method, args, tracker):
    t = tracker
    if method == "get_snapshot":
        return t.get_snapshot()
    if method == "get_trend":
        return [{"date": d, "seconds": s} for d, s in t.get_trend_data(args.get("app", ""), int(args.get("days", 7)))]
    if method == "get_all_dates":
        return t.get_all_dates()
    if method == "get_history":
        return {"report": t.get_history_report(args.get("date", ""))}
    if method == "get_category_stats":
        return t.get_category_stats()
    if method == "get_startup_status":
        return {"enabled": is_startup_enabled()}
    if method == "save_settings":
        t.save_settings(args)
        return {"ok": True}
    if method == "save_categories":
        t.save_categories(args)
        return {"ok": True}
    if method == "save_goals":
        t.save_goals(args)
        return {"ok": True}
    if method == "set_startup":
        enabled = args.get("enabled", False)
        ok, err = add_to_startup() if enabled else remove_from_startup()
        return {"ok": ok, "error": err}
    if method == "open_folder":
        os.startfile(str(t.data_dir))
        return {"ok": True}
    if method == "export_pdf":
        try:
            path = t.export_pdf()
            return {"ok": True, "path": path}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    if method == "export_csv":
        try:
            path = t.export_csv()
            return {"ok": True, "path": path}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    if method == "export_cumulative_csv":
        try:
            path = t.export_cumulative_csv()
            return {"ok": True, "path": path}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    if method == "quit":
        t.close()
        os._exit(0)
    if method == "uninstall":
        try:
            ok, err = remove_from_startup()
            if args.get("delete_data", False):
                import shutil
                try:
                    shutil.rmtree(str(t.data_dir))
                except Exception:
                    pass
            t.close()
            os._exit(0)
        except Exception as e:
            return {"ok": False, "error": str(e)}
    return {"error": f"unknown: {method}"}


def main():
    if "--install" in sys.argv:
        ok, err = add_to_startup()
        print(f"{'OK' if ok else 'FAIL'}: {err or '已添加'}")
        return
    if "--uninstall" in sys.argv:
        ok, err = remove_from_startup()
        print(f"{'OK' if ok else 'FAIL'}: {err or '已移除'}")
        return
    if _is_duplicate_instance():
        os._exit(0)

    tracker = UsageTracker()
    api = _Api(tracker)

    if is_startup_enabled():
        add_to_startup()

    def loop():
        while tracker.running:
            try:
                tracker.update()
                tracker._consecutive_errors = 0
                time.sleep(2)
            except Exception:
                tracker._consecutive_errors += 1
                time.sleep(min(2 ** tracker._consecutive_errors, 60))

    threading.Thread(target=loop, daemon=True).start()

    # 本地 HTTP 服务：前端静态文件 + API 端点，端口冲突自动换
    frontend_dir = _get_frontend_path()
    port = 17778
    from http.server import HTTPServer, SimpleHTTPRequestHandler

    class _Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/api/"):
                self._handle_api()
            else:
                super().do_GET()

        def do_POST(self):
            if self.path.startswith("/api/"):
                self._handle_api()
            else:
                super().do_POST()

        def _handle_api(self):
            from urllib.parse import parse_qs, urlparse
            method = self.path.split("?")[0].replace("/api/", "")
            # 解析 query 参数
            qs = parse_qs(urlparse(self.path).query)
            args = {k: v[0] for k, v in qs.items()}
            # POST body 覆盖 query 参数
            body_len = int(self.headers.get("Content-Length", 0))
            if body_len > 0:
                body = self.rfile.read(body_len)
                try:
                    args.update(json.loads(body.decode("utf-8")))
                except Exception:
                    try:
                        args.update(json.loads(body.decode("gbk", errors="replace")))
                    except Exception:
                        pass
            try:
                result = _call_api(method, args, tracker)
                data = json.dumps(result if result is not None else {}, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))

    http_server = None
    for _offset in range(100):
        try:
            http_server = HTTPServer(("127.0.0.1", port), _Handler)
            break
        except OSError:
            port += 1

    def _serve():
        import os as _os
        _os.chdir(frontend_dir)
        http_server.serve_forever()

    threading.Thread(target=_serve, daemon=True).start()
    time.sleep(0.3)

    global _g_window
    _g_window = webview.create_window(
        "程序使用时间追踪器 v2.0",
        url=f"http://127.0.0.1:{port}",
        width=900,
        height=680,
        resizable=False,
        text_select=True,
    )

    # 托盘 — 在 webview.start 之前初始化（v1 模式）
    _init_tray()

    # X 按钮 → 最小化（不退出进程，mutex 持续有效）
    def _on_closing():
        _g_window.minimize()
        return False
    _g_window.events.closing += _on_closing

    # 运行时强设窗口白色图标
    def _force_icon():
        import ctypes
        time.sleep(1)
        hwnd = ctypes.windll.user32.FindWindowW(None, "程序使用时间追踪器 v2.0")
        if not hwnd:
            return
        base = os.path.dirname(os.path.abspath(__file__))
        for candidate in [
            os.path.join(base, 'clock_white.ico'),
            os.path.join(os.path.dirname(base), 'clock_white.ico'),
        ]:
            if os.path.exists(candidate):
                hicon = ctypes.windll.user32.LoadImageW(0, candidate, 1, 0, 0, 0x0010)
                if hicon:
                    ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, hicon)
                    ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, hicon)
                break
    threading.Thread(target=_force_icon, daemon=True).start()

    webview.start(debug=False)

    # webview 关闭后清理
    try:
        _g_tray.stop()
    except Exception:
        pass
    tracker.close()


if __name__ == "__main__":
    main()
