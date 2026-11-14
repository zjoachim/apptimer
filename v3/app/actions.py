"""用户动作：迁移位置、导入旧数据、导出 PDF、清理旧数据、开关自启、改名、预算、番茄钟、主题。

App 只管窗口与渲染，这里管"做一件事 + 给一次可见反馈"。
"""
import os
import re
from pathlib import Path

from . import config, db, export, import_v2, migrate, startup, store, theme

_UNIT = re.compile(r"^\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?\s*(?:(\d+)\s*s)?\s*$", re.I)


def parse_duration(text):
    """把 "4h" / "3h30m" / "240"（纯数字按分钟）/ "14400s" 解析成秒。"""
    if not text:
        return 0
    raw = str(text).strip().lower()
    if raw.isdigit():
        return int(raw) * 60
    m = _UNIT.match(raw)
    if not m or not any(m.groups()):
        return 0
    h, mi, sec = (int(g) if g else 0 for g in m.groups())
    return h * 3600 + mi * 60 + sec


def _done(app, status):
    app.status = status
    if hasattr(app, "flash"):
        app.flash(status)
    else:
        app.render()


def change_location(app):
    from tkinter import filedialog

    current = store.data_root()
    choice = filedialog.askdirectory(
        title="选择数据位置（数据会放在其下的 %s）" % config.DATA_SUBDIR,
        initialdir=str(config.get_location()))
    if not choice:
        return
    location = Path(choice)
    target = config.data_dir(location)
    if location.resolve() == config.get_location().resolve():
        _done(app, "已经是当前位置")
        return
    if migrate.stats(target)[0] > 0:
        _done(app, "该位置下已有 %s 且有数据，请换一个位置" % config.DATA_SUBDIR)
        return

    files, _ = migrate.stats(current)
    moved = 0
    if files > 0:
        app.status = "正在迁移…"
        app.render()
        app.root.update_idletasks()
        report = migrate.migrate(current, target)
        if not report["ok"]:
            _done(app, "迁移失败：%s" % report["error"])
            return
        moved = report["files"]
        config.set_previous_data_dir(current)

    config.set_location(location)
    config.ensure_data_dir()
    prev = config.get_previous_data_dir()
    if prev and prev.resolve() == target.resolve():
        config.set_previous_data_dir(None)
    app.restart_collector()
    app.scroll = 0
    _done(app, ("已迁移 %d 个文件到 %s" % (moved, target)) if moved
          else ("已切换，数据目录 %s" % target))


def reset_location(app):
    config.set_location(None)
    config.ensure_data_dir()
    prev = config.get_previous_data_dir()
    if prev and prev.resolve() == store.data_dir().resolve():
        config.set_previous_data_dir(None)
    app.restart_collector()
    app.scroll = 0
    _done(app, "已恢复默认位置（数据在 %s）" % store.data_root())


def import_old_data(app):
    from tkinter import filedialog

    guess = Path.home() / "Desktop" / "程序使用记录"
    choice = filedialog.askdirectory(
        title="选择旧版数据目录（含 2026-01-01 这样的日期文件夹）",
        initialdir=str(guess if guess.is_dir() else Path.home() / "Desktop"))
    if not choice:
        return
    app.status = "正在导入…"
    app.render()
    app.root.update_idletasks()
    report = import_v2.import_from(choice, store.connection())
    if report["ok"]:
        store.bump()
        app.snap = store.load(force=True)
        app.scroll = 0
        _done(app, "已导入 %d 天 / %d 条会话 / %d 个小时桶" % (
            report["days"], report["sessions"], report["hours"]))
    else:
        _done(app, "导入失败：%s" % report["error"])


def export_pdf(app):
    app.status = "正在导出 PDF…"
    app.render()
    app.root.update_idletasks()
    ok, info = export.export_pdf()
    _done(app, ("PDF 已导出：%s" % info) if ok else ("导出失败：%s" % info))


def open_folder(app, path):
    if not path:
        return
    path = Path(path)
    if not path.is_dir():
        _done(app, "目录不存在：%s" % path)
        return
    try:
        os.startfile(str(path))
    except OSError as exc:
        _done(app, "打开失败：%s" % exc)


def clean_previous(app):
    from tkinter import messagebox

    prev = config.get_previous_data_dir()
    if not prev:
        return
    files, total = migrate.stats(prev)
    if not messagebox.askyesno(
            "清理旧数据",
            "将从下面位置删除 %d 个 AppTimer 数据文件（%.1f MB）：\n\n%s\n\n"
            "该目录里的其它文件不会动。" % (files, total / 1024 / 1024, prev)):
        return
    removed, freed, dir_removed = migrate.purge(prev)
    config.set_previous_data_dir(None)
    tail = "，目录已一并删除" if dir_removed else "（目录里还有其它文件，保留）"
    _done(app, "已清理旧数据：%d 项，释放 %.1f MB%s" % (removed, freed / 1024 / 1024, tail))


def toggle_startup(app):
    on, err = startup.toggle()
    if err:
        _done(app, "开机自启失败：请以管理员身份运行本程序后再试")
        return
    _done(app, "开机自启已开启" if on else "开机自启已关闭")


