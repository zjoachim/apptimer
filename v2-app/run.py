"""AppTimer 启动入口 — 避免 PyInstaller 相对导入问题"""
import sys
import os

# PyInstaller one-file 模式下 MEIPASS 是解压目录
if getattr(sys, 'frozen', False):
    base = sys._MEIPASS
    if base not in sys.path:
        sys.path.insert(0, base)
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.main import main

if __name__ == "__main__":
    main()
