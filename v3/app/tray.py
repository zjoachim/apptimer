"""原生托盘图标（ctypes + Shell_NotifyIconW），不依赖第三方库。"""
import ctypes
import ctypes.wintypes as wt
import threading
from pathlib import Path

from PIL import Image

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

WM_APP = 0x8000
WM_TRAY = WM_APP + 1
WM_COMMAND = 0x0111
WM_DESTROY = 0x0002
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
WM_QUIT = 0x0012
NIM_ADD, NIM_DELETE = 0, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP = 1, 2, 4
NIF_INFO = 0x10
NIIF_INFO = 0x1
TPM_RIGHTBUTTON, TPM_RETURNCMD = 0x0002, 0x0100
MF_STRING = 0x0000
ID_SHOW, ID_QUIT = 1001, 1002
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
HWND_MESSAGE = ctypes.c_void_p(-3)

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)

# 明确声明原型：64 位下不声明会把句柄截成 int，出现 OverflowError 或静默失败
kernel32.GetModuleHandleW.restype = wt.HMODULE
user32.RegisterClassW.argtypes = [ctypes.c_void_p]
user32.RegisterClassW.restype = wt.ATOM
user32.CreateWindowExW.argtypes = [wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                   wt.HWND, wt.HMENU, wt.HINSTANCE, wt.LPVOID]
user32.CreateWindowExW.restype = wt.HWND
user32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_ssize_t
user32.DestroyWindow.argtypes = [wt.HWND]
user32.ShowWindow.argtypes = [wt.HWND, ctypes.c_int]
shell32.Shell_NotifyIconW.argtypes = [wt.DWORD, ctypes.c_void_p]
shell32.Shell_NotifyIconW.restype = wt.BOOL
user32.CreateIconIndirect.argtypes = [ctypes.c_void_p]
user32.CreateIconIndirect.restype = wt.HICON
user32.GetDC.argtypes = [wt.HWND]
user32.GetDC.restype = wt.HDC
user32.ReleaseDC.argtypes = [wt.HWND, wt.HDC]
gdi32.CreateDIBSection.argtypes = [wt.HDC, ctypes.c_void_p, wt.UINT,
                                   ctypes.POINTER(ctypes.c_void_p), wt.HANDLE, wt.DWORD]
gdi32.CreateDIBSection.restype = wt.HBITMAP
gdi32.CreateBitmap.argtypes = [ctypes.c_int, ctypes.c_int, wt.UINT, wt.UINT, ctypes.c_void_p]
gdi32.CreateBitmap.restype = wt.HBITMAP
gdi32.DeleteObject.argtypes = [wt.HGDIOBJ]
gdi32.DeleteObject.restype = wt.BOOL


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", wt.UINT), ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                ("hInstance", wt.HINSTANCE), ("hIcon", wt.HICON),
                ("hCursor", wt.HANDLE), ("hbrBackground", wt.HBRUSH),
                ("lpszMenuName", wt.LPCWSTR), ("lpszClassName", wt.LPCWSTR)]


class GUID(ctypes.Structure):
    _fields_ = [("Data1", wt.DWORD), ("Data2", wt.WORD), ("Data3", wt.WORD),
                ("Data4", ctypes.c_ubyte * 8)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("hWnd", wt.HWND), ("uID", wt.UINT),
                ("uFlags", wt.UINT), ("uCallbackMessage", wt.UINT), ("hIcon", wt.HICON),
                ("szTip", wt.WCHAR * 128), ("dwState", wt.DWORD), ("dwStateMask", wt.DWORD),
                ("szInfo", wt.WCHAR * 256), ("uVersion", wt.UINT),
                ("szInfoTitle", wt.WCHAR * 64), ("dwInfoFlags", wt.DWORD),
                ("guidItem", GUID), ("hBalloonIcon", wt.HICON)]


def icon_image(size=64):
    """托盘图标：程序内自绘（见 app/iconart.py 的 draw）。"""
    from .iconart import draw
    return draw(size)


class ICONINFO(ctypes.Structure):
    _fields_ = [("fIcon", wt.BOOL), ("xHotspot", wt.DWORD), ("yHotspot", wt.DWORD),
                ("hbmMask", wt.HBITMAP), ("hbmColor", wt.HBITMAP)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long),
                ("biPlanes", wt.WORD), ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wt.DWORD),
                ("biClrImportant", wt.DWORD)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wt.DWORD * 3)]


