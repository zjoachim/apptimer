"""趋势页：单个应用最近 14 天的逐日折线。"""
from datetime import datetime, timedelta

from .. import db, store, theme

DAYS = 14
BTN_W = 26
BTN_H = 26
BTN_Y = 94
BTN_PREV = 20
BTN_NEXT = BTN_PREV + BTN_W + 4
NAME_X = BTN_NEXT + BTN_W + 12
HEAD_CY = BTN_Y + BTN_H / 2
RIGHT_X = theme.W - 20

C_L, C_R, C_T, C_B = 62, 856, 150, 600
YLABEL_X = 56
GRID_N = 5
MAX_LABELS = 7

# 应用下拉选择面板
PICK_W = 300
PICK_ROW = 26
PICK_VISIBLE = 10
PICK_X = NAME_X - 4
PICK_Y = BTN_Y + BTN_H + 8
NAME_HIT_W = 260
# 折线颜色在绘制时取 theme.LINE，避免 import 时被冻结
EMPTY = "暂无趋势数据"

# 纵轴上限的候选步长：step*4 是顶端数值，保证四等分标签是整分整时
_STEPS = (60, 120, 300, 600, 900, 1200, 1800, 2700, 3600,
          5400, 7200, 10800, 14400, 21600, 28800, 43200)


def _apps(snap):
    items = sorted(snap["cumulative"].items(), key=lambda kv: (-kv[1], kv[0]))
    return [name for name, _ in items]


def _index(state, n):
    try:
        i = int(state.get("app_index") or 0)
    except (TypeError, ValueError):
        i = 0
    i = max(0, min(n - 1, i))
    state["app_index"] = i
    return i


def _today(snap):
    try:
        return datetime.strptime(snap.get("date") or "", "%Y-%m-%d")
    except (TypeError, ValueError):
        return datetime.now()


def _series(snap, name):
    """补齐成连续 14 天：库里没记录的日子算 0。"""
    rows = dict(db.app_daily(store.connection(), name, days=DAYS))
    today = _today(snap)
    days = [today - timedelta(days=DAYS - 1 - i) for i in range(DAYS)]
    return ([int(rows.get(d.strftime("%Y-%m-%d"), 0)) for d in days],
            [d.strftime("%m-%d") for d in days])


def _smooth(pts, seg=14):
    """Catmull-Rom 采样，接近 ECharts 的 smooth:true。"""
    if len(pts) < 3:
        return list(pts)
    ext = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for s in range(seg):
            t = s / float(seg)
            t2, t3 = t * t, t * t * t
            x = 0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    out.append(pts[-1])
    return out


def _tw(s, size, mono=False):
    return theme.font(size, mono).getlength(s) / (theme.SCALE or 1.0)


def _picker_visible(apps):
    return max(1, min(PICK_VISIBLE, len(apps)))


def _picker_scroll(state, idx, total):
    vis = _picker_visible([0] * total)
    scroll = int(state.get("picker_scroll") or 0)
    if idx < scroll:
        scroll = idx
    elif idx >= scroll + vis:
        scroll = idx - vis + 1
    scroll = max(0, min(scroll, max(0, total - vis)))
    state["picker_scroll"] = scroll
    return scroll


