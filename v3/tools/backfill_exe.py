"""把数据库里缺 exe 路径的应用，用当前运行中的进程补齐（仅供图标使用）。"""
import ctypes
import ctypes.wintypes as wt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db, store

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi


def _running():
    count = 1024
    arr = (wt.DWORD * count)()
    needed = wt.DWORD()
    if not psapi.EnumProcesses(arr, ctypes.sizeof(arr), ctypes.byref(needed)):
        return {}
    out = {}
    for pid in arr[:needed.value // ctypes.sizeof(wt.DWORD)]:
        if not pid:
            continue
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            continue
        try:
            size = wt.DWORD(32768)
            buf = ctypes.create_unicode_buffer(size.value)
            if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                name = Path(buf.value).name
                out.setdefault(name.lower(), buf.value)
        finally:
            kernel32.CloseHandle(handle)
    return out


def main():
    conn = store.connection()
    have = db.exes(conn)
    rows = [r[0] for r in conn.execute("SELECT name FROM app").fetchall()]
    missing = [n for n in rows if not have.get(n)]
    live = _running()
    filled = 0
    for name in missing:
        path = live.get(name.lower())
        if path:
            conn.execute("UPDATE app SET exe=? WHERE name=?", (path, name))
            filled += 1
    conn.commit()
    print("补齐 %d / 缺失 %d 个 exe 路径" % (filled, len(missing)))


if __name__ == "__main__":
    main()
