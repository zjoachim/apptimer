"""v3 窗口：单画布 + 采集器 + 数据变更重绘。"""
import ctypes
import os
import time
import traceback
import tkinter as tk
from pathlib import Path

from PIL import ImageTk

from . import actions, collector, config, log as applog, store, theme, toast, tray
from .ui import overview, pages, placeholder, settings, shell

REFRESH_MS = 1000


def _log_pixels():
    hdc = ctypes.windll.user32.GetDC(0)
    try:
        return ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
    finally:
        ctypes.windll.user32.ReleaseDC(0, hdc)


def _draw_flash(f, text):
    """底部居中的一次性提示条。"""
    size = 12
    w = max(160, int(theme.font(size).getlength(text) / max(1.0, theme.SCALE)) + 40)
    h = 32
    x = (theme.W - w) / 2
    y = theme.H - 56
    f.rect(x, y, w, h, fill=theme.PANEL, outline=theme.BRAND_EDGE, radius=theme.R_TOAST, width=1)
    f.text_centered(theme.W / 2, y + h / 2, text, size, theme.TEXT)


def _hex(color):
    return "#%02x%02x%02x" % tuple(color)


def _dpi_scale():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass
    for probe in (lambda: ctypes.windll.user32.GetDpiForSystem(),
                  lambda: ctypes.windll.shcore.GetDpiForSystem(),
                  _log_pixels):
        try:
            dpi = probe()
        except (AttributeError, OSError):
            continue
        if dpi:
            return dpi / 96.0
    return 1.0


def _pid_paths():
    return (store.data_root() / "v3.pid", config.config_dir() / "v3.pid")


def _write_pid():
    pid = str(os.getpid())
    for path in _pid_paths():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(pid, encoding="utf-8")
        except OSError:
            pass


def _read_pid():
    for path in _pid_paths():
        try:
            return int(path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            continue
    return 0


def _pid_alive(pid):
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x1000, False, pid)      # QUERY_LIMITED_INFORMATION
    if not handle:
        return False
    code = ctypes.c_ulong()
    kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
    kernel32.CloseHandle(handle)
    return code.value == 259                               # STILL_ACTIVE


def _kill_pid(pid):
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x0001, False, pid)      # PROCESS_TERMINATE
    if not handle:
        return False
    ok = bool(kernel32.TerminateProcess(handle, 1))
    kernel32.CloseHandle(handle)
    return ok


def _find_window():
    hwnd = ctypes.windll.user32.FindWindowW(None, "程序使用时间追踪器")
    return hwnd or 0


def _focus_window(hwnd):
    try:
        ctypes.windll.user32.ShowWindow(hwnd, 9)           # SW_RESTORE
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    except OSError:
        pass


def _take_over_zombie():
    """互斥体被占但找不到窗口：清掉残留进程，好让新实例接管。"""
    if _find_window():
        return False
    pid = _read_pid()
    if pid and pid != os.getpid() and _pid_alive(pid):
        _kill_pid(pid)
        time.sleep(0.6)
        return True
    return False


def _single_instance():
    """同名互斥体：已有 v3 在跑就不开第二个，避免双份计时。"""
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel32.CreateMutexW(None, True, "Local\\AppTimerV3_SingleInstance")
    return handle if kernel32.GetLastError() != 183 else None