def _ask_number(app, title, tip, initial):
    from tkinter import simpledialog

    text = simpledialog.askstring(title, tip, initialvalue=str(initial), parent=app.root)
    if text is None:
        return None
    text = text.strip()
    if not text:
        return 0
    try:
        return max(0, int(float(text)))
    except ValueError:
        return None


def set_idle_threshold(app):
    value = _ask_number(app, "空闲阈值", "无输入多少秒后停止计时（默认 120）：",
                        config.get_idle_threshold())
    if value is None:
        return
    config.set_idle_threshold(max(10, value))
    _done(app, "空闲阈值已设为 %d 秒（重启后生效）" % config.get_idle_threshold())


def set_save_interval(app):
    value = _ask_number(app, "保存间隔", "采集器多少秒落一次库（默认 5）：",
                        config.get_save_interval())
    if value is None:
        return
    config.set_save_interval(max(1, value))
    _done(app, "保存间隔已设为 %d 秒（重启后生效）" % config.get_save_interval())


def set_retention_days(app):
    value = _ask_number(app, "数据保留", "保留多少天（0 = 永久）：", config.get_retention_days())
    if value is None:
        return
    config.set_retention_days(value)
    if value <= 0:
        _done(app, "数据保留已设为永久")
        return
    removed = db.purge_older_than(store.connection(), value)
    store.bump()
    app.snap = store.load(force=True)
    _done(app, "已保留最近 %d 天，清理了 %d 天的旧记录" % (value, removed))


def set_pomodoro(app):
    from tkinter import simpledialog
    from .ui import pomodoro

    work, brk, long_ = (v // 60 for v in config.get_pomodoro()[:3])
    text = simpledialog.askstring(
        "番茄钟时长", "按「专注/休息/长休息」填分钟，例如 25/5/15：",
        initialvalue="%d/%d/%d" % (work, brk, long_), parent=app.root)
    if text is None:
        return
    parts = [p for p in text.replace("，", "/").replace(" ", "/").split("/") if p.strip()]
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        _done(app, "格式不对，请填 25/5/15 这样")
        return
    if not nums or any(n <= 0 for n in nums):
        _done(app, "分钟数必须大于 0")
        return
    work = nums[0]
    brk = nums[1] if len(nums) > 1 else 5
    long_ = nums[2] if len(nums) > 2 else max(brk, 15)
    config.set_pomodoro(work, brk, long_)
    pomodoro.reset(app._page_state())
    _done(app, "番茄钟已设为 专注 %d / 休息 %d / 长休息 %d 分钟" % (work, brk, long_))


def set_goal(app):
    from tkinter import simpledialog

    cur = config.get_goal()
    text = simpledialog.askstring(
        "今日预算", "输入今日时长预算，例如 4h、3h30m、240（分钟）、14400s；填 0 取消：",
        initialvalue=theme.fmt_minutes(cur) if cur else "", parent=app.root)
    if text is None:
        return
    seconds = parse_duration(text)
    if not config.set_goal(seconds):
        _done(app, "保存失败：%s" % (config.last_error or "配置目录不可写"))
        return
    _done(app, "今日预算已设为 %s" % theme.fmt_minutes(seconds) if seconds
          else "已取消今日预算")


def toggle_goal(app):
    if not config.get_goal():
        _done(app, "请先设定今日预算")
        return
    on = config.toggle_goal_enabled()
    _done(app, "今日预算已开启" if on else "今日预算已关闭")


def toggle_remind(app):
    on = not config.get_remind()
    config.set_remind(on)
    if not config.last_error:
        _done(app, "预算提醒已开启" if on else "预算提醒已关闭")
    else:
        _done(app, "保存失败：%s" % config.last_error)


def set_brand(app):
    from tkinter import colorchooser

    cur = config.get_brand() or (theme.BRAND if theme.MODE == "dark" else theme.BRAND)
    hex_now = "#%02x%02x%02x" % tuple(cur)
    _rgb, hex_pick = colorchooser.askcolor(color=hex_now, title="选择主题色", parent=app.root)
    if not hex_pick:
        return
    rgb = tuple(int(hex_pick[i:i + 2], 16) for i in (1, 3, 5))
    config.set_brand(rgb)
    app.apply_theme()
    _done(app, "主题色已设为 RGB%s" % (rgb,))


def reset_brand(app):
    config.set_brand(None)
    app.apply_theme()
    _done(app, "主题色已恢复默认（跟随深浅色）")


def toggle_theme(app):
    mode = "light" if config.get_theme() == "dark" else "dark"
    config.set_theme(mode)
    app.apply_theme()
    _done(app, "已切换到%s模式" % ("亮色" if mode == "light" else "深色"))


def rename_app(app, name):
    from tkinter import simpledialog

    current = (app.snap.get("labels") or {}).get(name, name)
    new_name = simpledialog.askstring(
        "设置显示名称", "给「%s」起个显示名（留空恢复原名）：" % current,
        initialvalue="" if current == name else current, parent=app.root)
    if new_name is None:
        return
    db.set_alias(store.connection(), name,
                 "" if new_name.strip() in ("", name) else new_name.strip())
    store.bump()
    app.snap = store.load()
    _done(app, "已更新显示名")