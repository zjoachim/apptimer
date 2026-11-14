"""时段页：今日 24 小时分布 + 最近 7 天 × 24 小时热力。"""
from datetime import datetime, timedelta

from .. import db, store, theme

MARGIN = 20
RIGHT = theme.W - MARGIN
HOURS = 24

TODAY_TOP = 132
TODAY_BOT = 316
HEAT_TOP = 392
HEAT_ROW = 26
HEAT_ROWS = 7
CELL_GAP = 2

LEFT_LABEL_W = 44


def _cell_w():
    return (RIGHT - MARGIN - LEFT_LABEL_W) / HOURS


def _today_data():
    conn = store.connection()
    today = datetime.now().strftime("%Y-%m-%d")
    return db.day_hours(conn, today)


def _week_data():
    conn = store.connection()
    data = db.recent_hours(conn, days=HEAT_ROWS)
    today = datetime.now()
    days = [(today - timedelta(days=HEAT_ROWS - 1 - i)).strftime("%Y-%m-%d")
            for i in range(HEAT_ROWS)]
    return [(d, data.get(d, {})) for d in days]


def draw(f, snap, state):
    p = theme.eased_progress(state)
    hours = {int(ts[11:13]): sec for ts, sec in _today_data()}
    total = sum(hours.values())
    peak_hour = max(hours, key=lambda h: hours[h]) if hours else None

    f.text(MARGIN, 100, "今日时段分布", 14, theme.lerp(theme.BG, theme.TEXT, p))
    f.text(RIGHT, 100, "合计 %s" % theme.fmt_duration(total), 12,
           theme.lerp(theme.BG, theme.DIM, p), anchor="ra")
    if peak_hour is not None and hours.get(peak_hour, 0) > 0:
        f.text(MARGIN, 122, "高峰 %02d:00–%02d:00 · %s" % (
            peak_hour, peak_hour + 1, theme.fmt_duration(hours[peak_hour])), 11, theme.DIM)
    f.hline(MARGIN, 140, RIGHT, theme.BORDER)

    # 今日 24 小时柱
    top, bottom = 160, 330
    span = bottom - top
    cw = _cell_w()
    for h in range(HOURS):
        sec = hours.get(h, 0.0)
        x = MARGIN + LEFT_LABEL_W + h * cw
        hgt = span * min(1.0, sec / 3600.0) * p
        if hgt >= 1:
            f.rect(x + CELL_GAP / 2, bottom - hgt, cw - CELL_GAP, hgt,
                   fill=theme.lerp(theme.TRACK_SOFT, theme.HEAT_HI, min(1.0, sec / 3600.0)))
        if h % 3 == 0:
            f.text(x + cw / 2, bottom + 8, "%02d" % h, 9, theme.DIM, anchor="ma")
    f.text(MARGIN, top - 14, "1h", 9, theme.DIM)
    f.text(MARGIN, bottom - 6, "0", 9, theme.DIM)
    f.hline(MARGIN + LEFT_LABEL_W, bottom, RIGHT, theme.BORDER)
    if total <= 0:
        f.text(theme.W / 2, (top + bottom) / 2, "今天还没有记录", 12, theme.DIM, anchor="ma")

    # 最近 7 天热力
    f.text(MARGIN, 372, "最近 7 天时段热力", 12, theme.DIM, spacing=0.6)
    week = _week_data()
    heat_w = _cell_w()
    for i in range(HOURS):
        if i % 3 == 0:
            f.text(MARGIN + LEFT_LABEL_W + i * heat_w + heat_w / 2, 394, "%02d" % i,
                   9, theme.DIM, anchor="ma")
    for r, (date, cell) in enumerate(week):
        y = HEAT_TOP + r * HEAT_ROW
        label = date[5:]
        f.text(MARGIN, y + 2, label, 10, theme.DIM)
        for h in range(HOURS):
            sec = cell.get(h, 0.0)
            ratio = min(1.0, sec / 3600.0)
            x = MARGIN + LEFT_LABEL_W + h * heat_w
            color = theme.lerp(theme.HEAT_LO, theme.HEAT_HI, ratio)
            f.rect(x + CELL_GAP / 2, y, heat_w - CELL_GAP, HEAT_ROW - 6, fill=color, radius=theme.R_TINY)

    f.text(RIGHT, HEAT_TOP + HEAT_ROWS * HEAT_ROW + 12,
           ("颜色越浅 = 该小时使用越久（上限按 1 小时算）" if theme.MODE == "light" else "颜色越亮 = 该小时使用越久（上限按 1 小时算）"), 10, theme.DIM, anchor="ra")


def on_click(x, y, state, snap):
    return False


def on_wheel(delta, x, y, state, snap):
    return False