"""番茄钟：25 分钟专注 / 5 分钟休息，4 个番茄后长休息 15 分钟。

状态放在 state 里（窗口按 tab 保存），所以切走再切回来不会丢；
计时用绝对结束时间，不依赖渲染频率。
"""
import time

from .. import config, theme

LONG_EVERY = 4


def durations():
    work, brk, long_, _nw, _nb = config.get_pomodoro()
    return work, brk, long_


WORK, BREAK, LONG_BREAK = 25 * 60, 5 * 60, 15 * 60      # 默认值（用于对齐/测试）

CX = theme.W / 2.0
BAR_W, BAR_H, BAR_Y = 260, 4, 256

BTN_Y = 330
BTN_H = 36

SET_W, SET_H, SET_Y = 84, 24, 386
SET_X = theme.W - 20 - SET_W
TOG_W, TOG_H, TOG_Y = 104, 24, 424
TOG_GAP = 26
TOG_X = theme.W / 2 - (TOG_W * 2 + TOG_GAP) / 2
BTN_W_MAIN = 120
BTN_W = 96
GAP = 12


def _st(state):
    state.setdefault("phase", "work")
    state.setdefault("running", False)
    state.setdefault("end", 0.0)
    state.setdefault("remain", WORK)
    state.setdefault("done", 0)
    state.setdefault("last_date", "")
    return state


def _phase_len(phase, done):
    work, brk, long_ = durations()
    if phase == "work":
        return work
    if phase == "long":
        return long_
    return brk


def _phase_name(phase):
    return {"work": "专注", "break": "休息", "long": "长休息"}.get(phase, "专注")


def remaining(state):
    st = _st(state)
    if st["running"]:
        return max(0, int(round(st["end"] - time.time())))
    return max(0, int(st["remain"]))


def _phase_total(state):
    st = _st(state)
    return _phase_len(st["phase"], st["done"])


def start(state):
    st = _st(state)
    if st["running"]:
        return
    if st["remain"] <= 0:
        st["remain"] = _phase_len(st["phase"], st["done"])
    st["end"] = time.time() + st["remain"]
    st["running"] = True


def pause(state):
    st = _st(state)
    if not st["running"]:
        return
    st["remain"] = remaining(state)
    st["running"] = False


def reset(state, phase=None):
    st = _st(state)
    st["phase"] = phase or "work"
    st["running"] = False
    st["remain"] = _phase_len(st["phase"], st["done"])
    st["end"] = 0.0


def skip(state):
    """直接进入下一阶段（不计入完成数）。"""
    st = _st(state)
    nxt = "break" if st["phase"] == "work" else "work"
    reset(state, nxt)


def tick(state):
    """倒计时结束时推进阶段；返回 ('work_done'|'break_done', 提示文字) 或 None。"""
    st = _st(state)
    if not st["running"] or remaining(state) > 0:
        return None
    if st["phase"] == "work":
        st["done"] += 1
        nxt = "long" if st["done"] % LONG_EVERY == 0 else "break"
        hint = "完成第 %d 个番茄，去休息一下" % st["done"]
        event = "work_done"
    else:
        nxt = "work"
        hint = "休息结束，开始下一个番茄"
        event = "break_done"
    st["running"] = False
    st["phase"] = nxt
    st["remain"] = _phase_len(nxt, st["done"])
    return event, hint


def _buttons():
    total = BTN_W_MAIN + GAP + BTN_W + GAP + BTN_W
    x = (theme.W - total) / 2
    out = [("toggle", x, BTN_W_MAIN)]
    x += BTN_W_MAIN + GAP
    out.append(("reset", x, BTN_W))
    x += BTN_W + GAP
    out.append(("skip", x, BTN_W))
    return out


