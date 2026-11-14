"""设置页：数据位置、开机自启、预算与提醒、主题色、采集参数、目录清理。"""
from .. import config, migrate, startup, store, theme

MARGIN = 40
RIGHT = theme.W - MARGIN

PATH_ROW_Y, PATH_ROW_H = 168, 32
BTN_W = 132
BTN_X = RIGHT - BTN_W
BTN2_W = 104
BTN2_X = BTN_X - 12 - BTN2_W

OPEN_W, OPEN_H, OPEN_Y = 64, 24, 220
OPEN_X = RIGHT - OPEN_W

# 三行开关统一同一个宽度和左边界，视觉上对齐成一条竖线
TOGGLE_W, TOGGLE_H = 104, 24
TOGGLE_X = RIGHT - TOGGLE_W
START_Y = 282
GOAL_Y = 308
REM_Y = 334
BRAND_Y = 360

GOAL_SET_W = 84
GOAL_SET_X = TOGGLE_X - 8 - GOAL_SET_W
BRAND_SET_W = 84
BRAND_SET_X = TOGGLE_X - 8 - BRAND_SET_W - 8 - 64

IDLE_Y = 408
SAVE_Y = 436
RETAIN_Y = 464
SET_W, SET_H = 84, 24
SET_X = RIGHT - SET_W

IMPORT_W, IMPORT_H, IMPORT_Y = 128, 24, 500
IMPORT_X = RIGHT - IMPORT_W

PREV_OPEN_W, PREV_OPEN_H, PREV_OPEN_Y = 96, 26, 622
CLEAN_X = MARGIN + PREV_OPEN_W + 8
CLEAN_W, CLEAN_H = 116, 26


def _shorten(path, limit):
    if len(path) <= limit:
        return path
    keep = (limit - 3) // 2
    return path[:keep] + "…" + path[-(limit - 3 - keep):]


def previous_data_dir():
    prev = config.get_previous_data_dir()
    if prev and migrate.stats(prev)[0] > 0:
        return prev
    return None


def _hit(x, y, bx, by, bw, bh):
    return bx <= x <= bx + bw and by <= y <= by + bh


def hit_test(x, y):
    if PATH_ROW_Y <= y <= PATH_ROW_Y + PATH_ROW_H:
        if BTN_X <= x <= BTN_X + BTN_W:
            return "change_location"
        if BTN2_X <= x <= BTN2_X + BTN2_W and config.is_custom():
            return "reset_location"
    if _hit(x, y, OPEN_X, OPEN_Y, OPEN_W, OPEN_H):
        return "open_data_dir"
    if _hit(x, y, TOGGLE_X, START_Y, TOGGLE_W, TOGGLE_H):
        return "toggle_startup"
    if _hit(x, y, TOGGLE_X, GOAL_Y, TOGGLE_W, TOGGLE_H):
        return "toggle_goal"
    if _hit(x, y, GOAL_SET_X, GOAL_Y, GOAL_SET_W, TOGGLE_H):
        return "set_goal"
    if _hit(x, y, TOGGLE_X, REM_Y, TOGGLE_W, TOGGLE_H):
        return "toggle_remind"
    if _hit(x, y, BRAND_SET_X, BRAND_Y, BRAND_SET_W, TOGGLE_H):
        return "set_brand"
    if _hit(x, y, TOGGLE_X, BRAND_Y, TOGGLE_W, TOGGLE_H):
        return "reset_brand"
    if _hit(x, y, SET_X, IDLE_Y, SET_W, SET_H):
        return "set_idle"
    if _hit(x, y, SET_X, SAVE_Y, SET_W, SET_H):
        return "set_save"
    if _hit(x, y, SET_X, RETAIN_Y, SET_W, SET_H):
        return "set_retention"
    if _hit(x, y, IMPORT_X, IMPORT_Y, IMPORT_W, IMPORT_H):
        return "import_v2"
    if previous_data_dir():
        if _hit(x, y, MARGIN, PREV_OPEN_Y, PREV_OPEN_W, PREV_OPEN_H):
            return "open_previous"
        if _hit(x, y, CLEAN_X, PREV_OPEN_Y, CLEAN_W, CLEAN_H):
            return "clean_previous"
    return None


