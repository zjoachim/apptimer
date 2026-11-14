"""v3 数据访问：读 SQLite（写入由 collector 负责）。"""
import threading
from datetime import datetime

from . import config, db

_version = 0
_conn = None
_root = None
_lock = threading.Lock()


def data_root():
    return config.data_dir()


def _connection():
    global _conn, _root
    root = data_root()
    with _lock:
        if _conn is None or _root != root:
            if _conn is not None:
                try:
                    _conn.close()
                except Exception:
                    pass
            _conn = db.connect(db.db_path(root))
            _root = root
        return _conn


def connection():
    """页面只读查询用。"""
    return _connection()


def bump():
    """采集器写库后调用，界面据此重绘。"""
    global _version
    _version += 1


def version():
    return _version


def reset():
    global _conn, _root, _version
    with _lock:
        if _conn is not None:
            try:
                _conn.close()
            except Exception:
                pass
        _conn = None
        _root = None
        _version += 1


def load(force=False):
    conn = _connection()
    today = datetime.now().strftime("%Y-%m-%d")
    usage = db.today_usage(conn, today)
    return {
        "date": today,
        "usage": usage,
        "cumulative": db.cumulative(conn),
        "categories": db.categories(conn),
        "labels": db.labels(conn),
        "exes": db.exes(conn),
        "total": sum(usage.values()),
        "stamp": (version(), str(data_root())),
        "root": str(data_root()),
    }
