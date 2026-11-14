"""图表页：饼图 / 柱状图 × 今日 / 累计（自绘切换控件，纯灰阶）。"""
import math

from .. import theme

MARGIN = 20
RIGHT = theme.W - MARGIN
TOP = 128.0
BOT = theme.H - 16.0

BTN_Y = 91.0
BTN_H = 22.0
BTN_PAD = 12.0
BTN_GAP = 8.0
SEP_W = 18.0

# 调色板随主题变化，绘制时取 theme.PALETTE
GRID = theme.GRID      # 绘制时再取，避免 import 时被冻结
def _leader():
    return theme.lerp(theme.BG, theme.DIM, 0.62)

GROUPS = ((("pie", "饼图"), ("bar", "柱状图")), (("today", "今日"), ("cum", "累计")))

# 轴刻度候选值（秒）：让网格标签落在整分钟/整小时上
LADDER = (1, 2, 5, 10, 15, 20, 30, 45, 60, 120, 300, 600, 900, 1200, 1800, 2700
          ) + tuple(h * 3600 for h in (1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96,
                                       120, 168, 240, 336, 504, 720))

_wcache = {}


def _text_w(s, size):
    scale = theme.SCALE or 1.0
    key = (s, round(size, 2), round(scale, 3))
    v = _wcache.get(key)
    if v is None:
        v = theme.font(size).getlength(s) / scale
        _wcache[key] = v
    return v


def _fit(s, size, max_w):
    if not s or _text_w(s, size) <= max_w:
        return s
    cut = s
    while cut and _text_w(cut + "..", size) > max_w:
        cut = cut[:-1]
    return (cut + "..") if cut else ".."


def _strip_exe(name):
    n = name or ""
    return n[:-4] if n.lower().endswith(".exe") else n


def _xlabel(name, size, max_w):
    s = _strip_exe(name)
    if len(s) > 10:
        s = s[:8] + ".."
    return _fit(s, size, max_w)


def _series(snap, scope):
    table = snap.get("cumulative" if scope == "cum" else "usage") or {}
    items = [(k, float(v or 0)) for k, v in table.items() if float(v or 0) > 0]
    items.sort(key=lambda kv: kv[1], reverse=True)
    return items[:10]


def _tabs_layout():
    widths = [[_text_w(label, 12) + BTN_PAD * 2 for _key, label in g] for g in GROUPS]
    gaps = sum(len(g) - 1 for g in GROUPS) + (len(GROUPS) - 1)
    total = sum(sum(w) for w in widths) + BTN_GAP * gaps + SEP_W * (len(GROUPS) - 1)
    x = (theme.W - total) / 2.0
    rects = []
    sep_x = 0.0
    for gi, group in enumerate(GROUPS):
        if gi:
            x += BTN_GAP
            sep_x = x + SEP_W / 2.0
            x += SEP_W
        for i, (key, label) in enumerate(group):
            if i:
                x += BTN_GAP
            w = widths[gi][i]
            rects.append((key, label, x, BTN_Y, w, BTN_H))
            x += w
    return rects, sep_x


def _draw_tabs(f, chart_type, scope):
    rects, sep_x = _tabs_layout()
    for key, label, x, y, w, h in rects:
        if key == chart_type or key == scope:
            f.rect(x, y, w, h, fill=theme.BRAND_SOFT, outline=theme.BRAND_EDGE, radius=theme.R_PILL)
            f.text_centered(x + w / 2, y + h / 2, label, 12, theme.TEXT)
        else:
            f.rect(x, y, w, h, outline=theme.BORDER, radius=11)
            f.text_centered(x + w / 2, y + h / 2, label, 12, theme.DIM)
    f.line(sep_x, BTN_Y + 5, sep_x, BTN_Y + BTN_H - 5, theme.DIM)


def _empty_text(scope):
    return "今日暂无记录" if scope == "today" else "暂无累计数据"


def _spread(ys, top, bottom, gap):
    ys = list(ys)
    for i in range(1, len(ys)):
        if ys[i] < ys[i - 1] + gap:
            ys[i] = ys[i - 1] + gap
    if ys and ys[-1] > bottom:
        d = ys[-1] - bottom
        ys = [y - d for y in ys]
    for i in range(len(ys) - 2, -1, -1):
        ys[i] = min(ys[i], ys[i + 1] - gap)
    if ys and ys[0] < top:
        d = top - ys[0]
        ys = [y + d for y in ys]
    return ys


