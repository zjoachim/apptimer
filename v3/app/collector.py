"""事件驱动采集：前台切换钩子 + 1 秒节拍累加 + 空闲/声音/休眠判定。

写入 v3 自己的 SQLite（app/day/hour 三表），只统计前台应用。
"""
import ctypes
import os
import sys
import threading
import time
from ctypes import POINTER, byref, c_int, c_void_p
from ctypes.wintypes import DWORD, HWND, LONG, UINT
from pathlib import Path

from . import audio, db, store

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0000
PM_REMOVE = 0x0001
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

# 超过这个空闲秒数才去判声音（可用环境变量 V3_IDLE_THRESHOLD 覆盖，便于测试）
IDLE_THRESHOLD = float(os.environ.get("V3_IDLE_THRESHOLD", 120.0))
AUDIO_IDLE_CAP = 2 * 3600.0   # 持续有声超过 2 小时视为挂机
GAP_LIMIT = 5.0               # 节拍间隔超过这个值视为休眠/待机，跳过这段时间
TICK = 1.0
FLUSH_SECONDS = 5.0

WINEVENTPROC = ctypes.WINFUNCTYPE(None, c_void_p, DWORD, HWND, LONG, LONG, DWORD, DWORD)
ENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, HWND, c_void_p)


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", UINT), ("dwTime", DWORD)]


def idle_seconds():
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if user32.GetLastInputInfo(byref(info)):
        return max(0.0, (kernel32.GetTickCount64() - info.dwTime) / 1000.0)
    return 0.0


def _process_of_pid(pid):
    if not pid:
        return "", ""
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return "", ""
    try:
        size = DWORD(32768)
        buf = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, byref(size)):
            path = buf.value
            return Path(path).name, path
    finally:
        kernel32.CloseHandle(handle)
    return "", ""


def _pid_of(hwnd):
    pid = DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, byref(pid))
    return pid.value


def _uwp_child(hwnd):
    """ApplicationFrameHost 场景：枚举子窗口拿真实进程。"""
    found = []

    def _cb(child, _lparam):
        pid = _pid_of(child)
        name, path = _process_of_pid(pid)
        if name and name.lower() != "applicationframehost.exe":
            found.append((name, path, pid))
            return False
        return True

    try:
        user32.EnumChildWindows(hwnd, ENUMPROC(_cb), 0)
    except OSError:
        return None
    return found[0] if found else None


def foreground_app():
    """返回 (进程名, exe 路径, pid)。"""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return "", "", 0
    pid = _pid_of(hwnd)
    name, path = _process_of_pid(pid)
    if name.lower() == "applicationframehost.exe":
        for _ in range(2):
            child = _uwp_child(hwnd)
            if child:
                return child
            time.sleep(0.1)
    return name, path, pid


class Collector(threading.Thread):
    def __init__(self, root, flush_seconds=FLUSH_SECONDS):
        super().__init__(name="v3-collector", daemon=True)
        self.db_path = db.db_path(root)
        self.conn = None          # 在采集线程里打开（sqlite3 连接有线程亲和性）
        try:
            from . import config
            self.flush_seconds = float(config.get_save_interval())
            self.idle_threshold = float(config.get_idle_threshold())
        except Exception:
            self.flush_seconds = flush_seconds
            self.idle_threshold = IDLE_THRESHOLD
        self.buffer = {}
        self.current = ("", "")
        self.since = time.monotonic()
        self.audio_since = None
        self.running = True
        self._hook = None
        self._hook_ref = None
        self._last_flush = time.monotonic()
        self.written = 0
        self.errors = 0
        self.last_error = ""
        self.self_pid = os.getpid()
        self.self_exe = os.path.normcase(sys.executable)
        self._exe_cache = {}

    def _exe_of(self, name):
        if name not in self._exe_cache:
            name_now, path = self.current
            if name_now:
                self._exe_cache[name_now] = path
        return self._exe_cache.get(name, "")

    # ---------- 状态机 ----------
    def _credit(self, upto):
        delta = upto - self.since
        self.since = upto
        if delta <= 0 or not self.current[0]:
            return 0.0
        self.buffer[self.current[0]] = self.buffer.get(self.current[0], 0.0) + delta
        return delta

    def _flush(self, force=False):
        if not self.buffer:
            return
        total = sum(self.buffer.values())
        if not force and total < self.flush_seconds:
            return
        if self.conn is None:
            return
        try:
            for name, seconds in self.buffer.items():
                self.written += db.add_duration(self.conn, name, seconds,
                                                exe=self._exe_of(name))
            self.conn.commit()
        except Exception as exc:
            self.errors += 1
            self.last_error = repr(exc)
            return
        self.buffer.clear()
        self._last_flush = time.monotonic()
        store.bump()

    def _evaluate(self, now):
        if now - self.since > GAP_LIMIT:
            # 休眠/待机回来：这段时间不算
            self.current = ("", "")
            self.since = now
            self.audio_since = None
            return

        if idle_seconds() > self.idle_threshold:
            playing = audio.is_playing()
            if playing:
                if self.audio_since is None:
                    self.audio_since = now
                elif now - self.audio_since >= AUDIO_IDLE_CAP:
                    self._credit(now)
                    self.current = ("", "")
                    self.audio_since = None
                    return
            else:
                self._credit(now)
                self.current = ("", "")
                self.audio_since = None
                return
        else:
            self.audio_since = None

        name, path, pid = foreground_app()
        if name.lower() == "applicationframehost.exe":
            # UWP 壳没解析出真实子进程：宁可不记，也不记成壳
            self._credit(now)
            self.current = ("", "")
            return
        if (pid == self.self_pid or name.lower() == "apptimer.exe"
                or (path and os.path.normcase(path) == self.self_exe)):
            self._credit(now)
            self.current = ("", "")
            return
        if not name and not self.current[0]:
            self.since = now
            return
        if (name, path) != self.current:
            self._credit(now)
            self.current = (name, path)
            self._exe_cache[name] = path
            self._flush(force=True)
        self._credit(now)

    # ---------- 钩子 ----------
    def _on_foreground(self, _hook, _event, _hwnd, _idobj, _idchild, _thread, _time):
        self._evaluate(time.monotonic())

    def _pump(self):
        msg = ctypes.create_string_buffer(256)
        while user32.PeekMessageW(msg, 0, 0, 0, PM_REMOVE):
            user32.TranslateMessage(msg)
            user32.DispatchMessageW(msg)

    def run(self):
        self.conn = db.connect(self.db_path)
        user32.SetWinEventHook.restype = c_void_p
        self._hook_ref = WINEVENTPROC(self._on_foreground)
        self._hook = user32.SetWinEventHook(EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_FOREGROUND,
                                            0, self._hook_ref, 0, 0, WINEVENT_OUTOFCONTEXT)
        next_tick = time.monotonic()
        try:
            while self.running:
                self._pump()
                now = time.monotonic()
                if now >= next_tick:
                    self._evaluate(now)
                    self._flush()
                    next_tick = now + TICK
                time.sleep(0.02)
        finally:
            self._credit(time.monotonic())
            self._flush(force=True)
            if self._hook:
                user32.UnhookWinEvent(ctypes.c_void_p(self._hook))
            try:
                if self.conn:
                    self.conn.commit()
                    self.conn.close()
            except Exception:
                pass

    def stop(self):
        self.running = False
