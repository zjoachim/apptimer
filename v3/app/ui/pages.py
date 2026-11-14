"""非概览/设置页的统一协议：页面模块各自负责绘制与交互。

每个页面模块必须提供：
    draw(f, snap, state)                  # f 是 theme.Frame，state 是窗口持有的 dict
    on_click(x, y, state, snap) -> bool   # 处理点击，返回 True 表示已消费
    on_wheel(delta, state, snap) -> bool  # delta: +1 向下 / -1 向上
state 由窗口按 tab 各自保存一份，页面可自由读写（用于选中项、滚动、图表类型等）。

模块用静态导入登记（不是字符串 + importlib）：打包器能静态分析到，
少一类"开发能跑、打包缺模块"的坑。
"""
from .. import theme
from . import category, chart, cumulative, history, hours, pomodoro, trend

MODULES = {
    "图表": chart,
    "累计": cumulative,
    "时段": hours,
    "趋势": trend,
    "分类": category,
    "历史": history,
    "番茄钟": pomodoro,
}


def has_page(tab):
    return tab in MODULES


def _module(tab):
    return MODULES[tab]


def enter(tab, state):
    """进入/切回某页时触发一次入场动画。"""
    theme.anim_start(state)


def animating(tab, state):
    return theme.anim_running(state)


def draw(f, tab, snap, state):
    return _module(tab).draw(f, snap, state)


def on_click(tab, x, y, state, snap):
    """返回 True 表示已消费；返回字符串表示"还需要窗口做一件事"（如打开对话框）。"""
    mod = _module(tab)
    handler = getattr(mod, "on_click", None)
    return handler(x, y, state, snap) if handler else False


def on_right_click(tab, x, y, state, snap):
    mod = _module(tab)
    handler = getattr(mod, "on_right_click", None)
    return bool(handler and handler(x, y, state, snap))


def on_wheel(tab, delta, x, y, state, snap):
    mod = _module(tab)
    handler = getattr(mod, "on_wheel", None)
    return bool(handler and handler(delta, x, y, state, snap))