def _pill(f, x, y, w, h, text, on, hot=False):
    """on=True 用主题色填充（已启用）；hot=True 表示鼠标悬停在上面。"""
    if on:
        f.rect(x, y, w, h, fill=theme.BRAND_SOFT,
               outline=theme.BRAND_EDGE if not hot else theme.BRAND,
               radius=theme.R_MD, width=2 if hot else 1)
        f.text_centered(x + w / 2, y + h / 2, text, 12, theme.TEXT)
    elif hot:
        f.rect(x, y, w, h, fill=theme.BRAND_SOFT, outline=theme.BRAND_EDGE,
               radius=theme.R_MD, width=1)
        f.text_centered(x + w / 2, y + h / 2, text, 12, theme.TEXT)
    else:
        f.rect(x, y, w, h, outline=theme.BORDER, radius=theme.R_MD, width=1)
        f.text_centered(x + w / 2, y + h / 2, text, 12, theme.DIM)


def _row(f, y, label, value="", value_color=None):
    f.text(MARGIN, y, label, 12, theme.DIM, spacing=0.6)
    if value:
        f.text(MARGIN + 92, y, value, 12, value_color or theme.TEXT)


def _swatch(f, x, y, color, w=18, h=18):
    if color is None:
        f.rect(x, y, w, h, outline=theme.BORDER, radius=theme.R_SM, width=1)
        f.text_centered(x + w / 2, y + h / 2, "自", 9, theme.DIM)
    else:
        f.rect(x, y, w, h, fill=color, outline=theme.BRAND_EDGE, radius=theme.R_SM, width=1)


