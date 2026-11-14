"""无窗口渲染预览：py -3.14 v3/tools/preview.py [输出] [tab] [scroll]"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from app import store, theme
from app.ui import overview, pages, placeholder, settings, shell


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "preview.png")
    tab = sys.argv[2] if len(sys.argv) > 2 else "概览"
    arg = sys.argv[3] if len(sys.argv) > 3 else ""
    snap = store.load(force=True)
    f = theme.Frame()
    shell.draw_shell(f, tab, {
        "date": snap["date"],
        "current_app": "msedge.exe",
        "total_text": theme.fmt_duration(snap["total"]),
    })
    if tab == "概览":
        overview.draw(f, snap, scroll=min(int(arg or 0), overview.max_scroll(snap)))
    elif tab == "设置":
        settings.draw(f, arg)
    elif pages.has_page(tab):
        pages.draw(f, tab, snap, {})
    else:
        placeholder.draw(f, tab)
    img = f.finish()
    img.save(out)
    print("%s -> %s (%dx%d)" % (tab, out, img.width, img.height))


if __name__ == "__main__":
    main()
