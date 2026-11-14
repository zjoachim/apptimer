"""设计令牌 + 画布合成器（形状层超采样、文字层直绘）。"""
import os
import time

from PIL import Image, ImageDraw, ImageFont

W, H = 900, 680

# 圆角：整体比之前更"直"一点
R_TINY = 1      # 细条
R_SM = 3        # 小胶囊/进度轨道
R_MD = 5        # 列表行、按钮、面板
R_PILL = 8      # 分类胶囊、顶栏按钮
R_TOAST = 10     # 底部提示条

# 两套色板：深色（与 v2 的 frontend/src/style.css 对齐）/ 亮色
DARK = {
    "BG": (8, 8, 13),
    "TEXT": (217, 217, 222),
    "DIM": (138, 138, 146),     # 对比度 5.83:1（旧值 107 只有 3.78:1，小字看着发虚）
    "BORDER": (42, 42, 52),
    "ACCENT": (35, 35, 43),
    "PANEL": (16, 16, 22),      # 弹出面板底
    "TRACK": (32, 32, 41),      # 进度条轨道
    "FILL": (176, 176, 188),    # 进度条填充
    "TRACK_SOFT": (34, 34, 42),  # 粗一点的分段条底
    "HEAT_LO": (26, 26, 33),    # 热力图最低
    "HEAT_HI": (232, 232, 238),  # 热力图最高
    "GRID": (32, 32, 40),
    "LINE": (200, 200, 206),
    "OK": (86, 200, 124),
    "OVER": (255, 0, 0),
    "PALETTE": ((255, 255, 255), (221, 221, 221), (187, 187, 187), (153, 153, 153),
                (136, 136, 136), (119, 119, 119), (102, 102, 102), (85, 85, 85),
                (68, 68, 68), (51, 51, 51)),
    "CAPTION": 0x000D0808,      # COLORREF(BGR) → #08080D
    "DARK_TITLE": True,
}
LIGHT = {
    "BG": (247, 247, 250),
    "TEXT": (28, 28, 34),
    "DIM": (104, 104, 116),
    "BORDER": (223, 223, 232),
    "ACCENT": (228, 228, 238),
    "PANEL": (255, 255, 255),
    "TRACK": (214, 214, 223),
    "FILL": (86, 86, 104),
    "TRACK_SOFT": (222, 222, 231),
    "HEAT_LO": (235, 235, 242),
    "HEAT_HI": (52, 52, 66),
    "GRID": (214, 214, 223),
    "LINE": (58, 58, 74),
    "OK": (28, 150, 84),
    "OVER": (214, 0, 0),
    "PALETTE": ((24, 24, 30), (52, 52, 60), (84, 84, 94), (112, 112, 122),
                (132, 132, 142), (150, 150, 160), (168, 168, 178), (186, 186, 195),
                (204, 204, 212), (222, 222, 230)),
    "CAPTION": 0x00FAF7F7,      # COLORREF(BGR) → #F7F7FA
    "DARK_TITLE": False,
}

MODE = "dark"
BRAND_CUSTOM = None      # None = 跟随模式（深色底用白、亮色底用黑）

# 当前生效的令牌（apply_mode 会改写）
BG = DARK["BG"]
TEXT = DARK["TEXT"]
DIM = DARK["DIM"]
BORDER = DARK["BORDER"]
ACCENT = DARK["ACCENT"]
PANEL = DARK["PANEL"]
TRACK = DARK["TRACK"]
FILL = DARK["FILL"]
TRACK_SOFT = DARK["TRACK_SOFT"]
HEAT_LO = DARK["HEAT_LO"]
HEAT_HI = DARK["HEAT_HI"]
GRID = DARK["GRID"]
LINE = DARK["LINE"]
GOOD = DARK["OK"]
OVER = DARK["OVER"]
PALETTE = DARK["PALETTE"]
CAPTION = DARK["CAPTION"]
DARK_TITLE = DARK["DARK_TITLE"]

# 品牌色令牌的默认值（apply_mode 会按模式/自定义色重算）
BRAND = (244, 244, 248)
BRAND_SOFT = tuple(int(8 + (244 - 8) * 0.16) for _ in range(3))
BRAND_EDGE = tuple(int(8 + (244 - 8) * 0.42) for _ in range(3))
ON_BRAND = (18, 18, 22)


def _recompute_brand(brand):
    """按当前底色 + 自定义色，重算 BRAND/BRAND_SOFT/BRAND_EDGE/ON_BRAND。"""
    global BRAND, BRAND_SOFT, BRAND_EDGE, ON_BRAND
    BRAND = tuple(brand)
    BRAND_SOFT = lerp(BG, BRAND, 0.16)
    BRAND_EDGE = lerp(BG, BRAND, 0.42)
    lum = 0.299 * BRAND[0] + 0.587 * BRAND[1] + 0.114 * BRAND[2]
    ON_BRAND = (18, 18, 22) if lum > 150 else (250, 250, 252)


