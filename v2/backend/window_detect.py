"""三级降级进程检测 + 桌面路径工具"""

import ctypes
import ctypes.wintypes
import os
from pathlib import Path
import logging

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi
MAX_PATH = 260


def get_desktop_path():
    desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
    return desktop if os.path.exists(desktop) else str(Path.home() / "Desktop")


def get_idle_seconds():
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.wintypes.UINT),
            ("dwTime", ctypes.wintypes.DWORD),
        ]
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if user32.GetLastInputInfo(ctypes.byref(lii)):
        return (kernel32.GetTickCount64() - lii.dwTime) / 1000.0
    return 0.0


def get_active_window_title():
    hwnd = user32.GetForegroundWindow()
    if hwnd == 0:
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def get_exe_version_field(exe_path, field_name):
    """读取 exe 版本信息中的指定字段"""
    try:
        size = ctypes.windll.version.GetFileVersionInfoSizeW(exe_path, None)
        if size == 0:
            return ""
        buf = ctypes.create_string_buffer(size)
        ctypes.windll.version.GetFileVersionInfoW(exe_path, 0, size, buf)
        import struct
        lang_ptr = ctypes.c_void_p()
        lang_len = ctypes.c_uint()
        ctypes.windll.version.VerQueryValueW(buf, r"\VarFileInfo\Translation",
            ctypes.byref(lang_ptr), ctypes.byref(lang_len))
        if lang_len.value < 4:
            return ""
        lang, codepage = struct.unpack("<HH", ctypes.string_at(lang_ptr, 4))
        sub_path = rf"\StringFileInfo\{lang:04x}{codepage:04x}\{field_name}"
        ptr = ctypes.c_void_p()
        length = ctypes.c_uint()
        if ctypes.windll.version.VerQueryValueW(buf, sub_path, ctypes.byref(ptr), ctypes.byref(length)):
            return ctypes.wstring_at(ptr, length.value - 1) if length.value > 1 else ""
    except Exception:
        pass
    return ""


def get_active_window_process_name():
    """三级降级：PROCESS_QUERY|VM_READ → PROCESS_QUERY_LIMITED → CreateToolhelp32Snapshot"""
    hwnd = user32.GetForegroundWindow()
    if hwnd == 0:
        return "", ""
    pid = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    pid_val = pid.value

    # Tier 1：完整权限
    handle = kernel32.OpenProcess(0x0400 | 0x0010, False, pid_val)
    if handle == 0:
        # Tier 2：受限查询
        handle = kernel32.OpenProcess(0x1000, False, pid_val)
        if handle != 0:
            path_buf2 = ctypes.create_unicode_buffer(MAX_PATH)
            path_size2 = ctypes.wintypes.DWORD(MAX_PATH)
            exe_path2 = ""
            try:
                if kernel32.QueryFullProcessImageNameW(handle, 0, path_buf2, ctypes.byref(path_size2)):
                    exe_path2 = path_buf2.value
            except Exception:
                try:
                    if psapi.QueryFullProcessImageNameW(handle, 0, path_buf2, ctypes.byref(path_size2)):
                        exe_path2 = path_buf2.value
                except Exception:
                    pass
            kernel32.CloseHandle(handle)
            if exe_path2:
                return Path(exe_path2).name.lower(), exe_path2

        # Tier 3：快照枚举
        logging.warning(f"OpenProcess 失败 (pid={pid_val}, err={kernel32.GetLastError()}), 降级为快照枚举")
        try:
            TH32CS_SNAPPROCESS = 0x00000002
            class PROCESSENTRY32(ctypes.Structure):
                _fields_ = [
                    ("dwSize", ctypes.wintypes.DWORD),
                    ("cntUsage", ctypes.wintypes.DWORD),
                    ("th32ProcessID", ctypes.wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.POINTER(ctypes.wintypes.ULONG)),
                    ("th32ModuleID", ctypes.wintypes.DWORD),
                    ("cntThreads", ctypes.wintypes.DWORD),
                    ("th32ParentProcessID", ctypes.wintypes.DWORD),
                    ("pcPriClassBase", ctypes.wintypes.LONG),
                    ("dwFlags", ctypes.wintypes.DWORD),
                    ("szExeFile", ctypes.c_wchar * MAX_PATH),
                ]
            snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
            if snap != -1:
                pe = PROCESSENTRY32()
                pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
                if kernel32.Process32FirstW(snap, ctypes.byref(pe)):
                    while True:
                        if pe.th32ProcessID == pid_val:
                            name3 = pe.szExeFile.lower()
                            kernel32.CloseHandle(snap)
                            return name3, ""
                        if not kernel32.Process32NextW(snap, ctypes.byref(pe)):
                            break
                kernel32.CloseHandle(snap)
        except Exception as e:
            logging.warning(f"快照枚举失败: {e}")
        return "", ""

    # Tier 1 成功
    name_buf = ctypes.create_unicode_buffer(MAX_PATH)
    name_size = ctypes.wintypes.DWORD(MAX_PATH)
    name = ""
    if psapi.GetModuleBaseNameW(handle, None, name_buf, name_size):
        name = name_buf.value.lower()
    path_buf = ctypes.create_unicode_buffer(MAX_PATH)
    path_size = ctypes.wintypes.DWORD(MAX_PATH)
    exe_path = ""
    try:
        if kernel32.QueryFullProcessImageNameW(handle, 0, path_buf, ctypes.byref(path_size)):
            exe_path = path_buf.value
    except Exception:
        try:
            if psapi.QueryFullProcessImageNameW(handle, 0, path_buf, ctypes.byref(path_size)):
                exe_path = path_buf.value
        except Exception:
            pass
    kernel32.CloseHandle(handle)
    return name, exe_path
