"""只读查询默认播放设备是否在出声（Core Audio），不可用时返回 None。"""
import ctypes
from ctypes import POINTER, byref, c_float, c_int, c_uint16, c_uint32, c_ubyte, c_void_p
from ctypes.wintypes import DWORD
from uuid import UUID

CLSID_MMDEVICEENUMERATOR = "{BCDE0395-E52F-467C-8E3D-C4579291692E}"
IID_IMMDEVICEENUMERATOR = "{A95664D2-9614-4F35-A746-DE8DB63617E6}"
IID_IAUDIOMETERINFORMATION = "{C02216F6-8C67-4B5B-9D00-D008E73E0064}"
CLSCTX_ALL = 0x17
RENDER, MULTIMEDIA = 0, 1
PEAK_THRESHOLD = 0.0005


class GUID(ctypes.Structure):
    _fields_ = [("Data1", c_uint32), ("Data2", c_uint16), ("Data3", c_uint16),
                ("Data4", c_ubyte * 8)]

    def __init__(self, text):
        u = UUID(text)
        self.Data1, self.Data2, self.Data3 = u.fields[0], u.fields[1], u.fields[2]
        for i, b in enumerate(u.bytes[8:]):
            self.Data4[i] = b


def _method(ptr, index, restype, *argtypes):
    vtable = ctypes.cast(ptr, POINTER(POINTER(c_void_p)))[0]
    return ctypes.WINFUNCTYPE(restype, c_void_p, *argtypes)(vtable[index])


def _release(ptr, index=2):
    try:
        _method(ptr, index, ctypes.c_ulong)(ptr)
    except OSError:
        pass


def peak_value():
    """默认播放设备当前峰值 0.0-1.0；无法判定时返回 None。"""
    try:
        ole32 = ctypes.windll.ole32
        ole32.CoCreateInstance.restype = ctypes.c_long
        ole32.CoInitializeEx(None, 2)

        enumerator = c_void_p()
        hr = ole32.CoCreateInstance(
            byref(GUID(CLSID_MMDEVICEENUMERATOR)), None, CLSCTX_ALL,
            byref(GUID(IID_IMMDEVICEENUMERATOR)), byref(enumerator))
        if hr != 0 or not enumerator:
            return None
        try:
            device = c_void_p()
            hr = _method(enumerator, 4, ctypes.c_long, c_int, c_int, POINTER(c_void_p))(
                enumerator, RENDER, MULTIMEDIA, byref(device))
            if hr != 0 or not device:
                return None
            try:
                meter = c_void_p()
                hr = _method(device, 3, ctypes.c_long, POINTER(GUID), DWORD, c_void_p,
                             POINTER(c_void_p))(
                    device, byref(GUID(IID_IAUDIOMETERINFORMATION)), CLSCTX_ALL, None, byref(meter))
                if hr != 0 or not meter:
                    return None
                try:
                    peak = c_float(0.0)
                    hr = _method(meter, 3, ctypes.c_long, POINTER(c_float))(meter, byref(peak))
                    if hr != 0:
                        return None
                    return float(peak.value)
                finally:
                    _release(meter)
            finally:
                _release(device)
        finally:
            _release(enumerator)
    except (OSError, ValueError, AttributeError, TypeError):
        return None


def is_playing():
    """True 表示在出声；False 表示静音；None 表示无法判定。"""
    peak = peak_value()
    if peak is None:
        return None
    return peak > PEAK_THRESHOLD
