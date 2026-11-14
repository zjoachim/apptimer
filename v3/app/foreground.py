"""只读：取当前前台进程名（不落盘、不统计）。"""
import ctypes
import ctypes.wintypes as wt
from pathlib import Path

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def active_process_name():
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        pid = wt.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return ""
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not handle:
            return ""
        try:
            size = wt.DWORD(32768)
            buf = ctypes.create_unicode_buffer(size.value)
            if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                name = Path(buf.value).name
                return name if name.lower() != "apptimer.exe" else ""
        finally:
            kernel32.CloseHandle(handle)
    except OSError:
        return ""
    return ""