class App:
    def __init__(self, mutex=None, start_hidden=False):
        theme.set_scale(_dpi_scale())
        self._mutex = mutex
        w, h = theme.pixel_size()
        self.root = tk.Tk()
        self.root.title("程序使用时间追踪器")
        try:
            from PIL import ImageTk
            from . import iconart
            # 多档一起给，让 Windows 直接挑 16/20/24/32 的原图，不要再缩放
            self._icon_photos = [ImageTk.PhotoImage(ic) for _s, ic in iconart.window_icons()]
            self.root.iconphoto(True, *self._icon_photos)
        except (OSError, tk.TclError):
            pass
        self.root.geometry("%dx%d" % (w, h))
        self.root.configure(bg=_hex(theme.BG))
        self.root.resizable(False, False)
        self._dark_titlebar()

        config.ensure_data_dir()
        store.reset()
        try:
            db.purge_older_than(store.connection(), config.get_retention_days())
        except Exception:
            pass
        self.collector = collector.Collector(store.data_root())
        self.collector.start()

        self.canvas = tk.Canvas(self.root, width=w, height=h, bg=_hex(theme.BG), highlightthickness=0)
        self.canvas.pack()
        import os

        start = os.environ.get("V3_START_TAB", "")
        self.tab = {"overview": "概览", "cumulative": "累计", "chart": "图表", "trend": "趋势",
                    "hours": "时段", "pomodoro": "番茄钟",
                    "category": "分类", "history": "历史", "settings": "设置"}.get(start) or start or "概览"
        self.scroll = 0
        self.status = ""
        self.page_state = {}
        self._anim_job = None
        self._goal_alert_date = config.get_goal_alert_date()
        self.flash_msg = ""
        self.flash_until = 0.0
        self._hover = None
        self._closing = False
        self.snap = store.load(force=True)
        self._version = store.version()
        self._key = None
        self._photo = None
        self._item = self.canvas.create_image(0, 0, anchor="nw")
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", self._on_leave)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        _write_pid()
        self.tray = tray.Tray(on_show=lambda: self.root.after(0, self._show),
                              on_quit=lambda: self.root.after(0, self._quit),
                              icon_dir=config.config_dir())
        self.tray.start()
        self.render()
        if start_hidden:
            try:
                self.root.withdraw()
            except tk.TclError:
                pass
        self.root.after(REFRESH_MS, self._tick)

    def apply_theme(self):
        """切换深浅色：重设色板、窗口底色、标题栏，然后整帧重绘。"""
        theme.apply_mode(config.get_theme(), config.get_brand())
        self.root.configure(bg=_hex(theme.BG))
        self.canvas.configure(bg=_hex(theme.BG))
        self._dark_titlebar()
        self._key = None
        self.render()

    def _dark_titlebar(self):
        """标题栏跟随主题：深色用沉浸式深色 + 同色标题栏，亮色反过来。"""
        try:
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            dwm = ctypes.windll.dwmapi
            for attr in (20, 19):        # DWMWA_USE_IMMERSIVE_DARK_MODE（新旧编号）
                value = ctypes.c_int(1 if theme.DARK_TITLE else 0)
                if dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value),
                                             ctypes.sizeof(value)) == 0:
                    break
            # DWMWA_BORDER_COLOR=34 / DWMWA_CAPTION_COLOR=35：去掉深色窗口那圈白边
            border = ctypes.c_uint(0x00000000)      # 黑边（0xFFFFFFFE = 无边框）
            dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(border), ctypes.sizeof(border))
            caption = ctypes.c_uint(theme.CAPTION)  # COLORREF(BGR)，和背景同色
            dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption), ctypes.sizeof(caption))
        except (AttributeError, OSError):
            pass

    # ---------- 渲染 ----------
    @property
    def current_app(self):
        return self.collector.current[0]

    def _display_key(self):
        """决定"这帧和上一帧是否一样"。番茄钟在计时时把剩余秒数算进去。"""
        key = (self.snap["stamp"], self.current_app, self.tab, self.scroll, self.status)
        if self.tab == "番茄钟":
            from .ui import pomodoro
            state = self.page_state.get("番茄钟")
            key += (pomodoro.remaining(state) if state else 0,)
        return key

    def notify(self, title, body):
        """优先系统托盘气泡；被安全策略拒了就用自己的小窗，保证用户看得见。"""
        try:
            if self.tray.notify(title, body):
                return True
        except Exception:
            pass
        ok = toast.show(self.root, title.replace("AppTimer · ", ""), body)
        if not ok:
            applog.log("通知失败：%s / %s" % (title, body))
        return ok

    def flash(self, text, seconds=2.6):
        """一次性反馈条：任何页面都能看到的操作结果。"""
        if not text:
            return
        self.flash_msg = text
        self.flash_until = time.monotonic() + seconds
        self.render()

    def render(self):
        snap = self.snap
        self._key = self._display_key()
        self._anim_job = None
        f = theme.Frame()
        shell.draw_shell(f, self.tab, {
            "date": snap["date"],
            "current_app": self.current_app,
            "total_text": theme.fmt_duration(snap["total"]),
            "hover": self._hover,
        })
        if self.tab == "概览":
            overview.draw(f, snap, scroll=self.scroll, hover=self.hover_id("header"))
        elif self.tab == "设置":
            settings.draw(f, self.status, hover=self.hover_id("设置"))
        elif pages.has_page(self.tab):
            state = self._page_state()
            state["_hover"] = self.hover_id(self.tab)
            pages.draw(f, self.tab, snap, state)
        else:
            placeholder.draw(f, self.tab)
        if self.flash_msg and time.monotonic() < self.flash_until:
            _draw_flash(f, self.flash_msg)
        self._photo = ImageTk.PhotoImage(f.finish())
        self.canvas.itemconfig(self._item, image=self._photo)
        self._schedule_anim()

    def _schedule_anim(self):
        if self._anim_job is not None:
            return
        need = pages.has_page(self.tab) and pages.animating(self.tab, self._page_state())
        if need:
            self._anim_job = self.root.after(1, self._anim_frame)

    def _anim_frame(self):
        self._anim_job = None
        self.render()

    def _check_goal(self):
        """超出每日目标时弹一次托盘气泡（每天一次）。"""
        goal = config.get_goal()
        if goal <= 0 or not config.get_remind():
            return
        today = self.snap.get("date") or ""
        if self._goal_alert_date == today:
            return
        used = self.snap.get("total") or 0
        if used < goal:
            return
        self._goal_alert_date = today
        config.set_goal_alert_date(today)      # 跨进程也只提醒一次
        # 气泡第一行是进程名（dev 下是 Python），所以把产品名放进标题行
        sent = self.notify("AppTimer · 今日超出预算",
                           "今日已用 %s，预算 %s" % (theme.fmt_minutes(used),
                                                 theme.fmt_minutes(goal)))
        self.status = "已超出每日目标" + ("，已发送提醒" if sent else "")

    def _page_action(self, action):
        """页面内控件请求的额外动作（目前只有番茄钟的设定与提醒开关）。"""
        from .ui import pomodoro

        if action == "set_durations":
            actions.set_pomodoro(self)
        elif action in ("toggle_notify_work", "toggle_notify_break"):
            kind = "work" if action.endswith("work") else "break"
            current = config.get_pomodoro()[3 if kind == "work" else 4]
            config.set_pomo_notify(kind, not current)
            self.status = "专注结束提醒已%s" % ("关闭" if current else "开启") if kind == "work" \
                else "休息结束提醒已%s" % ("关闭" if current else "开启")
            state = self._page_state()
            if state.get("running") is None:
                pomodoro._st(state)
        self.render()

    def _pomodoro_tick(self):
        """番茄钟到期时推进阶段并弹气泡（任何 tab 下都生效）。"""
        from .ui import pomodoro

        state = self.page_state.get("番茄钟")
        if not state:
            return
        event = pomodoro.tick(state)
        if not event:
            return
        kind, hint = event
        want = (config.get_pomodoro()[3] if kind == "work_done"
                else config.get_pomodoro()[4])
        if want:
            self.notify("AppTimer · 番茄钟", hint)
        self.status = hint
        if self.tab == "番茄钟":
            theme.anim_start(state)

    def _watch_collector(self):
        """采集线程死了就重启（数据库被占用、线程异常等），否则界面照常但不计时。"""
        if self._closing:
            return
        try:
            alive = self.collector.is_alive()
        except Exception:
            alive = False
        if alive:
            return
        applog.log("采集线程已停止，自动重启")
        try:
            self.restart_collector()
            self.flash("采集已自动恢复", 4.0)
        except Exception:
            applog.log("重启采集失败：" + traceback.format_exc())

    def _tick(self):
        """1 秒心跳。异常绝不能掐断循环——否则界面静默冻结、采集还在写库。"""
        try:
            if store.version() != self._version:
                self._version = store.version()
                self.snap = store.load()
            self._check_goal()
            self._pomodoro_tick()
            if self.flash_msg and time.monotonic() >= self.flash_until:
                self.flash_msg = ""
                self._key = None
            if self._display_key() != self._key:
                self.render()
            self._watch_collector()
        except Exception:
            applog.log("心跳出错：" + traceback.format_exc())
        finally:
            try:
                self.root.after(REFRESH_MS, self._tick)
            except tk.TclError:
                pass

    def hover_id(self, group):
        """当前悬停目标的标识（只在 group 匹配时返回），页面据此画 hover 态。"""
        if self._hover and self._hover[0] == group:
            return self._hover[1]
        return None

    def _hover_target(self, x, y):
        action = shell.header_hit(x, y)
        if action:
            return ("header", action)
        tab = shell.nav_hit(x, y)
        if tab:
            return ("nav", tab)
        if self.tab == "概览":
            return ("header", "export_pdf") if overview.export_hit(
                x, y, self._overview_shift()) else None
        if self.tab == "设置":
            action = settings.hit_test(x, y)
            return ("设置", action) if action else None
        if pages.has_page(self.tab):
            mod = pages._module(self.tab)
            handler = getattr(mod, "hover", None)
            action = handler(x, y, self._page_state(), self.snap) if handler else None
            return (self.tab, action) if action else None
        return None

    def _on_motion(self, event):
        target = self._hover_target(event.x / theme.SCALE, event.y / theme.SCALE)
        if target != self._hover:
            self._hover = target
            self.render()

    def _on_leave(self, event):
        if self._hover is not None:
            self._hover = None
            self.render()

    def _overview_shift(self):
        return 14 if overview._goal_progress(self.snap) else 0

    def _page_state(self):
        return self.page_state.setdefault(self.tab, {})

    # ---------- 交互 ----------
    def _on_click(self, event):
        x = event.x / theme.SCALE
        y = event.y / theme.SCALE
        action = shell.header_hit(x, y)
        if action == "toggle_theme":
            actions.toggle_theme(self)
            return
        if action == "quit":
            self._quit()
            return
        tab = shell.nav_hit(x, y)
        if tab and tab != self.tab:
            self.tab = tab
            self.scroll = 0
            self.status = ""
            if pages.has_page(tab):
                pages.enter(tab, self._page_state())
            self.render()
            return
        if self.tab == "概览" and overview.export_hit(x, y, self._overview_shift()):
            self._export_pdf()
            return
        if self.tab == "设置":
            action = settings.hit_test(x, y)
            if action == "change_location":
                self._change_location()
            elif action == "reset_location":
                self._reset_location()
            elif action == "open_data_dir":
                self._open_folder(store.data_root())
            elif action == "open_previous":
                self._open_folder(config.get_previous_data_dir())
            elif action == "clean_previous":
                self._clean_previous()
            elif action == "import_v2":
                self._import_old_data()
            elif action == "toggle_startup":
                self._toggle_startup()
            elif action == "set_goal":
                actions.set_goal(self)
            elif action == "toggle_goal":
                actions.toggle_goal(self)
            elif action == "toggle_remind":
                actions.toggle_remind(self)
            elif action == "toggle_theme":
                actions.toggle_theme(self)
            elif action == "set_brand":
                actions.set_brand(self)
            elif action == "reset_brand":
                actions.reset_brand(self)
            elif action == "set_idle":
                actions.set_idle_threshold(self)
            elif action == "set_save":
                actions.set_save_interval(self)
            elif action == "set_retention":
                actions.set_retention_days(self)
            return
        if pages.has_page(self.tab):
            result = pages.on_click(self.tab, x, y, self._page_state(), self.snap)
            if isinstance(result, str):
                self._page_action(result)
                result = True
            if result:
                self.render()

    def _on_right_click(self, event):
        """分类页右键给应用起别名。"""
        if self.tab != "分类":
            return
        from .ui import category

        x = event.x / theme.SCALE
        y = event.y / theme.SCALE
        state = self._page_state()
        name = category.app_at(x, y, self.snap, state.get("scroll", 0))
        if name:
            actions.rename_app(self, name)

    def _on_wheel(self, event):
        delta = -1 if event.delta > 0 else 1
        if self.tab == "概览":
            limit = overview.max_scroll(self.snap)
            self.scroll = max(0, min(limit, self.scroll + delta))
            self.render()
        elif pages.has_page(self.tab):
            if pages.on_wheel(self.tab, delta, event.x / theme.SCALE, event.y / theme.SCALE,
                              self._page_state(), self.snap):
                self.render()

    # ---------- 采集器与数据目录 ----------
    def restart_collector(self):
        try:
            self.collector.stop()
            self.collector.join(2.0)
        except Exception:
            pass
        store.reset()
        self.collector = collector.Collector(store.data_root())
        self.collector.start()
        self._version = store.version()
        self.snap = store.load(force=True)

    def _change_location(self):
        actions.change_location(self)

    def _reset_location(self):
        actions.reset_location(self)

    def _import_old_data(self):
        actions.import_old_data(self)

    def _export_pdf(self):
        actions.export_pdf(self)

    def _open_folder(self, path):
        actions.open_folder(self, path)

    def _clean_previous(self):
        actions.clean_previous(self)

    def _toggle_startup(self):
        actions.toggle_startup(self)

    def _show(self):
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        except tk.TclError:
            pass

    def _on_close(self):
        """点 X = 最小化到任务栏，采集继续；要退出走「退出」或托盘菜单。"""
        try:
            self.root.iconify()
            self.status = ""
            return
        except tk.TclError:
            pass

    def _on_close_legacy(self):
        """有托盘就收进托盘继续采集；没有托盘才真正退出。"""
        if self.tray.ok:
            try:
                self.root.withdraw()
            except tk.TclError:
                pass
            return
        self._quit()

    def _quit(self):
        self._closing = True
        applog.log("退出")
        for path in _pid_paths():
            try:
                path.unlink()
            except OSError:
                pass
        self.tray.stop()
        try:
            self.collector.stop()
            self.collector.join(2.0)
        except Exception:
            pass
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def run(self):
        self.root.mainloop()


def _already_running():
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("程序使用时间追踪器", "已经有一个实例在运行了，不会重复计时。")
    root.destroy()


def main(silent=False):
    theme.apply_mode(config.get_theme(), config.get_brand())
    applog.log("启动 v3 · 主题=%s · 主题色=%s · 配置=%s"
               % (config.get_theme(), config.get_brand(), config.active_path()))
    mutex = _single_instance()
    if mutex is None:
        hwnd = _find_window()
        if hwnd:                       # 真的已经开着：把窗口叫到前面
            _focus_window(hwnd)
            return
        if _take_over_zombie():        # 上一份崩了/被强杀，互斥体还占着
            mutex = _single_instance()
        if mutex is None:
            _already_running()
            return
    App(mutex, start_hidden=silent).run()