def apply_mode(mode, brand=None):
    """切换深色/亮色 + 主题色，改写本模块令牌（各页面按属性访问，自动跟随）。

    brand 为 None 时：深色底用白、亮色底用黑；给了 RGB 就深浅都用它。
    """
    global MODE, BRAND_CUSTOM
    palette = LIGHT if str(mode).lower() == "light" else DARK
    MODE = "light" if palette is LIGHT else "dark"
    for key, value in palette.items():
        globals()[_TOKEN_NAMES.get(key, key)] = value
    BRAND_CUSTOM = tuple(brand) if brand else None
    _recompute_brand(BRAND_CUSTOM or ((24, 24, 30) if MODE == "light" else (244, 244, 248)))


_TOKEN_NAMES = {"OK": "GOOD"}

# 形状层超采样倍率：2.0 最圆润但要 7.3MB 帧缓冲，1.5 在 4 倍放大下几乎看不出差别却只占 4.1MB
SS = float(os.environ.get("V3_SS", 2))
SCALE = 1.0

_F_LIGHT = "C:/Windows/Fonts/msyhl.ttc"
_F_REG = "C:/Windows/Fonts/msyh.ttc"
_F_MONO = "C:/Windows/Fonts/consola.ttf"
_fonts = {}


def set_scale(s):
    global SCALE
    SCALE = float(s or 1.0)


def pixel_size():
    return int(round(W * SCALE)), int(round(H * SCALE))


def font(size, mono=False, light=False):
    """默认用 Microsoft YaHei UI 常规体；只有大号标题/数字才用 Light（细笔画）。"""
    px = max(1, int(round(size * SCALE)))
    key = (px, mono, light)
    if key in _fonts:
        return _fonts[key]
    if mono:
        f = ImageFont.truetype(_F_MONO, px)
    elif light and os.path.exists(_F_LIGHT):
        f = ImageFont.truetype(_F_LIGHT, px)
    else:
        f = ImageFont.truetype(_F_REG, px, index=1)
    _fonts[key] = f
    return f


def ink_center(s, size, mono=False):
    """字符串墨迹的垂直中心（相对绘制基线），用于不同字体之间对齐。"""
    if not s:
        return 0.0
    try:
        box = font(size, mono and s.isascii()).getbbox(s)
    except (OSError, ValueError):
        return 0.0
    return (box[1] + box[3]) / 2.0


def lerp(a, b, t):
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


def ease_out(t):
    """cubicOut，与 ECharts 默认 animationEasing 一致。"""
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


# 分类配色：只在分类胶囊上用一个小圆点，主体保持灰阶
CATEGORY_COLORS = {
    "工作": (86, 140, 255),
    "学习": (80, 190, 150),
    "娱乐": (235, 140, 90),
    "社交": (200, 120, 220),
    "其他": (150, 150, 162),
    "未分类": (92, 92, 102),
}


def category_color(name):
    return CATEGORY_COLORS.get(name or "未分类", CATEGORY_COLORS["其他"])


ANIM_SECONDS = 1.0      # ECharts 默认 animationDuration
FADE_SECONDS = 0.25     # v2 style.css 里 .fade-enter-active 的时长


def anim_start(state, seconds=ANIM_SECONDS):
    state["_t0"] = time.monotonic()
    state["_dur"] = float(seconds)


def anim_progress(state):
    """0..1；没有动画时返回 1.0（=终态）。"""
    t0 = state.get("_t0")
    if not t0:
        return 1.0
    p = (time.monotonic() - t0) / max(1e-3, float(state.get("_dur", ANIM_SECONDS)))
    return 1.0 if p >= 1.0 else p


def anim_running(state):
    t0 = state.get("_t0")
    return bool(t0) and (time.monotonic() - t0) < float(state.get("_dur", ANIM_SECONDS))


def eased_progress(state):
    return ease_out(anim_progress(state))


def fmt_hm(sec):
    """列表用的统一时长："2h 59m" / "39m"（不带秒，列宽整齐）。"""
    sec = int(max(0, sec or 0))
    minutes = sec // 60
    h, m = divmod(minutes, 60)
    if h:
        return "%dh %02dm" % (h, m)
    if minutes:
        return "%dm" % minutes
    return "<1m" if sec else "0m"


def fmt_minutes(sec):
    """按分钟显示（不出现秒）："3h 18m" / "18m" / "不到 1 分钟"。"""
    sec = int(max(0, sec or 0))
    minutes = sec // 60
    if minutes <= 0:
        return "不到 1 分钟" if sec > 0 else "0 分钟"
    h, m = divmod(minutes, 60)
    if h:
        return "%dh %dm" % (h, m) if m else "%dh" % h
    return "%dm" % m


