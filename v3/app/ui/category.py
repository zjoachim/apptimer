"""分类页：点一行循环切换分类，直接写 app.category。"""
from .. import config, db, icons, store, theme

MARGIN = 20
RIGHT = theme.W - MARGIN
TOP = 172
ROW_H = 34
ROW_GAP = 16
STEP = ROW_H + ROW_GAP
VISIBLE = 8
HINT_Y = 646
NAME_LIMIT = 34

CATEGORIES = ("未分类", "工作", "学习", "娱乐", "社交", "其他")
PILL_W = 66
PILL_H = 20
PILL_X2 = RIGHT - 12

TODAY_X2 = PILL_X2 - PILL_W - 16
CUM_X2 = TODAY_X2 - 64 - 12


def _rows(snap):
    return db.all_apps(store.connection())


def max_scroll(snap):
    return max(0, len(_rows(snap)) - VISIBLE)


def _clamp(scroll, total):
    return max(0, min(scroll, max(0, total - VISIBLE)))


def _shorten(name):
    return name if len(name) <= NAME_LIMIT else name[:NAME_LIMIT - 1] + "…"


def draw(f, snap, state):
    rows = _rows(snap)
    total = len(rows)
    scroll = _clamp(int(state.setdefault("scroll", 0) or 0), total)
    state["scroll"] = scroll
    tagged = sum(1 for _n, cat, _t, _td in rows if cat)

    p = theme.eased_progress(state)
    f.text(MARGIN, 100, "分类设置", 14, theme.lerp(theme.BG, theme.TEXT, p))
    f.text(RIGHT, 100, "%d 个应用 · 已分类 %d 个" % (total, tagged), 12,
           theme.lerp(theme.BG, theme.DIM, p), anchor="ra")
    f.text(MARGIN, 128, "点击一行循环切换：未分类 → 工作 → 学习 → 娱乐 → 社交 → 其他", 11,
           theme.lerp(theme.BG, theme.DIM, p))
    f.hline(MARGIN, 156, RIGHT, theme.BORDER)

    if not rows:
        f.text(theme.W / 2, 340, "还没有应用数据", 14, theme.DIM, anchor="ma")
        return

    labels = snap.get("labels") or {}
    exes = snap.get("exes") or {}
    icon_dir = config.config_dir() / "icons"
    page = rows[scroll:scroll + VISIBLE]
    y = TOP
    for i, (name, cat, cum, today) in enumerate(page):
        rp = theme.ease_out(max(0.0, min(1.0, (p - i * 0.07) / 0.55)))
        border = theme.lerp(theme.BG, theme.BORDER, rp)
        text_c = theme.lerp(theme.BG, theme.TEXT, rp)
        dim_c = theme.lerp(theme.BG, theme.DIM, rp)
        f.rect(MARGIN, y, RIGHT - MARGIN, ROW_H, outline=border, radius=8)
        ico = icons.load(name, exes.get(name, ""), icon_dir)
        if ico is not None:
            f.image(ico, MARGIN + 12, y + 9, 16, 16)
        f.text(MARGIN + 34, y + 8, _shorten(labels.get(name, name)), 13, text_c)
        f.text(CUM_X2, y + 9, theme.fmt_duration(cum), 12, text_c, anchor="ra", mono=True)
        f.text(TODAY_X2, y + 9, theme.fmt_duration(today) if today > 0 else "", 12,
               dim_c, anchor="ra", mono=True)
        px = PILL_X2 - PILL_W
        shown = cat or "未分类"
        if cat:
            f.rect(px, y + 7, PILL_W, PILL_H, fill=theme.lerp(theme.BG, theme.BRAND_SOFT, rp),
                   outline=theme.lerp(theme.BG, theme.BRAND_EDGE, rp), radius=theme.R_MD)
        else:
            f.rect(px, y + 7, PILL_W, PILL_H, outline=border, radius=10)
        f.circle(px + 11, y + 17, 3, fill=theme.lerp(theme.BG, theme.category_color(shown), rp))
        f.text(px + 18, y + 10, shown, 11, text_c if cat else dim_c)
        y += STEP

    if total > VISIBLE:
        f.text(RIGHT, HINT_Y, "第 %d-%d 项 / 共 %d 项 · 滚轮翻页"
               % (scroll + 1, scroll + len(page), total), 11, theme.DIM, anchor="ra")


def _row_at(x, y, rows, scroll):
    if not (MARGIN <= x <= RIGHT) or y < TOP:
        return None
    idx = int((y - TOP) // STEP)
    if idx < 0 or idx >= VISIBLE:
        return None
    if (y - TOP) - idx * STEP > ROW_H:
        return None
    real = scroll + idx
    return real if real < len(rows) else None


def app_at(x, y, snap, scroll=0):
    """某坐标落在哪个应用上（右键改名用）。"""
    rows = _rows(snap)
    idx = _row_at(x, y, rows, _clamp(int(scroll or 0), len(rows)))
    return rows[idx][0] if idx is not None else None


def on_click(x, y, state, snap):
    rows = _rows(snap)
    idx = _row_at(x, y, rows, _clamp(int(state.get("scroll") or 0), len(rows)))
    if idx is None:
        return False
    name, cat = rows[idx][0], rows[idx][1]
    cur = cat if cat in CATEGORIES else "未分类"
    nxt = CATEGORIES[(CATEGORIES.index(cur) + 1) % len(CATEGORIES)]
    db.set_category(store.connection(), name, "" if nxt == "未分类" else nxt)
    store.bump()
    return True


def on_wheel(delta, x, y, state, snap):
    rows = _rows(snap)
    total = len(rows)
    if total <= VISIBLE:
        return False
    cur = int(state.setdefault("scroll", 0) or 0)
    nxt = _clamp(cur + delta, total)
    state["scroll"] = nxt
    return nxt != cur

def hover(x, y, state, snap):
    name = app_at(x, y, snap, state.get("scroll", 0))
    return ("app_" + name) if name else None