def _picker_hit(x, y, apps, state):
    """返回被点中的应用索引；点在面板外返回 -1；没命中面板返回 None。"""
    vis = _picker_visible(apps)
    scroll = int(state.get("picker_scroll") or 0)
    h = vis * PICK_ROW + 8
    if not (PICK_X <= x <= PICK_X + PICK_W and PICK_Y <= y <= PICK_Y + h):
        return None
    row = int((y - PICK_Y - 4) // PICK_ROW)
    if row < 0 or row >= vis:
        return -1
    real = scroll + row
    return real if real < len(apps) else -1


def _draw_picker(f, apps, idx, state, labels):
    vis = _picker_visible(apps)
    scroll = _picker_scroll(state, idx, len(apps))
    h = vis * PICK_ROW + 8
    f.rect(PICK_X, PICK_Y, PICK_W, h, fill=theme.PANEL, outline=theme.BORDER, radius=theme.R_MD, width=1)
    for i in range(vis):
        real = scroll + i
        if real >= len(apps):
            break
        y = PICK_Y + 4 + i * PICK_ROW
        on = real == idx
        if on:
            f.rect(PICK_X + 4, y, PICK_W - 8, PICK_ROW, fill=theme.BRAND_SOFT, radius=theme.R_SM)
        text = labels.get(apps[real], apps[real])
        f.text(PICK_X + 12, y + 6, text[:32], 12, theme.TEXT if on else theme.DIM)
    if len(apps) > vis:
        f.text(PICK_X + PICK_W - 10, PICK_Y + h - 16, "滚轮翻页", 10, theme.DIM, anchor="ra")


def _top(peak):
    for step in _STEPS:
        if step * (GRID_N - 1) >= peak:
            return step * (GRID_N - 1)
    step = (int(peak / (GRID_N - 1) / 3600) + 1) * 3600
    return step * (GRID_N - 1)


def draw(f, snap, state):
    apps = _apps(snap)
    if not apps:
        f.text(theme.W / 2, 340, EMPTY, 14, theme.DIM, anchor="ma")
        return

    idx = _index(state, len(apps))
    for bx, glyph, live in ((BTN_PREV, "\u2039", idx > 0),
                            (BTN_NEXT, "\u203a", idx < len(apps) - 1)):
        f.rect(bx, BTN_Y, BTN_W, BTN_H, outline=theme.BORDER, radius=theme.R_MD, width=1)
        f.text_centered(bx + BTN_W / 2, HEAD_CY, glyph, 14,
                        theme.TEXT if live else theme.DIM)
    labels_map = snap.get("labels") or {}
    shown = labels_map.get(apps[idx], apps[idx])
    f.text(NAME_X, HEAD_CY - 8, shown, 14, theme.TEXT)
    tri = NAME_X + _tw(shown, 14) + 9
    ty = HEAD_CY - 2
    f.line(tri, ty, tri + 9, ty, theme.DIM)
    f.line(tri, ty, tri + 4.5, ty + 5, theme.DIM)
    f.line(tri + 9, ty, tri + 4.5, ty + 5, theme.DIM)
    f.text(RIGHT_X, HEAD_CY - 7, "最近 %d 天" % DAYS, 11, theme.DIM, anchor="ra")

    values, labels = _series(snap, apps[idx])
    peak = max(values)
    if peak <= 0:
        f.text((C_L + C_R) / 2, (C_T + C_B) / 2, EMPTY, 14, theme.DIM, anchor="ma")
        if state.get("picker"):
            _draw_picker(f, apps, idx, state, labels_map)
        return

    top = _top(peak)
    for i in range(GRID_N):
        y = C_B - (C_B - C_T) * i / (GRID_N - 1)
        f.hline(C_L, y, C_R, theme.BORDER)
        f.text(YLABEL_X, y - 6, theme.fmt_duration(top * i / (GRID_N - 1)),
               10, theme.DIM, anchor="ra")

    n = len(values)
    step = (C_R - C_L) / (n - 1)
    pts = [(C_L + i * step, C_B - (C_B - C_T) * v / top) for i, v in enumerate(values)]
    curve = [(x, max(C_T, min(C_B, y))) for x, y in _smooth(pts)]
    p = theme.eased_progress(state)
    cut = max(2, int(round(len(curve) * p)))
    for (x1, y1), (x2, y2) in zip(curve[:cut - 1], curve[1:cut]):
        f.line(x1, y1, x2, y2, theme.LINE, 2)
    reached = max(1, int(round((n - 1) * p)) + 1)
    for x, y in pts[:reached]:
        f.circle(x, y, 2.5, fill=theme.LINE)

    every = -(-n // MAX_LABELS)
    for i in range(0, n, every):
        f.text(pts[i][0], C_B + 15, labels[i], 9, theme.DIM, anchor="ma")

    if state.get("picker"):
        _draw_picker(f, apps, idx, state, labels_map)


def on_click(x, y, state, snap):
    apps = _apps(snap)
    if not apps:
        return False
    idx = _index(state, len(apps))

    if state.get("picker"):
        hit = _picker_hit(x, y, apps, state)
        if hit is None:
            state["picker"] = False        # 点面板外：关闭
            return True
        state["picker"] = False
        if hit >= 0 and hit != idx:
            state["app_index"] = hit
            theme.anim_start(state)
        return True

    if not (BTN_Y <= y <= BTN_Y + BTN_H):
        return False
    if NAME_X - 4 <= x <= NAME_X + NAME_HIT_W:
        state["picker"] = True
        _picker_scroll(state, idx, len(apps))
        return True
    if BTN_PREV <= x <= BTN_PREV + BTN_W:
        target = idx - 1
    elif BTN_NEXT <= x <= BTN_NEXT + BTN_W:
        target = idx + 1
    else:
        return False
    target = max(0, min(len(apps) - 1, target))
    if target == idx:
        return False
    state["app_index"] = target
    theme.anim_start(state)
    return True


def on_wheel(delta, x, y, state, snap):
    if not state.get("picker"):
        return False
    apps = _apps(snap)
    vis = _picker_visible(apps)
    if len(apps) <= vis:
        return False
    cur = int(state.get("picker_scroll") or 0)
    nxt = max(0, min(cur + delta, len(apps) - vis))
    state["picker_scroll"] = nxt
    return nxt != cur