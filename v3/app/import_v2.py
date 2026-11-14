"""把 v2 的 JSON 数据一次性导入 v3 的 SQLite（只读 v2 目录，可重复执行）。"""
import json
from datetime import datetime, timedelta
from pathlib import Path

from . import db

DATE_FMT = "%Y-%m-%d"


def _read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _day_dirs(root):
    root = Path(root)
    if not root.is_dir():
        return []
    out = []
    for item in sorted(root.iterdir()):
        if not item.is_dir():
            continue
        try:
            datetime.strptime(item.name, DATE_FMT)
        except ValueError:
            continue
        out.append(item)
    return out


def scan(root):
    """先看能导入什么，不写库。"""
    days, apps, sessions = [], set(), 0
    for item in _day_dirs(root):
        data = _read_json(item / "数据.json", {}) or {}
        usage = data.get("usage") or {}
        sess = data.get("sessions") or []
        if not usage and not sess:
            continue
        days.append(item.name)
        apps.update(usage.keys())
        apps.update(s.get("app") for s in sess if s.get("app"))
        sessions += len(sess)
    return {"days": days, "apps": len(apps), "sessions": sessions}


def _split_session(start, end, seconds):
    """把一段会话按小时切分 -> {'YYYY-MM-DD HH:00': 秒}。"""
    if not start or not end:
        return {}
    try:
        t0 = datetime.fromisoformat(start)
        t1 = datetime.fromisoformat(end)
    except (TypeError, ValueError):
        return {}
    if t1 <= t0:
        return {}
    if seconds and seconds > 0 and abs((t1 - t0).total_seconds() - seconds) > 2:
        t1 = t0 + timedelta(seconds=float(seconds))
    out = {}
    cur = t0
    while cur < t1:
        boundary = cur.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        seg_end = min(t1, boundary)
        key = cur.strftime("%Y-%m-%d %H:00")
        out[key] = out.get(key, 0.0) + (seg_end - cur).total_seconds()
        cur = seg_end
    return out


def import_from(root, conn):
    """导入。返回 {'ok','days','apps','sessions','hours','error'}；重复执行结果不变。"""
    root = Path(root)
    if not root.is_dir():
        return {"ok": False, "error": "目录不存在：%s" % root}

    categories = (_read_json(root / "分类标签.json", {}) or {}).get("categories") or {}
    cumulative = (_read_json(root / "累计数据.json", {}) or {}).get("cumulative") or {}

    days = sessions = hours = 0
    seen = set()
    try:
        for item in _day_dirs(root):
            data = _read_json(item / "数据.json", {}) or {}
            usage = data.get("usage") or {}
            sess = data.get("sessions") or []
            if not usage and not sess:
                continue
            day = item.name

            conn.execute("DELETE FROM day WHERE date=?", (day,))
            conn.execute("DELETE FROM hour WHERE ts LIKE ?", (day + "%",))

            for name, sec in usage.items():
                app_id = db._app_id(conn, name)
                seen.add(name)
                conn.execute(
                    "INSERT INTO day(app_id, date, seconds) VALUES(?,?,?) "
                    "ON CONFLICT(app_id, date) DO UPDATE SET seconds=excluded.seconds",
                    (app_id, day, min(db.DAY_CAP, int(round(float(sec or 0))))))
            days += 1

            per_app = {}
            for s in sess:
                sessions += 1
                name = s.get("app")
                if not name:
                    continue
                seen.add(name)
                for key, sec in _split_session(s.get("start"), s.get("end"),
                                               s.get("duration_seconds") or 0).items():
                    slot = per_app.setdefault(name, {})
                    slot[key] = slot.get(key, 0.0) + sec

            for name, kv in per_app.items():
                app_id = db._app_id(conn, name)
                for ts, sec in kv.items():
                    conn.execute(
                        "INSERT INTO hour(app_id, ts, seconds) VALUES(?,?,?) "
                        "ON CONFLICT(app_id, ts) DO UPDATE SET seconds=excluded.seconds",
                        (app_id, ts, min(db.HOUR_CAP, int(round(sec)))))
                    hours += 1

        for name, cat in categories.items():
            if cat:
                conn.execute(
                    "UPDATE app SET category=? WHERE name=? AND (category IS NULL OR category='')",
                    (cat, name))

        for name, total in cumulative.items():
            app_id = db._app_id(conn, name)
            seen.add(name)
            conn.execute("UPDATE app SET total_seconds = MAX(total_seconds, ?) WHERE id=?",
                         (int(round(float(total or 0))), app_id))

        conn.commit()
        return {"ok": True, "days": days, "apps": len(seen), "sessions": sessions,
                "hours": hours, "error": ""}
    except Exception as exc:
        conn.rollback()
        return {"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)}
