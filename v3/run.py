"""AppTimer 入口。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _selftest(out_path):
    r"""打包后自检：把结果写到文件（windowed exe 没有控制台）。

    用法：AppTimer.exe --selftest D:patheport.txt
    """
    import tempfile
    import traceback
    from pathlib import Path

    lines = []
    try:
        from app import db, export, icons, import_v2, store, theme  # noqa: F401
        from app.ui import (category, chart, cumulative, history,  # noqa: F401
                            overview, pages, settings, shell, trend)
        lines.append("页面模块导入: ok (%d 个)" % len(pages.MODULES))

        conn = store.connection()
        lines.append("SQLite: ok，应用 %d 个" % len(db.cumulative(conn)))

        img = icons.extract(os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                                         "System32", "notepad.exe"), 32)
        lines.append("图标提取: %s" % ("ok %s" % (img.size,) if img else "失败"))

        ok, info = export.export_pdf(os.path.join(tempfile.gettempdir(), "v3_selftest.pdf"))
        lines.append("PDF 导出: %s (%s)" % (ok, info))

        lines.append("scan 旧版数据: %s" % (import_v2.scan(store.data_root()),))
        try:
            from app import window
            window._write_pid()
            paths = [str(p) for p in window._pid_paths() if p.exists()]
            lines.append("pid 文件写入: ok（%d 处可写）" % len(paths))
        except Exception as exc:
            lines.append("pid 文件写入失败: %s: %s" % (type(exc).__name__, exc))
        # 配置写入（切换主题/预算都依赖它）：必须能在打包环境里落盘
        try:
            from app import config
            before = config.get_theme()
            ok_write = config.set_theme("dark")
            after = config.get_theme()
            lines.append("配置写入: set=%s, 读回=%s, 期望=dark, 错误=%s"
                         % (ok_write, after, config.last_error or "无"))
            lines.append("配置落点: %s" % " | ".join(str(p) for p in config._candidates()))
            config.set_theme(before)
        except Exception as exc:
            lines.append("配置写入异常: %s: %s" % (type(exc).__name__, exc))
        # 逐项探测注册表/启动文件夹的权限，定位到底哪一步被拦
        try:
            import winreg
            from pathlib import Path as _P
            detail = []
            try:
                k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
                detail.append("OpenKey=ok")
                try:
                    winreg.SetValueEx(k, "AppTimerProbe", 0, winreg.REG_SZ, "x")
                    detail.append("SetValue=ok")
                    winreg.DeleteValue(k, "AppTimerProbe")
                except OSError as e:
                    detail.append("SetValue=%s" % e)
                winreg.CloseKey(k)
            except OSError as e:
                detail.append("OpenKey=%s" % e)
            try:
                k2 = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run")
                detail.append("CreateKey=ok")
                winreg.CloseKey(k2)
            except OSError as e:
                detail.append("CreateKey=%s" % e)
            try:
                startup_dir = _P(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
                probe = startup_dir / "_apptimer_probe.txt"
                probe.write_text("x", encoding="utf-8")
                probe.unlink()
                detail.append("启动文件夹=ok")
            except OSError as e:
                detail.append("启动文件夹=%s" % e)
            lines.append("权限探测: " + " | ".join(detail))
        except Exception as exc:
            lines.append("权限探测异常: %s" % exc)
        # 开机自启：关→开→关 能否往返（打包环境里注册表写入可能被拦）
        try:
            from app import startup
            was = startup.is_enabled()
            ok_off, err_off = startup.set_enabled(False)
            ok_on, err_on = startup.set_enabled(True)
            ok_off2, err_off2 = startup.set_enabled(False)
            lines.append("开机自启往返: 关=%s 开=%s 再关=%s 错误=%s 命令=%s"
                         % (ok_off, ok_on, ok_off2, err_on or err_off or "无",
                            startup._command()))
            if not ok_on:
                lines.append("  → 写入被拒：以管理员身份运行本程序后可解决")
            if was:
                startup.set_enabled(True)
        except Exception as exc:
            lines.append("开机自启异常: %s: %s" % (type(exc).__name__, exc))
        # 进程身份：完整性级别/会话/是否提权——托盘注册被拒时最常是这些差异
        try:
            import ctypes as _ct
            import ctypes.wintypes as _wt
            k32 = _ct.windll.kernel32
            advapi = _ct.windll.advapi32
            sid = k32.WTSGetActiveConsoleSessionId()
            pid_sess = _wt.DWORD()
            k32.ProcessIdToSessionId(k32.GetCurrentProcessId(), _ct.byref(pid_sess))
            tok = _wt.HANDLE()
            advapi.OpenProcessToken(k32.GetCurrentProcess(), 0x0008, _ct.byref(tok))
            size = _wt.DWORD(0)
            advapi.GetTokenInformation(tok, 25, None, 0, _ct.byref(size))   # TokenIntegrityLevel
            buf = _ct.create_string_buffer(size.value or 64)
            advapi.GetTokenInformation(tok, 25, buf, size, _ct.byref(size))
            sid_ptr = _ct.cast(buf, _ct.POINTER(_ct.c_void_p))[0]
            count = _ct.cast(sid_ptr, _ct.POINTER(_ct.c_ubyte))[1]
            rid = _ct.cast(sid_ptr + 8 + 4 * (count - 1), _ct.POINTER(_ct.c_uint))[0]
            lines.append("进程身份: 会话=%s(控制台=%s) 完整性RID=0x%X 管理员=%s"
                         % (pid_sess.value, sid, rid, bool(_ct.windll.shell32.IsUserAnAdmin())))
        except Exception as exc:
            lines.append("进程身份探测失败: %s" % exc)
        # 托盘图标（内存 HICON）+ 气泡通知：打包版最容易退化或失效的两处
        try:
            from app import tray as tray_mod
            ic = tray_mod.hicon_from_image(tray_mod.icon_image(32))
            lines.append("托盘图标: hicon=%s" % ("ok" if ic else "失败"))
            probe = tray_mod.Tray(lambda: None, lambda: None)
            started = probe.start()
            lines.append("托盘注册: %s (ok=%s)" % (started, probe.ok))
            sent = probe.notify("AppTimer · 自检", "如果你看到这条，通知是通的")
            lines.append("气泡通知: %s" % sent)
            lines.append("托盘诊断: " + " | ".join(tray_mod.diagnose()))
            import time as _t
            _t.sleep(0.6)
            probe.stop()
        except Exception as exc:
            lines.append("托盘探测异常: %s: %s" % (type(exc).__name__, exc))
            lines.append(traceback.format_exc()[-700:])
        lines.append("frozen: %s" % getattr(sys, "frozen", False))
    except Exception:
        lines.append("异常:\n" + traceback.format_exc())
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")
    return 0


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--selftest":
        sys.exit(_selftest(sys.argv[2]))
    from app.window import main as run_app
    run_app(silent="--silent" in sys.argv)


if __name__ == "__main__":
    main()