def fmt_duration(sec):
    sec = int(max(0, sec or 0))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return "%dh %dm" % (h, m)
    if m:
        return "%dm %ds" % (m, s)
    return "%ds" % s


def _text_width(d, s, f, spacing=0.0):
    if not s:
        return 0.0
    return sum(d.textlength(c, font=f) for c in s) + spacing * (len(s) - 1)


def draw_text(d, xy, s, f, color, anchor="la", spacing=0.0):
    x, y = xy
    total = _text_width(d, s, f, spacing)
    if anchor[0] == "m":
        x -= total / 2
    elif anchor[0] == "r":
        x -= total
    for c in s:
        d.text((x, y), c, font=f, fill=color)
        x += d.textlength(c, font=f) + spacing


class Frame:
    """一帧画面：形状画在 2x 超采样层，文字画在缩放后的整尺寸层。"""

    def __init__(self):
        pw, ph = pixel_size()
        self.img = Image.new("RGB", (int(pw * SS), int(ph * SS)), BG)
        self.d = ImageDraw.Draw(self.img)
        self._texts = []

    def _s(self, v):
        return int(round(v * SCALE * SS))

    def _ray(self, v):
        return int(round(v * SS))

    def rect(self, x, y, w, h, fill=None, outline=None, width=1, radius=0):
        # 两者都不给时 Pillow 仍会沿边缘画 1px 白线（顶部就是那条"白边"），必须跳过
        if fill is None and outline is None:
            return
        box = [self._s(x), self._s(y), self._s(x + w) - 1, self._s(y + h) - 1]
        if radius:
            self.d.rounded_rectangle(box, radius=self._s(radius), fill=fill,
                                     outline=outline, width=max(1, self._s(width)))
        else:
            self.d.rectangle(box, fill=fill, outline=outline, width=max(1, self._s(width)))

    def hline(self, x1, y, x2, color, width=1):
        self.d.rectangle([self._s(x1), self._s(y), self._s(x2), self._s(y + width) - 1], fill=color)

    def image(self, img, x, y, w=None, h=None):
        """贴一张 RGBA 图片（图标），尺寸按逻辑坐标给。"""
        if img is None:
            return
        img = img.convert("RGBA")
        if w and h:
            img = img.resize((max(1, int(round(w * SCALE * SS))),
                              max(1, int(round(h * SCALE * SS)))), Image.LANCZOS)
        self.img.paste(img, (self._s(x), self._s(y)), img)

    def line(self, x1, y1, x2, y2, color, width=1):
        self.d.line([(self._s(x1), self._s(y1)), (self._s(x2), self._s(y2))],
                    fill=color, width=max(1, self._s(width)))

    def circle(self, cx, cy, r, fill=None, outline=None, width=1):
        self.d.ellipse([self._s(cx - r), self._s(cy - r), self._s(cx + r), self._s(cy + r)],
                       fill=fill, outline=outline, width=max(1, self._s(width)))

    def sector(self, cx, cy, r, start_deg, end_deg, fill):
        """扇形填充（角度 0 在 3 点方向，顺时针，可传负角度）。"""
        self.d.pieslice([self._s(cx - r), self._s(cy - r), self._s(cx + r), self._s(cy + r)],
                        start_deg, end_deg, fill=fill)

    def text(self, x, y, s, size, color, anchor="la", spacing=0.0, mono=False,
             bold=False, light=False):
        self._texts.append((x, y, s, size, color, anchor, spacing, mono, bold, light, False))

    def text_centered(self, cx, cy, s, size, color, spacing=0.0, mono=False,
                      bold=False, light=False):
        """把文字墨迹的中心放到 (cx, cy)——用于按钮/胶囊，避免上下偏一两像素。"""
        self._texts.append((cx, cy, s, size, color, "la", spacing, mono, bold, light, True))

    def finish(self):
        pw, ph = pixel_size()
        img = self.img.resize((pw, ph), Image.LANCZOS)
        d = ImageDraw.Draw(img)
        for x, y, s, size, color, anchor, spacing, mono, bold, light, centered in self._texts:
            # 等宽字体没有中文字形，含非 ASCII 时回退到常规体
            use_mono = mono and s.isascii()
            f = font(size * 1.06, use_mono, light) if bold else font(size, use_mono, light)
            if centered:
                x0, y0, x1, y1 = f.getbbox(s)
                draw_text(d, ((x - (x1 - x0) / 2 - x0) * SCALE, (y - (y1 - y0) / 2 - y0) * SCALE),
                          s, f, color, "la", spacing * SCALE)
            else:
                draw_text(d, (x * SCALE, y * SCALE), s, f, color, anchor, spacing * SCALE)
        return img