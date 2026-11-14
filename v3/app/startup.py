r"""开机自启：写 HKCUSoftwareMicrosoftWindowsCurrentVersionRun。"""
import sys
import winreg
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "AppTimerV3"


def _command():
    exe = Path(sys.executable)
    if exe.name.lower().startswith("python"):
        entry = Path(__file__).resolve().parents[1] / "run.py"
        return '"%s" "%s" --silent' % (exe, entry)
    return '"%s" --silent' % exe


def is_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
            return bool(value)
    except OSError:
        return False


def enable():
    """只申请 KEY_SET_VALUE（v2 的做法）。

    CreateKey 会请求 KEY_ALL_ACCESS，在部分机器上被安全软件拒绝（WinError 5），
    而 Run 键本来就存在，OpenKey + SetValueEx 就够了。
    """
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
    except FileNotFoundError:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY)
    with key:
        winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _command())


def disable():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, VALUE_NAME)
    except OSError:
        pass


def set_enabled(on):
    """返回 (成功, 错误信息)。注册表写入可能被系统安全策略拒绝（WinError 5）。"""
    try:
        if on:
            enable()
        else:
            disable()
    except OSError as exc:
        return False, "%s" % (exc,)
    return True, ""


def toggle():
    """返回 (当前是否开启, 错误信息)。"""
    want = not is_enabled()
    ok, err = set_enabled(want)
    if not ok:
        return is_enabled(), err
    return is_enabled(), ""