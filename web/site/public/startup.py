"""注册表开机自启动"""

import os
import sys
import winreg


def add_to_startup():
    script_path = os.path.abspath(sys.argv[0])
    if script_path.endswith(".py"):
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        command = f'"{pythonw}" "{script_path}" --silent'
    else:
        command = f'"{script_path}" --silent'
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "AppUsageTimer", 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)
        return True, ""
    except Exception as e:
        return False, str(e)


def remove_from_startup():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, "AppUsageTimer")
        winreg.CloseKey(key)
        return True, ""
    except FileNotFoundError:
        return False, "未找到自启动项"
    except Exception as e:
        return False, str(e)


def is_startup_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, "AppUsageTimer")
        winreg.CloseKey(key)
        return True
    except Exception:
        return False
