"""图标：两处来源，各管一处。

- 托盘 / exe / 开始菜单：程序内按尺寸直绘（深色表盘 + 白环白针，深浅底都看得见）
- 窗口标题栏：复用 v2 的 clock_white.ico（细环细针，最干净）
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ASSET = "clock_white.ico"
FACE = (18, 18, 26, 255)
WHITE = (238, 238, 244, 255)
DIM = (200, 200, 210, 255)
DARK_GLYPH = (28, 28, 34)


def resource_path(name):
    """打包后在 sys._MEIPASS/assets，开发时在 v3/assets。"""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        p = Path(base) / "assets" / name
        if p.exists():
            return p
    return Path(__file__).resolve().parent.parent / "assets" / name


def draw(size):
    """自绘图标（托盘 / exe）：每档尺寸单独画，不缩放。"""
    s = max(8, int(size))
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    pad = s * 0.02
    d.ellipse([pad, pad, s - 1 - pad, s - 1 - pad], fill=FACE)
    ring = max(1, int(round(s * 0.055)))
    d.ellipse([pad + ring, pad + ring, s - 1 - pad - ring, s - 1 - pad - ring],
              outline=WHITE, width=ring)
    cx = cy = s / 2
    d.line([cx, cy, cx, cy - s * 0.24], fill=WHITE, width=max(1, int(round(s * 0.055))))
    d.line([cx, cy, cx + s * 0.18, cy + s * 0.09], fill=DIM,
           width=max(1, int(round(s * 0.042))))
    hub = s * 0.04
    d.ellipse([cx - hub, cy - hub, cx + hub, cy + hub], fill=WHITE)
    return img


def load_asset(size, glyph=None):
    """读 v2 的 ico 资产：取最接近的一层，必要时整体着色。"""
    path = resource_path(ASSET)
    try:
        img = Image.open(path)
        sizes = sorted({s[0] for s in img.info.get("sizes", [(256, 256)])})
    except (OSError, ValueError):
        return None
    best = min(sizes, key=lambda s: (abs(s - size), s))
    img.size = (best, best)
    icon = img.convert("RGBA")
    if best != size:
        icon = icon.resize((size, size), Image.LANCZOS)
    if glyph is not None:
        solid = Image.new("RGBA", icon.size, tuple(glyph) + (255,))
        solid.putalpha(icon.split()[3])
        icon = solid
    return icon


def clock(size, dark=False, ss=6):
    """标题栏用的矢量式表盘：按目标尺寸的 6 倍超采样再缩，环和针始终连续。

    直接缩放 ico 会把 1px 的环缩成"离散的点"，所以这里每档尺寸重画。
    """
    s = max(8, int(size))
    S = s * ss
    color = DARK_GLYPH + (255,) if dark else WHITE
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    pad = S * 0.035
    ring = max(ss, int(round(S * 0.052)))
    d.ellipse([pad, pad, S - 1 - pad, S - 1 - pad], outline=color, width=ring)

    cx = cy = S / 2
    d.line([cx, cy, cx, cy - S * 0.255], fill=color, width=max(ss, int(round(S * 0.060))))
    d.line([cx, cy, cx + S * 0.185, cy + S * 0.100], fill=color,
           width=max(ss, int(round(S * 0.050))))
    hub = S * 0.045
    d.ellipse([cx - hub, cy - hub, cx + hub, cy + hub], fill=color)
    return img.resize((s, s), Image.LANCZOS)


def window_icons():
    """标题栏用小图：和托盘/exe 同一份画法（黑底白墨，两种主题都看得见）。"""
    return [(s, draw(s)) for s in (16, 20, 24, 32, 48)]


def window_icon(size):
    return draw(size)


SIZES = (16, 20, 24, 32, 48, 64, 128, 256)


def save_ico(path):
    """把各档尺寸**分别绘制**后写进 ico（PNG 负载）。

    PIL 的 save(sizes=...) 只会把 256 那张缩下去，小尺寸会糊；这里自己写容器，
    每档都是原生绘制，开始菜单/文件图标在 16px 也是清晰的。
    """
    import io
    import struct

    entries, payloads = [], []
    offset = 6 + 16 * len(SIZES)
    for s in SIZES:
        buf = io.BytesIO()
        draw(s).save(buf, format="PNG")
        data = buf.getvalue()
        dim = 0 if s >= 256 else s
        entries.append(struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
        payloads.append(data)
    with open(path, "wb") as f:
        f.write(struct.pack("<HHH", 0, 1, len(SIZES)))
        for e in entries:
            f.write(e)
        for p in payloads:
            f.write(p)
    return path