def draw(f, status="", hover=None):
    location = config.get_location()
    data_dir = store.data_root()
    custom = config.is_custom()
    files, total = migrate.stats(data_dir)
    exists = data_dir.is_dir()
    boot = startup.is_enabled()
    goal = config.get_goal()
    goal_on = config.goal_enabled()
    remind = config.get_remind()
    idle = config.get_idle_threshold()
    save_s = config.get_save_interval()
    retention = config.get_retention_days()
    brand = config.get_brand()

    f.text(MARGIN, 96, "设置", 20, theme.TEXT, spacing=1.2)
    f.hline(MARGIN, 134, RIGHT, theme.BORDER)

    f.text(MARGIN, 152, "数据位置", 12, theme.DIM, spacing=0.6)
    box_w = RIGHT - MARGIN - BTN_W - BTN2_W - 24
    f.rect(MARGIN, PATH_ROW_Y, box_w, PATH_ROW_H, outline=theme.BORDER, radius=theme.R_MD)
    f.text(MARGIN + 14, PATH_ROW_Y + 9, _shorten(str(location), 54), 12, theme.TEXT, mono=True)
    _pill(f, BTN_X, PATH_ROW_Y, BTN_W, PATH_ROW_H, "更改位置…", False, hover == "change_location")
    if custom:
        _pill(f, BTN2_X, PATH_ROW_Y, BTN2_W, PATH_ROW_H, "恢复默认", False, hover == "reset_location")

    f.text(MARGIN, 208, ("自定义位置" if custom else "默认位置（%LOCALAPPDATA%\\AppTimer）")
           + " · 数据只会写进下面的数据目录", 12, theme.DIM)
    f.text(MARGIN, 230, "实际数据目录：", 11, theme.DIM)
    f.text(MARGIN + 78, 230, _shorten(str(data_dir), 54), 11,
           theme.TEXT if exists else theme.DIM, mono=True)
    _pill(f, OPEN_X, OPEN_Y, OPEN_W, OPEN_H, "打开", False, hover == "open_data_dir")
    if status:
        f.text(MARGIN, 252, status, 12, theme.GOOD)

    f.hline(MARGIN, 272, RIGHT, theme.BORDER)
    _row(f, 288, "开机自启")
    _pill(f, TOGGLE_X, START_Y, TOGGLE_W, TOGGLE_H, "已开启" if boot else "已关闭", boot, hover == "toggle_startup")

    _row(f, 314, "今日预算", theme.fmt_minutes(goal) if goal else "未设定",
         theme.TEXT if goal_on else theme.DIM)
    _pill(f, GOAL_SET_X, GOAL_Y, GOAL_SET_W, TOGGLE_H, "设定…", False, hover == "set_goal")
    _pill(f, TOGGLE_X, GOAL_Y, TOGGLE_W, TOGGLE_H, "已开启" if goal_on else "已关闭", goal_on, hover == "toggle_goal")

    _row(f, 340, "预算提醒")
    _pill(f, TOGGLE_X, REM_Y, TOGGLE_W, TOGGLE_H, "已开启" if remind else "已关闭", remind, hover == "toggle_remind")

    _row(f, 366, "主题色")
    _swatch(f, MARGIN + 92, BRAND_Y + 3, brand)
    f.text(MARGIN + 116, BRAND_Y + 6,
           ("自定义" if brand else "跟随模式（深色白 / 亮色黑）"), 11, theme.DIM)
    _pill(f, BRAND_SET_X, BRAND_Y, BRAND_SET_W, TOGGLE_H, "选颜色…", False, hover == "set_brand")
    _pill(f, TOGGLE_X, BRAND_Y, TOGGLE_W, TOGGLE_H, "恢复默认" if brand else "默认", brand is None, hover == "reset_brand")

    f.hline(MARGIN, 392, RIGHT, theme.BORDER)
    _row(f, 408, "空闲阈值", "%d 秒" % idle)
    _pill(f, SET_X, IDLE_Y, SET_W, SET_H, "设定…", False, hover == "set_idle")
    _row(f, 436, "保存间隔", "%d 秒" % save_s)
    _pill(f, SET_X, SAVE_Y, SET_W, SET_H, "设定…", False, hover == "set_save")
    _row(f, 464, "数据保留", ("%d 天" % retention) if retention else "永久")
    _pill(f, SET_X, RETAIN_Y, SET_W, SET_H, "设定…", False, hover == "set_retention")

    f.hline(MARGIN, 490, RIGHT, theme.BORDER)
    _row(f, 506, "该数据目录内容")
    _pill(f, IMPORT_X, IMPORT_Y, IMPORT_W, IMPORT_H, "导入旧版数据…", False, hover == "import_v2")
    f.text(MARGIN, 530, "AppTimer 数据 %d 个文件 · 合计 %.1f MB" % (files, total / 1024 / 1024),
           12, theme.TEXT, mono=True)
    f.text(MARGIN, 550, "空闲阈值＝无输入多久停表；保存间隔＝多久落库；数据保留＝0 或留空为永久。",
           11, theme.DIM)

    f.hline(MARGIN, 574, RIGHT, theme.BORDER)
    prev = previous_data_dir()
    if prev:
        prev_files, prev_bytes = migrate.stats(prev)
        f.text(MARGIN, 588, "旧数据（已停用，不再读取）", 12, theme.DIM, spacing=0.6)
        f.text(MARGIN, 606, _shorten(str(prev), 46), 11, theme.TEXT, mono=True)
        f.text(RIGHT, 606, "%d 个文件 · %.1f MB" % (prev_files, prev_bytes / 1024 / 1024),
               11, theme.DIM, anchor="ra")
        _pill(f, MARGIN, PREV_OPEN_Y, PREV_OPEN_W, PREV_OPEN_H, "打开旧目录", False, hover == "open_previous")
        _pill(f, CLEAN_X, PREV_OPEN_Y, CLEAN_W, CLEAN_H, "清理旧数据", False, hover == "clean_previous")
    else:
        f.text(MARGIN, 590, "关窗后最小化到任务栏继续计时 · 右键托盘图标可显示窗口或退出",
               11, theme.DIM)