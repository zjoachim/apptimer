"""顶栏 + tab 导航。"""
from PIL import Image, ImageDraw

from .. import theme

TABS = ["概览", "累计", "图表", "时段", "趋势", "分类", "历史", "番茄钟", "设置"]
_geo = {}
_measurer = ImageDraw.Draw(Image.new("RGB", (1, 1)))


def nav_geometry():
    if _geo:
        return _geo
    x = 20
    for t in TABS:
        w = _measurer.textlength(t, font=theme.font(12)) / theme.SCALE + 26
        _geo[t] = (x, w)
        x += w
    return _geo


def _tw(s, size=12, mono=False):
    if not s:
        return 0.0
    return _measurer.textlength(s, font=theme.font(size, mono and s.isascii())) / theme.SCALE


def _fit(s, max_w, size=12):
    """超宽就截断加省略号（按实测宽度，不是按字符数）。"""
    if not s or max_w <= 0:
        return ""
    if _tw(s, size) <= max_w:
        return s
    cut = s
    while cut and _tw(cut + "…", size) > max_w:
        cut = cut[:-1]
    return (cut + "…") if cut else ""


def nav_hit(x, y):
    if not (44 <= y <= 78):
        return None
    for t, (nx, nw) in nav_geometry().items():
        if nx <= x <= nx + nw:
            return t
    return None


def header_items():
    """从右往左：退出 → 主题开关。"""
    mode_label = "亮色" if theme.MODE == "dark" else "深色"
    return (("quit", "退出", 44), ("toggle_theme", mode_label, 48))


def header_buttons():
    bx = theme.W - 20
    out = []
    for action, label, w in header_items():
        bx -= w
        out.append((action, label, bx, w))
        bx -= 8
    return out


def header_hit(x, y):
    if not (11 <= y <= 33):
        return None
    for action, _label, bx, w in header_buttons():
        if bx <= x <= bx + w:
            return action
    return None


def draw_shell(f, active, header):
    f.hline(0, 43, theme.W, theme.BORDER)
    f.text(20, 15, "AppTimer", 12, theme.TEXT, spacing=0.7)

    hover = header.get("hover")
    hot_header = hover[1] if hover and hover[0] == "header" else None
    hot_nav = hover[1] if hover and hover[0] == "nav" else None
    for key, label, bx, w in header_buttons():
        hot = hot_header == key
        f.rect(bx, 11, w, 22, fill=theme.BRAND_SOFT if hot else None,
               outline=theme.BRAND_EDGE if hot else theme.BORDER, radius=theme.R_PILL, width=1)
        f.text_centered(bx + w / 2, 22, label, 12, theme.TEXT if hot else theme.DIM)

    # 右侧信息从右往左按实测宽度排布，应用名过长时截断，绝不与日期重叠
    total_text = header.get("total_text", "")
    app = header.get("current_app") or "空闲"
    date = header.get("date", "")

    # 右侧信息从「退出」左侧往左排，依次：总时长 → 应用名 → 日期
    right_limit = min(x for _a, _l, x, _w in header_buttons()) - 16
    # 等宽字体与雅黑的基线差一两个像素，用墨迹中心校正后再画，保证三行文字平行
    tw_total = _tw(total_text, 12, True)
    dy = theme.ink_center(date, 12) - theme.ink_center(total_text, 12, True)
    f.text(right_limit - tw_total, 15 + dy, total_text, 12, theme.TEXT, mono=True)

    tw_date = _tw(date, 12)
    app_right = right_limit - tw_total - 16
    app_room = app_right - 16 - tw_date - 100     # 100 = "AppTimer" 标题的预留
    app_text = _fit(app, app_room, 12)
    if app_text:
        f.text(app_right - _tw(app_text, 12), 15, app_text, 12, theme.DIM)

    x_date = app_right - (_tw(app_text, 12) + 16 if app_text else 0) - tw_date
    f.text(x_date, 15, date, 12, theme.DIM)

    f.hline(0, 77, theme.W, theme.BORDER)
    geo = nav_geometry()
    nav_hot = hot_nav
    for t in TABS:
        nx, nw = geo[t]
        color = theme.BRAND if t == active else (
            theme.TEXT if nav_hot == t else theme.DIM)
        f.text(nx + nw / 2, 54, t, 12, color, anchor="ma", spacing=0.5)
    nx, nw = geo[active]
    f.hline(nx + 8, 76, nx + nw - 8, theme.BRAND)