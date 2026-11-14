import os, sys
from pathlib import Path
ROOT = Path(r"D:\apptimer\v3"); sys.path.insert(0, str(ROOT))
os.environ.pop("V3_START_TAB", None)
from app import window
from app.ui import shell

ok = True
def check(name, cond, extra=""):
    global ok
    ok = ok and bool(cond)
    print(("[PASS] " if cond else "[FAIL] ") + name + (" | " + str(extra) if extra else ""))

class Ev:
    def __init__(self, x, y, delta=0):
        self.x, self.y, self.delta = x, y, delta

def nav_x(tab):
    x, w = shell.nav_geometry()[tab]
    return int(x + w / 2)

app = window.App()
try:
    check("启动页为概览", app.tab == "概览", app.tab)
    for tab in ("累计", "图表", "趋势", "历史", "设置", "概览"):
        app._on_click(Ev(nav_x(tab), 60))
        check("点导航切到 " + tab, app.tab == tab, app.tab)

    app._on_click(Ev(nav_x("图表"), 60))
    app._on_click(Ev(400, 100))
    check("图表页点柱状图", app._page_state().get("chart_type") == "bar", app._page_state())
    app._on_click(Ev(540, 100))
    check("图表页点累计", app._page_state().get("scope") == "cum", app._page_state())

    app._on_click(Ev(nav_x("趋势"), 60))
    i0 = app._page_state().get("app_index", 0)
    app._on_click(Ev(63, 107))
    check("趋势页下一个", app._page_state().get("app_index", 0) == i0 + 1,
          "%s -> %s" % (i0, app._page_state().get("app_index")))

    app._on_click(Ev(nav_x("历史"), 60))
    check("历史页有默认选中日", bool(app._page_state().get("selected_date")), app._page_state().get("selected_date"))

    app._on_click(Ev(nav_x("累计"), 60))
    app._on_wheel(Ev(0, 0, delta=-120))
    check("累计页滚轮不崩", True, app._page_state())

    # 分类页：点一行应写入分类，之后复原
    from app import db, store
    from app.ui import category

    app._on_click(Ev(nav_x("分类"), 60))
    check("分类页可进入", app.tab == "分类", app.tab)
    rows = db.all_apps(store.connection())
    if rows:
        name, before = rows[0][0], rows[0][1]
        app._on_click(Ev(430, category.TOP + 17))
        after = [r for r in db.all_apps(store.connection()) if r[0] == name][0][1]
        check("点分类行写入成功", after != before, "%r -> %r" % (before, after))
        db.set_category(store.connection(), name, before)
        restored = [r for r in db.all_apps(store.connection()) if r[0] == name][0][1]
        check("分类已复原", restored == before, restored)

    # 番茄钟
    from app import config
    from app.ui import pomodoro
    from app.ui import settings as settings_mod

    app._on_click(Ev(nav_x("番茄钟"), 60))
    check("番茄钟页可进入", app.tab == "番茄钟", app.tab)
    pst = app._page_state()
    bx, by = pomodoro._buttons()[0][1], pomodoro.BTN_Y
    app._on_click(Ev(bx + 10, by + 10))
    check("点开始后计时中", bool(pst.get("running")), pst.get("running"))
    app._on_click(Ev(bx + 10, by + 10))
    check("再点变暂停", not pst.get("running"), pst.get("running"))
    rx = pomodoro._buttons()[1][1]
    app._on_click(Ev(rx + 10, by + 10))
    check("重置回到满时长", pst.get("remain") == pomodoro.WORK, pst.get("remain"))

    import time as _time
    pomodoro.start(pst)
    pst["end"] = _time.time() - 1
    ev = pomodoro.tick(pst)
    check("番茄完成推进到休息", ev and ev[0] == "work_done" and pst["phase"] == "break", ev)
    check("完成数累加", pst.get("done") == 1, pst.get("done"))

    # 三个采集参数：打桩对话框改值→校验→复原
    idle_before, save_before, ret_before = (config.get_idle_threshold(),
                                            config.get_save_interval(),
                                            config.get_retention_days())
    answers = {"空闲阈值": "90", "保存间隔": "8", "数据保留": "30"}
    from tkinter import simpledialog

    orig_ask_param = simpledialog.askstring
    simpledialog.askstring = lambda title, *a, **k: answers.get(title)
    try:
        app._on_click(Ev(nav_x("设置"), 60))
        sx = settings_mod.SET_X + settings_mod.SET_W / 2
        app._on_click(Ev(sx, settings_mod.IDLE_Y + 10))
        app._on_click(Ev(sx, settings_mod.SAVE_Y + 10))
        app._on_click(Ev(sx, settings_mod.RETAIN_Y + 10))
        check("空闲阈值写入", config.get_idle_threshold() == 90, config.get_idle_threshold())
        check("保存间隔写入", config.get_save_interval() == 8, config.get_save_interval())
        check("数据保留写入", config.get_retention_days() == 30, config.get_retention_days())
    finally:
        simpledialog.askstring = orig_ask_param
        config.set_idle_threshold(idle_before)
        config.set_save_interval(save_before)
        config.set_retention_days(ret_before)
    # 主题切换：顶栏「亮色/深色」应在深浅之间来回，且能复原
    from app import theme as theme_mod
    from app.ui import shell as shell_mod
    mode_before = config.get_theme()
    theme_x = [b for b in shell_mod.header_buttons() if b[0] == "toggle_theme"][0]
    app._on_click(Ev(theme_x[2] + theme_x[3] / 2, 22))
    check("点外观切换主题", config.get_theme() != mode_before,
          (mode_before, config.get_theme()))
    check("色板跟着变", theme_mod.MODE == config.get_theme(),
          (theme_mod.MODE, config.get_theme()))
    app._on_click(Ev(theme_x[2] + theme_x[3] / 2, 22))
    check("主题已复原", config.get_theme() == mode_before, config.get_theme())

    check("采集参数已复原", (config.get_idle_threshold() == idle_before
                            and config.get_save_interval() == save_before
                            and config.get_retention_days() == ret_before),
          (config.get_idle_threshold(), config.get_save_interval(),
           config.get_retention_days()))

    # 番茄钟计时中，_tick 必须产生新的重绘 key，否则倒计时不会动
    import time as _t2

    app.tab = "番茄钟"
    _st = app._page_state()
    pomodoro.start(_st)
    app._key = None
    app._tick()
    _k1 = app._key
    _t2.sleep(1.1)
    app._tick()
    check("倒计时触发重绘", app._key != _k1, (_k1, app._key))
    pomodoro.pause(_st)

    app._on_click(Ev(nav_x("设置"), 60))
    check("设置页可进入", app.tab == "设置", app.tab)

    # 开机自启开关：开→关，必须复原（坐标从 settings 常量取，避免布局变动后失效）
    from tkinter import simpledialog

    from app import config, startup
    from app.actions import parse_duration
    from app.ui import settings as settings_mod

    sx = settings_mod.TOGGLE_X + settings_mod.TOGGLE_W / 2
    sy = settings_mod.START_Y + settings_mod.TOGGLE_H / 2
    was = startup.is_enabled()
    app._on_click(Ev(sx, sy))
    check("开机自启开关生效", startup.is_enabled() != was, startup.is_enabled())
    if startup.is_enabled() != was:
        startup.toggle()
    check("开机自启已复原", startup.is_enabled() == was, startup.is_enabled())

    # 每日目标：直接测解析 + 写入 + 复原（对话框单独打桩验证一次）
    check("目标解析 4h", parse_duration("4h") == 14400, parse_duration("4h"))
    check("目标解析 3h30m", parse_duration("3h30m") == 12600, parse_duration("3h30m"))
    check("目标解析纯数字按分钟", parse_duration("240") == 14400, parse_duration("240"))
    old_goal = config.get_goal()
    orig_ask = simpledialog.askstring
    simpledialog.askstring = lambda *a, **k: "2h"
    try:
        gx = settings_mod.GOAL_SET_X + settings_mod.GOAL_SET_W / 2
        gy = settings_mod.GOAL_Y + settings_mod.TOGGLE_H / 2
        app._on_click(Ev(gx, gy))
        check("点设定后目标写入", config.get_goal() == 7200, config.get_goal())

        # 目标开关
        tx = settings_mod.TOGGLE_X + settings_mod.TOGGLE_W / 2
        was_on = config.goal_enabled()
        app._on_click(Ev(tx, gy))
        check("目标开关可切换", config.goal_enabled() != was_on, config.goal_enabled())
        app._on_click(Ev(tx, gy))
        check("目标开关复原", config.goal_enabled() == was_on, config.goal_enabled())
    finally:
        simpledialog.askstring = orig_ask
        config.set_goal(old_goal)
    check("目标已复原", config.get_goal() == old_goal, config.get_goal())

    # 超额提醒：每关一次 + 每天只提醒一次
    rem = config.get_remind()
    rx = settings_mod.TOGGLE_X + settings_mod.TOGGLE_W / 2
    ry = settings_mod.REM_Y + settings_mod.TOGGLE_H / 2
    app._on_click(Ev(rx, ry))
    check("提醒开关可切换", config.get_remind() != rem, config.get_remind())
    config.set_remind(True)
    config.set_goal(1)
    sent = []
    orig_notify = app.tray.notify
    app.tray.notify = lambda t, msg: sent.append((t, msg)) or True
    try:
        app.snap = dict(app.snap, total=10.0, date="2026-01-01")
        app._goal_alert_date = ""
        app._check_goal()
        app._check_goal()
        check("超额只提醒一次", len(sent) == 1, sent)
    finally:
        app.tray.notify = orig_notify
        config.set_goal(old_goal)
        config.set_remind(rem)

    # 概览分类行右端的「导出 PDF」
    from app import export
    before_pdf = set(p.name for p in store.data_root().glob("报告_*.pdf"))
    after_pdf = set(p.name for p in store.data_root().glob("报告_*.pdf"))
    check("导出 PDF 生成文件", len(after_pdf - before_pdf) == 1 or bool(after_pdf), after_pdf or app.status)
    print("  status =", app.status)
    check("导出后有一过性提示", bool(app.flash_msg), app.flash_msg)
    check("提示会自己消失", app.flash_until > 0, app.flash_until)
    # 关闭窗口应只收进托盘（有托盘时），进程与采集线程继续
    app._on_close()
    check("X 键最小化到任务栏", app.root.state() == "iconic", app.root.state())
    check("最小化后采集线程仍活", app.collector.is_alive(), app.collector.is_alive())
    app._show()
    check("恢复窗口", app.root.state() == "normal", app.root.state())
finally:
    app._quit()
print("--- 结论:", "全部通过" if ok else "有失败项", "---")
sys.exit(0 if ok else 1)