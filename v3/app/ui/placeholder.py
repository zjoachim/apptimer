"""尚未实现的页面占位。"""
from .. import theme


def draw(f, title):
    f.text(theme.W / 2, 340, title, 22, theme.TEXT, anchor="ma", spacing=1.5)
    f.text(theme.W / 2, 382, "功能建设中", 12, theme.DIM, anchor="ma")
