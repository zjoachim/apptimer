"""从 exe 提取图标并缓存为 PNG（ctypes + GDI，无第三方依赖）。"""
import ctypes
import ctypes.wintypes as wt
import hashlib
from pathlib import Path

from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
shell32 = ctypes.windll.shell32

SHGFI_ICON = 0x0000000100
SHGFI_LARGEICON = 0x0000000000
DI_NORMAL = 0x0003
_cache = {}


class SHFILEINFOW(ctypes.Structure):
    _fields_ = [("hIcon", wt.HICON), ("iIcon", ctypes.c_int), ("dwAttributes", wt.DWORD),
                ("szDisplayName", wt.WCHAR * 260), ("szTypeName", wt.WCHAR * 80)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long), ("biPlanes", wt.WORD), ("biBitCount", wt.WORD),
                ("biCompression", wt.DWORD), ("biSizeImage", wt.DWORD),
                ("biXPelsPerMeter", ctypes.c_long), ("biYPelsPerMeter", ctypes.c_long),
                ("biClrUsed", wt.DWORD), ("biClrImportant", wt.DWORD)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wt.DWORD * 3)]


def _hicon_to_image(hicon, size):
    hdc = user32.GetDC(None)
    memdc = gdi32.CreateCompatibleDC(hdc)
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = size
    bmi.bmiHeader.biHeight = -size
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0
    bits = ctypes.c_void_p()
    gdi32.CreateDIBSection.restype = wt.HBITMAP
    hbmp = gdi32.CreateDIBSection(memdc, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
    if not hbmp:
        gdi32.DeleteDC(memdc)
        user32.ReleaseDC(None, hdc)
        return None
    old = gdi32.SelectObject(memdc, hbmp)
    user32.DrawIconEx(memdc, 0, 0, hicon, size, size, 0, None, DI_NORMAL)
    buf = ctypes.string_at(bits, size * size * 4)
    img = Image.frombuffer("RGBA", (size, size), buf, "raw", "BGRA", 0, 1).copy()
    gdi32.SelectObject(memdc, old)
    gdi32.DeleteObject(hbmp)
    gdi32.DeleteDC(memdc)
    user32.ReleaseDC(None, hdc)
    if img.getextrema()[3][1] == 0:      # 老式图标没有 alpha，按黑色抠图
        px = img.load()
        for y in range(size):
            for x in range(size):
                r, g, b, _a = px[x, y]
                px[x, y] = (r, g, b, 0 if (r, g, b) == (0, 0, 0) else 255)
    return img


shell32.SHGetFileInfoW.argtypes = [wt.LPCWSTR, wt.DWORD, ctypes.POINTER(SHFILEINFOW),
                                    wt.UINT, wt.UINT]
shell32.SHGetFileInfoW.restype = ctypes.c_void_p
user32.DestroyIcon.argtypes = [wt.HICON]
user32.DrawIconEx.argtypes = [wt.HDC, ctypes.c_int, ctypes.c_int, wt.HICON,
                              ctypes.c_int, ctypes.c_int, wt.UINT, wt.HANDLE, wt.UINT]


shell32.ExtractIconExW.argtypes = [wt.LPCWSTR, ctypes.c_int, ctypes.POINTER(wt.HICON),
                                    ctypes.POINTER(wt.HICON), wt.UINT]
shell32.ExtractIconExW.restype = wt.UINT


def _via_shell(path, size):
    info = SHFILEINFOW()
    try:
        got = shell32.SHGetFileInfoW(str(path), 0, ctypes.byref(info),
                                     ctypes.sizeof(info), SHGFI_ICON | SHGFI_LARGEICON)
    except Exception:
        return None
    if not got or not info.hIcon:
        return None
    try:
        return _hicon_to_image(info.hIcon, size)
    finally:
        user32.DestroyIcon(info.hIcon)


def _via_extract(path, size):
    large = wt.HICON()
    small = wt.HICON()
    try:
        count = shell32.ExtractIconExW(str(path), 0, ctypes.byref(large),
                                       ctypes.byref(small), 1)
    except Exception:
        return None
    if not count:
        return None
    try:
        handle = large if large.value else small
        return _hicon_to_image(handle, size) if handle.value else None
    finally:
        for h in (large, small):
            if h.value:
                user32.DestroyIcon(h)


def extract(exe_path, size=32):
    """先试 Shell，失败再试 ExtractIconEx（系统/UWP 保护目录下前者常失败）。"""
    if not exe_path:
        return None
    for attempt in (_via_shell, _via_extract):
        try:
            img = attempt(exe_path, size)
        except Exception:
            img = None
        if img is not None:
            return img
    return None


def icon_cache_path(name, icon_dir):
    key = hashlib.md5(name.lower().encode("utf-8")).hexdigest()[:16]
    return Path(icon_dir) / (key + ".png")


def load(name, exe, icon_dir, size=16):
    """返回 16px 图标（PIL），取不到就返回 None。"""
    if not name:
        return None
    key = (name.lower(), size)
    if key in _cache:
        return _cache[key]
    path = icon_cache_path(name, icon_dir)
    img = None
    if path.exists():
        try:
            img = Image.open(path).convert("RGBA")
        except OSError:
            img = None
    if img is None and exe:
        big = extract(exe, 32)
        if big is not None:
            try:
                Path(icon_dir).mkdir(parents=True, exist_ok=True)
                big.save(path)
            except OSError:
                pass
            img = big
    if img is not None and img.size != (size, size):
        img = img.resize((size, size), Image.LANCZOS)
    _cache[key] = img
    return img