def hicon_from_image(img):
    """内存里建 HICON：打包版对 %LOCALAPPDATA% 无写权限时，不再依赖写 .ico 文件。"""
    gdi32 = ctypes.windll.gdi32
    img = img.convert("RGBA")
    size = img.size[0]
    hdc = user32.GetDC(None)
    try:
        bmi = BITMAPINFO()
        header = bmi.bmiHeader
        header.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        header.biWidth = size
        header.biHeight = -size          # 自上而下
        header.biPlanes = 1
        header.biBitCount = 32
        header.biCompression = 0         # BI_RGB
        bits = ctypes.c_void_p()
        color = gdi32.CreateDIBSection(hdc, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
        if not color:
            return None
        data = img.tobytes()
        ctypes.memmove(bits, data, len(data))
        mask_bytes = ctypes.create_string_buffer(((size + 31) // 32) * 4 * size)
        mask = gdi32.CreateBitmap(size, size, 1, 1, mask_bytes)
        info = ICONINFO(1, 0, 0, mask, color)
        handle = user32.CreateIconIndirect(ctypes.byref(info))
        gdi32.DeleteObject(mask)
        gdi32.DeleteObject(color)
        return handle or None
    finally:
        user32.ReleaseDC(None, hdc)


class Tray:
    """callback 已经在 Tk 主线程里被 after() 包一层，这里只负责触发。"""

    def __init__(self, on_show, on_quit, title="程序使用时间追踪器", icon_dir=None):
        self.on_show = on_show
        self.on_quit = on_quit
        self.title = title
        self.icon_dir = Path(icon_dir) if icon_dir else Path.home() / "AppData" / "Local" / "AppTimer"
        self._hwnd = None
        self._wndproc = None
        self._hicon = None
        self._thread = None
        self._ready = threading.Event()
        self.ok = False

    def start(self):
        self._thread = threading.Thread(target=self._run, name="v3-tray", daemon=True)
        self._thread.start()
        self._ready.wait(3.0)
        return self.ok

    def _run(self):
        try:
            hinst = kernel32.GetModuleHandleW(None)
            self._wndproc = WNDPROC(self._wnd_proc)
            wc = WNDCLASSW()
            wc.style = 0
            wc.lpfnWndProc = self._wndproc
            wc.cbClsExtra = wc.cbWndExtra = 0
            wc.hInstance = hinst
            wc.hIcon = wc.hCursor = wc.hbrBackground = None
            wc.lpszMenuName = None
            wc.lpszClassName = "AppTimerV3TrayWindow"
            user32.RegisterClassW(ctypes.byref(wc))
            hwnd = user32.CreateWindowExW(0, "AppTimerV3TrayWindow", self.title, 0,
                                          0, 0, 0, 0, HWND_MESSAGE, None, hinst, None)
            if not hwnd:
                self._ready.set()
                return
            self._hwnd = hwnd
            self._hicon = self._load_icon()
            nid = NOTIFYICONDATAW()
            nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
            nid.hWnd = hwnd
            nid.uID = 1
            nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
            nid.uCallbackMessage = WM_TRAY
            nid.hIcon = self._hicon
            nid.szTip = self.title[:127]
            if not shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid)):
                self._ready.set()
                return
            self.ok = True
            self._ready.set()
            msg = wt.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        except OSError:
            self._ready.set()

    def _load_icon(self):
        """优先内存建图（不依赖可写目录），失败再退回写文件/系统图标。"""
        try:
            handle = hicon_from_image(icon_image(32))
            if handle:
                return handle
        except OSError:
            pass
        try:
            self.icon_dir.mkdir(parents=True, exist_ok=True)
            path = self.icon_dir / "tray.ico"
            icon_image(32).save(path, format="ICO",
                                sizes=[(16, 16), (20, 20), (24, 24), (32, 32), (48, 48), (64, 64)])
            handle = user32.LoadImageW(None, str(path), IMAGE_ICON, 0, 0, LR_LOADFROMFILE)
            if handle:
                return handle
        except OSError:
            pass
        return user32.LoadIconW(None, 32516)

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAY:
            event = lparam & 0xFFFF
            if event == WM_LBUTTONUP:
                self.on_show()
            elif event == WM_RBUTTONUP:
                self._popup(hwnd)
            return 0
        if msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _popup(self, hwnd):
        menu = user32.CreatePopupMenu()
        user32.AppendMenuW(menu, MF_STRING, ID_SHOW, "显示窗口")
        user32.AppendMenuW(menu, MF_STRING, ID_QUIT, "退出")
        pt = wt.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.SetForegroundWindow(hwnd)
        cmd = user32.TrackPopupMenu(menu, TPM_RIGHTBUTTON | TPM_RETURNCMD,
                                    pt.x, pt.y, 0, hwnd, None)
        user32.DestroyMenu(menu)
        user32.PostMessageW(hwnd, 0, 0, 0)
        if cmd == ID_SHOW:
            self.on_show()
        elif cmd == ID_QUIT:
            self.on_quit()

    def notify(self, title, text):
        """托盘气泡通知（失败静默）。"""
        if not self.ok or not self._hwnd:
            return False
        try:
            nid = NOTIFYICONDATAW()
            nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
            nid.hWnd = self._hwnd
            nid.uID = 1
            nid.uFlags = NIF_INFO
            nid.szInfoTitle = str(title)[:63]
            nid.szInfo = str(text)[:255]
            nid.dwInfoFlags = NIIF_INFO
            return bool(shell32.Shell_NotifyIconW(1, ctypes.byref(nid)))   # NIM_MODIFY
        except OSError:
            return False

    def stop(self):
        try:
            if self._hwnd:
                nid = NOTIFYICONDATAW()
                nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
                nid.hWnd = self._hwnd
                nid.uID = 1
                shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
                user32.PostMessageW(self._hwnd, WM_QUIT, 0, 0)
                self._hwnd = None
        except OSError:
            pass
        self.ok = False

def diagnose():
    """逐步复现托盘注册，返回每一步的结果（用于排查打包环境的失败点）。"""
    out = []
    try:
        hinst = kernel32.GetModuleHandleW(None)
        out.append("hinst=%s" % bool(hinst))
        proc = WNDPROC(lambda h, m, w, l: user32.DefWindowProcW(h, m, w, l))
        wc = WNDCLASSW()
        wc.style = 0
        wc.lpfnWndProc = proc
        wc.hInstance = hinst
        wc.lpszClassName = "AppTimerV3DiagWindow"
        reg = user32.RegisterClassW(ctypes.byref(wc))
        out.append("RegisterClass=%s err=%s" % (reg, kernel32.GetLastError()))
        hwnd = user32.CreateWindowExW(0, "AppTimerV3DiagWindow", "diag", 0, 0, 0, 0, 0,
                                      HWND_MESSAGE, None, hinst, None)
        out.append("CreateWindow=%s err=%s" % (bool(hwnd), kernel32.GetLastError()))
        if not hwnd:
            return out
        icon = hicon_from_image(icon_image(32))
        out.append("hicon=%s" % bool(icon))
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = hwnd
        nid.uID = 1
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAY
        nid.hIcon = icon
        nid.szTip = "AppTimer 诊断"
        ok = shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
        out.append("NIM_ADD=%s err=%s" % (ok, kernel32.GetLastError()))
        if ok:
            nid.uFlags = NIF_INFO
            nid.szInfoTitle = "AppTimer 诊断"
            nid.szInfo = "诊断气泡：看到这条说明通知链路是通的"
            nid.dwInfoFlags = NIIF_INFO
            ok2 = shell32.Shell_NotifyIconW(1, ctypes.byref(nid))
            out.append("NIM_MODIFY(NIF_INFO)=%s err=%s" % (ok2, kernel32.GetLastError()))
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
        user32.DestroyWindow(hwnd)
        # 再用普通隐藏窗口试一次（HWND_MESSAGE 在部分环境下被拒）
        hwnd2 = user32.CreateWindowExW(0, "AppTimerV3DiagWindow", "diag2", 0, 0, 0, 0, 0,
                                       None, None, hinst, None)
        out.append("普通窗口=%s err=%s" % (bool(hwnd2), kernel32.GetLastError()))
        if hwnd2:
            user32.ShowWindow(hwnd2, 0)
            nid2 = NOTIFYICONDATAW()
            nid2.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
            nid2.hWnd = hwnd2
            nid2.uID = 1
            nid2.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
            nid2.uCallbackMessage = WM_TRAY
            nid2.hIcon = icon
            nid2.szTip = "AppTimer 诊断2"
            ok3 = shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid2))
            out.append("NIM_ADD(普通窗口)=%s err=%s" % (ok3, kernel32.GetLastError()))
            if ok3:
                nid2.uFlags = NIF_INFO
                nid2.szInfoTitle = "AppTimer 诊断2"
                nid2.szInfo = "普通窗口的气泡"
                nid2.dwInfoFlags = NIIF_INFO
                out.append("NIM_MODIFY=%s" % shell32.Shell_NotifyIconW(1, ctypes.byref(nid2)))
                shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid2))
            user32.DestroyWindow(hwnd2)
    except Exception as exc:
        out.append("异常: %s: %s" % (type(exc).__name__, exc))
    return out