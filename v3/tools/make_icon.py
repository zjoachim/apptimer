"""生成 exe 图标 assets/timer.ico（自绘），并输出预览。"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from PIL import Image  # noqa: E402

from app import iconart  # noqa: E402

OUT = HERE.parent / "assets"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ico = iconart.save_ico(OUT / "timer.ico")
    print("exe 图标:", ico, ico.stat().st_size, "bytes")

    sizes = (16, 24, 32, 48, 64)
    scale, pad = 3, 10
    w = pad + len(sizes) * (64 * scale + pad)
    sheet = Image.new("RGBA", (w, 64 * scale + pad), (24, 24, 30, 255))
    x = pad
    for sz in sizes:
        ic = iconart.draw(sz)
        big = ic.resize((sz * scale, sz * scale), Image.NEAREST)
        sheet.paste(big, (x, (64 * scale - sz * scale) // 2), big)
        x += 64 * scale + pad
    sheet.save(OUT / "timer_preview.png")
    print("预览:", OUT / "timer_preview.png")


if __name__ == "__main__":
    main()