def draw(f, snap, state):
    st = _st(state)
    secs = remaining(state)
    total = _phase_total(state) or 1
    ratio = 1.0 - min(1.0, secs / float(total))
    work = st["phase"] == "work"
    accent = theme.GOOD if work else theme.DIM

    f.text(CX, 112, _phase_name(st["phase"]), 14, accent, anchor="ma")
    f.text(CX, 152, "%02d:%02d" % (secs // 60, secs % 60), 72, theme.TEXT,
           anchor="ma", light=True)

    bx = CX - BAR_W / 2
    f.rect(bx, BAR_Y, BAR_W, BAR_H, fill=theme.TRACK_SOFT, radius=theme.R_TINY)
    if ratio > 0:
        f.rect(bx, BAR_Y, max(2, int(BAR_W * ratio)), BAR_H, fill=accent, radius=theme.R_TINY)

    f.text(CX, 282, "今日完成 %d 个番茄" % st["done"], 12, theme.DIM, anchor="ma")

    for action, x, w in _buttons():
        label = "暂停" if (action == "toggle" and st["running"]) else {
            "toggle": "开始", "reset": "重置", "skip": "跳过"}[action]
        on = action == "toggle"
        f.rect(x, BTN_Y, w, BTN_H, fill=theme.BRAND if on else None,
               outline=None if on else theme.BORDER, radius=theme.R_PILL)
        f.text_centered(x + w / 2, BTN_Y + BTN_H / 2, label, 12,
                        theme.ON_BRAND if on else theme.DIM)

    work, brk, long_ = durations()
    nw, nb = config.get_pomodoro()[3:]
    f.text(CX, 394, "专注 %d 分钟 · 休息 %d 分钟 · 长休息 %d 分钟（每 %d 个）" % (
        work // 60, brk // 60, long_ // 60, LONG_EVERY), 11, theme.DIM, anchor="ma")
    f.rect(SET_X, SET_Y, SET_W, SET_H, outline=theme.BORDER, radius=theme.R_MD)
    f.text_centered(SET_X + SET_W / 2, SET_Y + SET_H / 2, "设定…", 12, theme.DIM)

    f.text(TOG_X - 12, TOG_Y + 6, "到点提醒", 11, theme.DIM, anchor="ra")
    for i, (label, on) in enumerate((("专注结束", nw), ("休息结束", nb))):
        x = TOG_X + i * (TOG_W + TOG_GAP)
        f.rect(x, TOG_Y, TOG_W, TOG_H, fill=theme.BRAND_SOFT if on else None,
               outline=theme.BRAND_EDGE if on else theme.BORDER, radius=theme.R_MD)
        f.text_centered(x + TOG_W / 2, TOG_Y + TOG_H / 2,
                        "%s %s" % (label, "开" if on else "关"), 12,
                        theme.TEXT if on else theme.DIM)


def on_click(x, y, state, snap):
    st = _st(state)
    if SET_X <= x <= SET_X + SET_W and SET_Y <= y <= SET_Y + SET_H:
        return "set_durations"
    if TOG_Y <= y <= TOG_Y + TOG_H:
        if TOG_X <= x <= TOG_X + TOG_W:
            return "toggle_notify_work"
        if TOG_X + TOG_W + TOG_GAP <= x <= TOG_X + TOG_W * 2 + TOG_GAP:
            return "toggle_notify_break"
    if not (BTN_Y <= y <= BTN_Y + BTN_H):
        return False
    for action, bx, w in _buttons():
        if not (bx <= x <= bx + w):
            continue
        if action == "toggle":
            pause(state) if st["running"] else start(state)
        elif action == "reset":
            reset(state, st["phase"])
        elif action == "skip":
            skip(state)
        return True
    return False


def on_wheel(delta, x, y, state, snap):
    return False

def hover(x, y, state, snap):
    """返回鼠标下的控件标识，供窗口画 hover 态。"""
    if SET_X <= x <= SET_X + SET_W and SET_Y <= y <= SET_Y + SET_H:
        return "set_durations"
    if TOG_Y <= y <= TOG_Y + TOG_H:
        if TOG_X <= x <= TOG_X + TOG_W:
            return "toggle_notify_work"
        if TOG_X + TOG_W + TOG_GAP <= x <= TOG_X + TOG_W * 2 + TOG_GAP:
            return "toggle_notify_break"
    if BTN_Y <= y <= BTN_Y + BTN_H:
        for action, bx, w in _buttons():
            if bx <= x <= bx + w:
                return "btn_" + action
    return None
