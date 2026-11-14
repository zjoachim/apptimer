"""累计页：累计总览 + 排行列表（滚轮翻页，一屏 8 行）。"""
from PIL import Image, ImageDraw

from .. import config, icons, theme

MARGIN = 20
RIGHT = theme.W - MARGIN
TOP = 150
ROW_H = 34
ROW_GAP = 16
STEP = ROW_H + ROW_GAP
VISIBLE = 8
BAR_W = 56
NAME_LIMIT = 34
HINT_Y = 646

# 列右边界：从右往左排，行内留 14px 边距给进度条
BAR_X2 = RIGHT - 14
BAR_X1 = BAR_X2 - BAR_W
PCT_X2 = BAR_X1 - 16
TODAY_X2 = PCT_X2 - 58
CUM_X2 = TODAY_X2 - 80
IDX_X2 = MARGIN + 38
NAME_X = MARGIN + 70

_measurer = ImageDraw.Draw(Image.new("RGB", (1, 1)))


def _tw(s, size, mono=False):
    """文字逻辑宽度（用于让「合计」紧贴右对齐的数值）。"""
    return _measurer.textlength(s, font=theme.font(size, mono and s.isascii())) / theme.SCALE


def _rows(snap):
    items = [(name, sec) for name, sec in (snap.get("cumulative") or {}).items() if (sec or 0) > 0]
    items.sort(key=lambda kv: (-kv[1], kv[0]))
    return items


def _bound(total):
    return max(0, total - VISIBLE)


def max_scroll(snap):
    return _bound(len(_rows(snap)))


def _clamp(scroll, total):
    return max(0, min(scroll, _bound(total)))


def _shorten(name):
    return name if len(name) <= NAME_LIMIT else name[:NAME_LIMIT - 1] + "…"


def draw(f, snap, state):
    rows = _rows(snap)
    total = len(rows)
    scroll = _clamp(int(state.setdefault("scroll", 0) or 0), total)
    state["scroll"] = scroll
    used = sum(sec for _, sec in rows)

    head_p = theme.eased_progress(state)
    f.text(MARGIN, 100, "累计应用", 12, theme.lerp(theme.BG, theme.DIM, head_p))
    f.text(MARGIN + _tw("累计应用", 12) + 6, 100, "%d 个" % total, 12,
           theme.lerp(theme.BG, theme.TEXT, head_p))

    value = theme.fmt_duration(used)
    f.text(RIGHT, 100, value, 12, theme.lerp(theme.BG, theme.TEXT, head_p), anchor="ra", mono=True)
    f.text(RIGHT - _tw(value, 12, True) - 8, 100, "合计", 12,
           theme.lerp(theme.BG, theme.DIM, head_p), anchor="ra")

    f.hline(MARGIN, 132, RIGHT, theme.BORDER)

    if not rows:
        f.text(theme.W / 2, 388, "暂无累计数据", 14, theme.DIM, anchor="ma")
        return

    peak = rows[0][1] or 1.0
    usage = snap.get("usage") or {}
    labels = snap.get("labels") or {}
    exes = snap.get("exes") or {}
    icon_dir = config.config_dir() / "icons"
    page = rows[scroll:scroll + VISIBLE]
    p = theme.eased_progress(state)
    y = TOP
    for i, (name, sec) in enumerate(page):
        rp = theme.ease_out(max(0.0, min(1.0, (p - i * 0.07) / 0.55)))
        border = theme.lerp(theme.BG, theme.BORDER, rp)
        text_c = theme.lerp(theme.BG, theme.TEXT, rp)
        dim_c = theme.lerp(theme.BG, theme.DIM, rp)
        f.rect(MARGIN, y, RIGHT - MARGIN, ROW_H, outline=border, radius=theme.R_MD)
        f.text(IDX_X2, y + 9, str(scroll + i + 1), 12, dim_c, anchor="ra", mono=True)
        ico = icons.load(name, exes.get(name, ""), icon_dir)
        if ico is not None:
            f.image(ico, NAME_X - 20, y + 9, 16, 16)
        f.text(NAME_X, y + 8, _shorten(labels.get(name, name)), 13, text_c)
        f.text(CUM_X2, y + 9, theme.fmt_duration(sec), 12, text_c, anchor="ra", mono=True)
        today = usage.get(name) or 0
        if today > 0:
            f.text(TODAY_X2, y + 9, theme.fmt_duration(today), 12, dim_c, anchor="ra", mono=True)
        f.text(PCT_X2, y + 9, "%.1f%%" % (sec / used * 100), 12, dim_c, anchor="ra")
        f.rect(BAR_X1, y + 15, BAR_W, 4, fill=theme.lerp(theme.BG, theme.TRACK, rp))
        f.rect(BAR_X1, y + 16, max(1, int(BAR_W * sec / peak * rp)), 2,
               fill=theme.lerp(theme.BG, theme.BRAND, 0.85 * rp + 0.15))
        y += STEP

    if total > VISIBLE:
        f.text(RIGHT, HINT_Y, "第 %d-%d 项 / 共 %d 项 · 滚轮翻页"
               % (scroll + 1, scroll + len(page), total), 11, theme.DIM, anchor="ra")


def on_click(x, y, state, snap):
    return False


def on_wheel(delta, x, y, state, snap):
    total = len(_rows(snap))
    if total <= VISIBLE:
        return False
    cur = int(state.setdefault("scroll", 0) or 0)
    nxt = _clamp(cur + delta, total)
    state["scroll"] = nxt
    return nxt != cur