"""历史页：左列最近 30 天，右列选中日的应用明细。"""
from PIL import Image, ImageDraw

from .. import config, db, icons, store, theme

DAYS = 30
LEFT_X, LEFT_W = 20, 320
LEFT_R = LEFT_X + LEFT_W
ROW_H = 30
VISIBLE = 12
LIST_TOP = 120
HLINE_Y = 112

RIGHT_X, RIGHT_W = 360, 520
RIGHT_R = RIGHT_X + RIGHT_W
DROW_H = 32
DROW_MAX = 8
DETAIL_TOP = 132

BAR_W = 56
BAR_H = 4
BAR_GAP = 12
DUR_COL_W = 62          # 时长列固定宽度，条形图左端才不会随文字长度漂移
BAR_R = RIGHT_R - DUR_COL_W - BAR_GAP
BAR_L = BAR_R - BAR_W
EMPTY = "暂无历史数据"

_measurer = ImageDraw.Draw(Image.new("RGB", (1, 1)))


def _text_w(s, size, mono=False):
    return _measurer.textlength(s, font=theme.font(size, mono)) / theme.SCALE


def _days():
    return db.recent_days(store.connection(), DAYS)


def _selected(days, state):
    dates = [d for d, _ in days]
    sel = state.get("selected_date")
    if sel not in dates:
        sel = dates[0]
    state["selected_date"] = sel
    return sel


def _scroll(days, state):
    try:
        s = int(state.get("scroll") or 0)
    except (TypeError, ValueError):
        s = 0
    s = max(0, min(max(0, len(days) - VISIBLE), s))
    state["scroll"] = s
    return s


def _draw_days(f, days, sel, scroll, state=None):
    f.text(LEFT_X, 88, "最近 %d 天" % DAYS, 11, theme.DIM)
    f.hline(LEFT_X, HLINE_Y, LEFT_R, theme.BORDER)
    for i, (date, sec) in enumerate(days[scroll:scroll + VISIBLE]):
        y = LIST_TOP + i * ROW_H
        on = date == sel
        hot = (state.get("_hover") == "day_%d" % (scroll + i)) and not on
        if hot:
            f.rect(LEFT_X, y + 1, LEFT_W, ROW_H - 2, fill=theme.BRAND_SOFT, radius=theme.R_MD)
        if on:
            f.rect(LEFT_X, y + 1, LEFT_W, ROW_H - 2, fill=theme.BRAND_SOFT, outline=theme.BRAND_EDGE, radius=theme.R_MD)
        f.text(LEFT_X + 12, y + 8, date, 12, theme.TEXT if on else theme.DIM)
        f.text(LEFT_R - 12, y + 8, theme.fmt_hm(sec), 12,
               theme.TEXT if on else theme.DIM, anchor="ra", mono=True)
    if len(days) > VISIBLE:
        end = min(len(days), scroll + VISIBLE)
        f.text(LEFT_X, LIST_TOP + VISIBLE * ROW_H + 10,
               "第 %d-%d 天 / 共 %d 天 · 滚轮翻页" % (scroll + 1, end, len(days)),
               11, theme.DIM)


def _draw_detail(f, sel, snap):
    apps = db.day_apps(store.connection(), sel)
    total = sum(apps.values())
    f.text(RIGHT_X, 86, sel, 14, theme.TEXT)
    if apps:
        f.text(RIGHT_X + _text_w(sel, 14) + 10, 89,
               " · 合计 %s · %d 个应用" % (theme.fmt_duration(total), len(apps)),
               12, theme.DIM)
    f.hline(RIGHT_X, HLINE_Y, RIGHT_R, theme.BORDER)
    if not apps:
        f.text(RIGHT_X, 148, "这一天没有记录", 12, theme.DIM)
        return
    items = sorted(apps.items(), key=lambda kv: (-kv[1], kv[0]))[:DROW_MAX]
    for i, (name, sec) in enumerate(items):
        y = DETAIL_TOP + i * DROW_H
        ratio = sec / total if total else 0.0
        dur = theme.fmt_hm(sec)
        ico = icons.load(name, (snap.get("exes") or {}).get(name, ""),
                         config.config_dir() / "icons")
        if ico is not None:
            f.image(ico, RIGHT_X, y + 8, 16, 16)
        label = (snap.get("labels") or {}).get(name, name)
        f.text(RIGHT_X + 22, y + 7, label, 13, theme.TEXT)
        f.text(RIGHT_R, y + 8, dur, 12, theme.TEXT, anchor="ra", mono=True)
        # 固定列：轨道整条画、填充覆盖，左端每行一致
        f.rect(BAR_L, y + 15, BAR_W, BAR_H, fill=theme.TRACK)
        f.rect(BAR_L, y + 15, max(2, int(round(BAR_W * ratio))), BAR_H, fill=theme.BRAND)
    if len(apps) > DROW_MAX:
        f.text(RIGHT_X, DETAIL_TOP + DROW_MAX * DROW_H + 10,
               "另有 %d 个应用未显示" % (len(apps) - DROW_MAX), 11, theme.DIM)


def draw(f, snap, state):
    days = _days()
    if not days:
        f.text(theme.W / 2, 340, EMPTY, 14, theme.DIM, anchor="ma")
        return
    sel = _selected(days, state)
    _draw_days(f, days, sel, _scroll(days, state), state)
    _draw_detail(f, sel, snap)


def on_click(x, y, state, snap):
    days = _days()
    if not days or not (LEFT_X <= x <= LEFT_R):
        return False
    if not (LIST_TOP <= y < LIST_TOP + VISIBLE * ROW_H):
        return False
    i = _scroll(days, state) + int((y - LIST_TOP) // ROW_H)
    if i >= len(days):
        return False
    state["selected_date"] = days[i][0]
    return True


def on_wheel(delta, x, y, state, snap):
    # 只有指针在左列（日期列表）上时滚轮才翻页，右侧明细区不动
    if not (LEFT_X <= x <= LEFT_R):
        return False
    days = _days()
    limit = max(0, len(days) - VISIBLE)
    if limit <= 0:
        return False
    s = _scroll(days, state)
    nxt = max(0, min(limit, s + delta))
    if nxt == s:
        return False
    state["scroll"] = nxt
    return True

def hover(x, y, state, snap):
    days = _days()
    if not days or not (LEFT_X <= x <= LEFT_R):
        return None
    if not (LIST_TOP <= y < LIST_TOP + VISIBLE * ROW_H):
        return None
    i = _scroll(days, state) + int((y - LIST_TOP) // ROW_H)
    return "day_%d" % i if i < len(days) else None