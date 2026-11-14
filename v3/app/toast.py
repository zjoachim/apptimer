"""自绘通知条：不依赖系统托盘/通知中心，右下角浮一个无边框小窗，几秒后自动消失。

打包版里 Shell_NotifyIcon 可能被安全策略拒绝（Access Denied），此时它是唯一的提醒手段。
"""
import tkinter as tk

from . import theme

WIDTH, PAD = 320, 16
SHOW_MS = 4200


def _hex(color):
    return "#%02x%02x%02x" % tuple(color)


def show(root, title, body, seconds=SHOW_MS / 1000.0):
    """在屏幕右下角弹一条通知。root 用来继承图标与 DPI，不影响主窗口。"""
    try:
        win = tk.Toplevel(root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        bg = _hex(theme.PANEL)
        fg = _hex(theme.TEXT)
        dim = _hex(theme.DIM)
        edge = _hex(theme.BRAND_EDGE)
        win.configure(bg=edge)

        height = 78
        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()
        x = screen_w - WIDTH - 32
        y = screen_h - height - 64
        win.geometry("%dx%d+%d+%d" % (WIDTH, height, x, y))

        inner = tk.Frame(win, bg=bg)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Label(inner, text=title, bg=bg, fg=fg, anchor="w",
                 font=("Microsoft YaHei UI", 10, "bold")).pack(
            fill="x", padx=PAD, pady=(12, 2))
        tk.Label(inner, text=body, bg=bg, fg=dim, anchor="w", justify="left",
                 wraplength=WIDTH - PAD * 2, font=("Microsoft YaHei UI", 9)).pack(
            fill="x", padx=PAD)

        win.after(int(seconds * 1000), win.destroy)
        return True
    except tk.TclError:
        return False