def _draw_pie(f, data, scope, p=1.0):
    cx = theme.W / 2.0
    cy = TOP + (BOT - TOP) * 0.48
    r = min(RIGHT - MARGIN, BOT - TOP) * 0.36
    if not data:
        f.text(cx, cy - 8, _empty_text(scope), 14, theme.DIM, anchor="ma")
        return

    total = sum(sec for _name, sec in data) or 1.0
    reveal = 360.0 * p
    angle = -90.0
    mids = []
    for i, (name, sec) in enumerate(data):
        sweep = 360.0 * sec / total
        vis_end = min(angle + sweep, -90.0 + reveal)
        if vis_end > angle:
            f.sector(cx, cy, r, angle, vis_end, theme.PALETTE[i % len(theme.PALETTE)])
        mids.append((name, angle + sweep / 2.0))
        angle += sweep
    f.circle(cx, cy, r * 45.0 / 70.0, fill=theme.BG)

    label_a = max(0.0, min(1.0, (p - 0.55) / 0.45))
    if label_a <= 0.01:
        return
    leader_c = theme.lerp(theme.BG, _leader(), label_a)
    label_c = theme.lerp(theme.BG, theme.DIM, label_a)

    sides = {1: [], -1: []}
    for name, mid in mids:
        a = math.radians(mid)
        dx, dy = math.cos(a), math.sin(a)
        p0 = (cx + dx * (r + 4), cy + dy * (r + 4))
        p1 = (cx + dx * (r + 20), cy + dy * (r + 20))
        sides[1 if dx >= 0 else -1].append((name, p0, p1, p1[1]))

    for side, items in sides.items():
        if not items:
            continue
        items.sort(key=lambda it: it[3])
        ys = _spread([it[3] for it in items], TOP + 6, BOT - 8, 13.0)
        elbow = cx + side * (r + 26)
        for (name, p0, p1, _y), yc in zip(items, ys):
            f.line(p0[0], p0[1], p1[0], p1[1], leader_c)
            f.line(p1[0], p1[1], elbow, yc, leader_c)
            max_w = (RIGHT - elbow - 8) if side > 0 else (elbow - 8 - MARGIN)
            label = _fit(name, 10, max_w)
            if side > 0:
                f.text(elbow + 8, yc - 5, label, 10, label_c)
            else:
                f.text(elbow - 8, yc - 5, label, 10, label_c, anchor="ra")


def _nice_step(raw):
    """把步长收到「好看」的时长刻度上，轴上不会出现 13m 20s。"""
    if raw <= 0:
        return 1.0
    for sec in LADDER:
        if sec >= raw:
            return float(sec)
    base = 10.0 ** math.floor(math.log10(raw))
    for m in (1, 2, 5, 10):
        if m * base >= raw:
            return float(m * base)
    return 10.0 * base


def _draw_bar(f, data, scope, p=1.0):
    x1, x2 = 62.0, RIGHT - 24
    y_top, y_bot = 138.0, BOT - 62.0
    if not data:
        f.text((x1 + x2) / 2, (y_top + y_bot) / 2 - 8, _empty_text(scope), 14, theme.DIM, anchor="ma")
        return

    span = y_bot - y_top
    step = _nice_step(max(sec for _name, sec in data) * 1.12 / 4.0)
    gmax = step * 4.0
    for i in range(5):
        y = y_bot - span * i / 4.0
        f.hline(x1, y, x2, theme.GRID)
        f.text(x1 - 8, y - 6, theme.fmt_duration(int(round(step * i))), 10, theme.DIM, anchor="ra")

    slot = (x2 - x1) / len(data)
    bar_w = min(slot * 0.5, 72.0)
    for i, (name, sec) in enumerate(data):
        bcx = x1 + slot * (i + 0.5)
        h = span * sec / gmax * p
        top = y_bot - h
        if h >= 1.0:
            f.rect(bcx - bar_w / 2, top, bar_w, h, fill=theme.PALETTE[i % len(theme.PALETTE)], radius=theme.R_TINY)
        if p > 0.85:
            f.text(bcx, top - 14, theme.fmt_duration(sec), 10, theme.DIM, anchor="ma")
        f.text(bcx, y_bot + 9, _xlabel(name, 9, min(slot - 8, 120.0)), 9, theme.DIM, anchor="ma")


def draw(f, snap, state):
    chart_type = state.setdefault("chart_type", "pie")
    scope = state.setdefault("scope", "today")
    _draw_tabs(f, chart_type, scope)
    data = _series(snap, scope)
    p = theme.eased_progress(state)
    if chart_type == "bar":
        _draw_bar(f, data, scope, p)
    else:
        _draw_pie(f, data, scope, p)


def on_click(x, y, state, snap):
    state.setdefault("chart_type", "pie")
    state.setdefault("scope", "today")
    rects, _sep = _tabs_layout()
    for key, _label, bx, by, bw, bh in rects:
        if bx <= x <= bx + bw and by <= y <= by + bh:
            field, value = ("chart_type", key) if key in ("pie", "bar") else ("scope", key)
            if state.setdefault(field, None) == value:
                return False
            state[field] = value
            theme.anim_start(state)
            return True
    return False


def on_wheel(delta, x, y, state, snap):
    return False