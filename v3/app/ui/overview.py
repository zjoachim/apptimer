"""概览页：大号总时长、分类胶囊、应用列表（可滚轮翻页）。"""
from PIL import Image, ImageDraw

from .. import config, icons, theme

_meas = ImageDraw.Draw(Image.new("RGB", (1, 1)))


def _tw(s, size=12):
    """按实际字体量文本宽度（中英文一起算，避免按字符数估宽撑破胶囊）。"""
    return _meas.textlength(s, font=theme.font(size)) / max(1.0, theme.SCALE)

TOP = 250
ROW_H = 34
ROW_GAP = 16
STEP = ROW_H + ROW_GAP
MARGIN = 20
BAR_W = 56
EXPORT_W, EXPORT_H = 66, 22
EXPORT_X = theme.W - MARGIN - EXPORT_W


def export_hit(x, y, shift=0):
    """分类胶囊行右端的「导出 PDF」按钮。"""
    return (EXPORT_X <= x <= EXPORT_X + EXPORT_W
            and 186 + shift <= y <= 186 + shift + EXPORT_H)


def visible_rows():
    return max(1, int((theme.H - MARGIN - TOP) // STEP))


def _rows(snap):
    items = sorted(snap["usage"].items(), key=lambda kv: kv[1], reverse=True)
    return items


def max_scroll(snap):
    return max(0, len(_rows(snap)) - visible_rows())


def _category_pills(snap):
    totals = {}
    for app, sec in snap["usage"].items():
        cat = snap["categories"].get(app) or "未分类"
        totals[cat] = totals.get(cat, 0.0) + sec
    total = sum(totals.values()) or 1.0
    return sorted(((c, s / total) for c, s in totals.items()), key=lambda kv: kv[1], reverse=True)


def _goal_progress(snap):
    """返回 (说明文字, 完成比例, 剩余文字)；预算关闭或未设定返回 None。"""
    if not config.goal_enabled():
        return None
    goal = config.get_goal()
    if goal <= 0:
        return None
    used = snap.get("total") or 0
    ratio = used / goal
    label = "今日预算 %s" % theme.fmt_minutes(goal)
    if used >= goal:
        left = "已超出 %s" % theme.fmt_minutes(used - goal)
    else:
        left = "还剩 %s" % theme.fmt_minutes(goal - used)
    return label, ratio, left


def draw(f, snap, scroll=0, pill_a=1.0, row_a=None, hover=None):
    f.text(theme.W / 2, 88, theme.fmt_duration(snap["total"]), 30, theme.TEXT,
           anchor="ma", spacing=2.0, light=True)
    f.text(theme.W / 2, 132, "今日总使用时间", 12, theme.DIM, anchor="ma")

    goal = _goal_progress(snap)
    shift = 0
    if goal:
        label, ratio, left_text = goal
        over = ratio >= 1.0
        color = theme.OVER if over else theme.GOOD
        f.text(theme.W / 2, 158, "%s · %s" % (label, left_text), 11, color, anchor="ma")
        bar_w = 220
        bx = (theme.W - bar_w) / 2
        f.rect(bx, 178, bar_w, 4, fill=theme.TRACK_SOFT, radius=theme.R_TINY)
        f.rect(bx, 178, max(2, int(bar_w * min(1.0, ratio))), 4, fill=color, radius=theme.R_TINY)
        shift = 14

    pills = _category_pills(snap)
    if pills and pill_a > 0:
        x = MARGIN
        shown = 0
        limit = EXPORT_X - 8
        for cat, ratio in pills[:6]:
            label = "%s %d%%" % (cat, round(ratio * 100))
            w = 20 + _tw(label) + 14          # 圆点 + 文字实测宽度 + 左右留白
            if x + w > limit:
                break
            f.rect(x, 186 + shift, w, 22, fill=theme.lerp(theme.BG, theme.ACCENT, pill_a), radius=theme.R_PILL)
            f.circle(x + 12, 197 + shift, 3,
                     fill=theme.lerp(theme.BG, theme.category_color(cat), pill_a))
            f.text(x + 20, 190 + shift, label, 12, theme.lerp(theme.BG, theme.DIM, pill_a))
            x += w + 6
            shown += 1
        rest = len(pills) - shown
        if rest > 0 and x + _tw("+%d" % rest) + 6 < limit:
            f.text(x + 2, 190 + shift, "+%d" % rest, 12, theme.DIM)

    hot = hover == "export_pdf"
    f.rect(EXPORT_X, 186 + shift, EXPORT_W, EXPORT_H,
           fill=theme.BRAND_SOFT if hot else None,
           outline=theme.BRAND_EDGE if hot else theme.BORDER, radius=theme.R_PILL, width=1)
    f.text_centered(EXPORT_X + EXPORT_W / 2, 186 + shift + EXPORT_H / 2, "导出 PDF", 11,
                    theme.TEXT if hot else theme.DIM)

    f.hline(MARGIN, 233 + shift, theme.W - MARGIN, theme.BORDER)

    rows = _rows(snap)[scroll:scroll + visible_rows()]
    labels = snap.get("labels") or {}
    exes = snap.get("exes") or {}
    icon_dir = config.config_dir() / "icons"
    total = snap["total"] or 1.0
    right = theme.W - MARGIN
    bar_x2 = right - 12
    bar_x1 = bar_x2 - BAR_W
    pct_x2 = bar_x1 - 12
    cum_x2 = pct_x2 - 40 - 12
    today_x2 = cum_x2 - 64 - 12
    cat_x2 = today_x2 - 64 - 12

    y = TOP + shift
    for i, (app, sec) in enumerate(rows):
        a = 1.0 if row_a is None else row_a[i]
        if a <= 0:
            y += STEP
            continue
        ratio = min(1.0, sec / total)
        f.rect(MARGIN, y, theme.W - MARGIN * 2, ROW_H, outline=theme.lerp(theme.BG, theme.BORDER, a), radius=theme.R_MD)
        col = theme.lerp(theme.BG, theme.TEXT, a)
        cdim = theme.lerp(theme.BG, theme.DIM, a)
        ico = icons.load(app, exes.get(app, ""), icon_dir)
        if ico is not None:
            f.image(ico, MARGIN + 12, y + 9, 16, 16)
        f.text(MARGIN + 34, y + 8, labels.get(app, app), 13, col)
        f.text(cat_x2, y + 9, snap["categories"].get(app, ""), 12, cdim, anchor="ra")
        f.text(today_x2, y + 9, theme.fmt_hm(sec), 12, col, anchor="ra", mono=True)
        f.text(cum_x2, y + 9, theme.fmt_hm(snap["cumulative"].get(app, 0)), 12, cdim,
               anchor="ra", mono=True)
        f.text(pct_x2, y + 9, "%.1f%%" % (sec / total * 100), 12, cdim, anchor="ra", mono=True)
        # 进度条：整条轨道 + 覆盖填充，都不用圆角，保证每行左端像素级对齐
        f.rect(bar_x1, y + 15, BAR_W, 4, fill=theme.lerp(theme.BG, theme.TRACK, a))
        f.rect(bar_x1, y + 15, max(2, int(round(BAR_W * ratio))), 4,
               fill=theme.lerp(theme.BG, theme.BRAND, 0.85 * a + 0.15))
        y += STEP

    remaining = len(_rows(snap)) - scroll - len(rows)
    if scroll > 0 or remaining > 0:
        f.text(theme.W - MARGIN, theme.H - 22, "第 %d-%d 项 / 共 %d 项 · 滚轮翻页"
               % (scroll + 1, scroll + len(rows), len(_rows(snap))), 11, theme.DIM, anchor="ra")

    if 0 < len(rows) < visible_rows():
        _draw_summary(f, snap, TOP + shift + len(rows) * STEP + 16)

    if not snap["usage"]:
        f.text(theme.W / 2, 380 + shift, "今日暂无记录 · 有动静就会开始计时", 12,
               theme.DIM, anchor="ma")
        f.text(theme.W / 2, 404 + shift, "（空闲超过 2 分钟会暂停计时，看视频有声则继续）",
               11, theme.DIM, anchor="ma")

def _draw_summary(f, snap, y):
    """今日小结三格：用得最多 / 峰值时段 / 预算差额。只在列表没占满时出现。"""
    ordered = _rows(snap)
    top_app, top_sec = ordered[0] if ordered else ("-", 0)
    labels = snap.get("labels") or {}

    hours = {}
    try:
        from .. import db, store
        for ts, sec in db.day_hours(store.connection(), snap.get("date")):
            hours[int(ts[11:13])] = hours.get(int(ts[11:13]), 0) + float(sec)
    except Exception:
        hours = {}
    peak = max(hours, key=lambda k: hours[k]) if hours else None
    peak_text = ("%02d:00 · %s" % (peak, theme.fmt_hm(hours[peak]))) if peak is not None else "-"

    goal = config.get_goal()
    if goal and config.goal_enabled():
        left = goal - (snap.get("total") or 0)
        budget_text = ("还剩 %s" % theme.fmt_minutes(left)) if left > 0 else (
            "已超出 %s" % theme.fmt_minutes(-left))
        budget_color = theme.GOOD if left > 0 else theme.OVER
    else:
        budget_text, budget_color = "未设预算", theme.DIM

    cells = (
        ("用得最多", "%s · %s" % (labels.get(top_app, top_app)[:20], theme.fmt_hm(top_sec)),
         theme.TEXT),
        ("峰值时段", peak_text, theme.TEXT),
        ("今日预算", budget_text, budget_color),
    )
    f.hline(MARGIN, y, theme.W - MARGIN, theme.BORDER)
    col_w = (theme.W - MARGIN * 2) / 3.0
    for i, (label, value, color) in enumerate(cells):
        x = MARGIN + i * col_w
        f.text(x, y + 14, label, 11, theme.DIM, spacing=0.6)
        f.text(x, y + 36, value, 12, color)