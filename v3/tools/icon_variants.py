"""图标候选：按尺寸逐个绘制（不缩放），输出对比图。"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(r"D:\apptimer\v3\assets")
DARK = (16, 16, 22, 255)
WHITE = (247, 247, 250, 255)
DIMWHITE = (208, 208, 218, 255)


def _disc(d, s, inset, color=DARK):
    d.ellipse([inset, inset, s - 1 - inset, s - 1 - inset], fill=color)


def v1_ring_hands(s):
    """圆盘 + 细环 + 双针（时针粗、分针细），无顶部按钮。"""
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = 1 if s >= 24 else 0
    _disc(d, s, pad)
    ring = max(1, round(s * 0.07))
    d.ellipse([pad, pad, s - 1 - pad, s - 1 - pad], outline=WHITE, width=ring)
    cx = cy = (s - 1) / 2
    r = (s - 1) / 2 - pad - ring
    w_hour = max(1, round(s * 0.13))
    w_min = max(1, round(s * 0.09))
    d.line([cx, cy, cx, cy - r * 0.55], fill=WHITE, width=w_hour)
    d.line([cx, cy, cx + r * 0.62, cy + r * 0.18], fill=DIMWHITE, width=w_min)
    dot = max(1, round(s * 0.08))
    d.ellipse([cx - dot, cy - dot, cx + dot, cy + dot], fill=WHITE)
    return img


def v2_ticks(s):
    """圆盘 + 细环 + 4 个刻线 + 一根粗针。"""
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = 1 if s >= 24 else 0
    _disc(d, s, pad)
    ring = max(1, round(s * 0.06))
    d.ellipse([pad, pad, s - 1 - pad, s - 1 - pad], outline=WHITE, width=ring)
    cx = cy = (s - 1) / 2
    r = (s - 1) / 2 - pad - ring
    if s >= 32:
        tick = max(1, round(s * 0.05))
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            d.line([cx + dx * r * 0.72, cy + dy * r * 0.72,
                    cx + dx * r * 0.95, cy + dy * r * 0.95], fill=DIMWHITE, width=tick)
    w = max(1, round(s * 0.13))
    d.line([cx, cy, cx + r * 0.58, cy - r * 0.48], fill=WHITE, width=w)
    dot = max(1, round(s * 0.09))
    d.ellipse([cx - dot, cy - dot, cx + dot, cy + dot], fill=WHITE)
    return img


def v3_badge(s):
    """圆角方徽章 + 环形指针。"""
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rad = max(2, round(s * 0.23))
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=rad, fill=DARK)
    ring = max(1, round(s * 0.075))
    m = max(2, round(s * 0.16))
    d.ellipse([m, m, s - 1 - m, s - 1 - m], outline=WHITE, width=ring)
    cx = cy = (s - 1) / 2
    r = (s - 1) / 2 - m - ring
    w = max(1, round(s * 0.12))
    d.line([cx, cy, cx, cy - r * 0.55], fill=WHITE, width=w)
    d.line([cx, cy, cx + r * 0.6, cy + r * 0.2], fill=WHITE, width=max(1, w - 1))
    dot = max(1, round(s * 0.08))
    d.ellipse([cx - dot, cy - dot, cx + dot, cy + dot], fill=WHITE)
    return img


def v4_hourglass(s):
    """圆盘 + 沙漏剪影：16px 也一眼能认。"""
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = 1 if s >= 24 else 0
    _disc(d, s, pad)
    m = max(2, round(s * 0.26))
    top, bot = m, s - 1 - m
    w = max(1, round(s * 0.10))
    d.line([m, top, s - 1 - m, top], fill=WHITE, width=w)
    d.line([m, bot, s - 1 - m, bot], fill=WHITE, width=w)
    d.polygon([(m + w, top + 1), (s - 1 - m - w, top + 1),
               ((s - 1) / 2, (top + bot) / 2)], fill=WHITE)
    d.polygon([(m + w, bot - 1), (s - 1 - m - w, bot - 1),
               ((s - 1) / 2, (top + bot) / 2)], fill=WHITE)
    return img


VARIANTS = (("v1 细环双针", v1_ring_hands), ("v2 刻线单针", v2_ticks),
            ("v3 圆角徽章", v3_badge), ("v4 沙漏", v4_hourglass))
SIZES = (16, 24, 32, 48, 64)


def main():
    scale = 3
    cell = max(SIZES) * scale
    pad = 12
    width = pad + len(SIZES) * (cell + pad)
    row_h = cell + pad * 2
    sheet = Image.new("RGBA", (width, row_h * len(VARIANTS) * 2), (250, 250, 252, 255))
    dark_bg = Image.new("RGBA", (width, row_h), (22, 22, 28, 255))

    y = 0
    for name, fn in VARIANTS:
        for backdrop, strip in (("light", None), ("dark", dark_bg)):
            band = Image.new("RGBA", (width, row_h), (250, 250, 252, 255) if strip is None else (22, 22, 28, 255))
            x = pad
            for sz in SIZES:
                icon = fn(sz)
                big = icon.resize((sz * scale, sz * scale), Image.NEAREST)
                band.paste(big, (x, (row_h - sz * scale) // 2), big)
                x += cell + pad
            sheet.paste(band, (0, y))
            y += row_h
    sheet.save(OUT / "icon_variants.png")
    print("saved", OUT / "icon_variants.png", sheet.size)


if __name__ == "__main__":
    main()
