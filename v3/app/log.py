"""极简日志：写到数据目录的 v3.log，超过 256KB 自动截半。"""
import time
from pathlib import Path

from . import store

MAX_BYTES = 256 * 1024


def log_path():
    try:
        return Path(store.data_root()) / "v3.log"
    except Exception:
        return None


def log(text):
    path = log_path()
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > MAX_BYTES:
            data = path.read_bytes()[-MAX_BYTES // 2:]
            path.write_bytes(data)
        with open(path, "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), text))
    except OSError:
        pass
