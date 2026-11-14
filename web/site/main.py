"""AppTimer v2 入口：内嵌 HTTP 服务 + Edge 无边框窗口"""

import sys
import os
import json
import time
import threading
import subprocess
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

from .tracker import UsageTracker, get_desktop_path
from .startup import add_to_startup, remove_from_startup, is_startup_enabled


class _ApiHandler(SimpleHTTPRequestHandler):
    """单路由：/api/<method>?args"""
    tracker = None

    def do_GET(self):
        if self.path.startswith("/api/"):
            self._api()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self._api()
        else:
            super().do_POST()

    def _api(self):
        import urllib.parse
        path = self.path.split("?")[0]
        method = path.replace("/api/", "")
        qs = urllib.parse.parse_qs(self.path.split("?")[1] if "?" in self.path else "")
        try:
            result = self._call(method, qs)
            data = json.dumps(result, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode("utf-8"))

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            args = json.loads(body)
            method = self.path.split("?")[0].replace("/api/", "")
            result = self._call_post(method, args)
            data = json.dumps(result, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode("utf-8"))

    def _call_post(self, method, args):
        t = self.tracker
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
            import os as _os
            _os.startfile(str(t.data_dir))
            return {"ok": True}
        return {"error": f"unknown method {method}"}

    def _call(self, method, qs):
        t = self.tracker
        if method == "snapshot":
            return t.get_snapshot()
        if method == "trend":
            return [{"date": d, "seconds": s} for d, s in t.get_trend_data(qs.get("app", [""])[0], int(qs.get("days", ["7"])[0]))]
        if method == "dates":
            return t.get_all_dates()
        if method == "history":
            return {"report": t.get_history_report(qs.get("date", [""])[0])}
        if method == "category_stats":
            return t.get_category_stats()
        if method == "startup_status":
            return {"enabled": is_startup_enabled()}
        return {"error": f"unknown method {method}"}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def _get_frontend_dir():
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS if hasattr(sys, "_MEIPASS") else Path(sys.executable).parent)
    else:
        base = Path(__file__).parent.parent / "frontend"
    return str(base / "dist")


from http.server import SimpleHTTPRequestHandler as BaseHandler

class _StaticHandler(_ApiHandler):
    tracker = None
    frontend_dir = ""

    def translate_path(self, path):
        if path.startswith("/api/"):
            return path
        p = path.split("?")[0]
        if p == "/" or p == "":
            return os.path.join(self.frontend_dir, "index.html")
        return os.path.join(self.frontend_dir, p.lstrip("/"))


def _run_server(port, frontend_dir, tracker):
    _StaticHandler.tracker = tracker
    _StaticHandler.frontend_dir = frontend_dir
    server = HTTPServer(("127.0.0.1", port), _StaticHandler)
    server.serve_forever()


def _is_duplicate_instance():
    import ctypes.wintypes
    _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\AppTimerV2_SingleInstance")
    return ctypes.windll.kernel32.GetLastError() == 183


def main():
    if "--install" in sys.argv:
        ok, err = add_to_startup()
        print(f"{'OK' if ok else 'FAIL'}: {err or '已添加自启动'}")
        return
    if "--uninstall" in sys.argv:
        ok, err = remove_from_startup()
        print(f"{'OK' if ok else 'FAIL'}: {err or '已移除自启动'}")
        return
    if _is_duplicate_instance():
        os._exit(0)

    tracker = UsageTracker()

    # 自修复注册表
    if is_startup_enabled():
        add_to_startup()

    # 追踪线程
    def loop():
        while tracker.running:
            try:
                tracker.update()
                tracker._consecutive_errors = 0
                time.sleep(2)
            except Exception as e:
                tracker._consecutive_errors += 1
                backoff = min(2 ** tracker._consecutive_errors, 60)
                time.sleep(backoff)
    threading.Thread(target=loop, daemon=True).start()

    # HTTP 服务器
    frontend_dir = _get_frontend_dir()
    port = 17777
    threading.Thread(target=_run_server, args=(port, frontend_dir, tracker), daemon=True).start()
    time.sleep(0.5)

    # Edge 无边框窗口
    url = f"http://127.0.0.1:{port}"
    edge = _find_edge()

    if edge:
        subprocess.Popen([
            edge,
            f"--app={url}",
            "--new-window",
            f"--window-size=900,680",
        ], creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0)
    else:
        import webbrowser
        webbrowser.open(url)

    # 阻塞主线程
    try:
        while tracker.running:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    tracker.close()


def _find_edge():
    """查找 Edge 或 Chrome 路径"""
    paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    import shutil
    for p in paths:
        if os.path.exists(p):
            return p
    # PATH 搜索
    found = shutil.which("msedge") or shutil.which("chrome") or shutil.which("chromium")
    return found


if __name__ == "__main__":
    main()
