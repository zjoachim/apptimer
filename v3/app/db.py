"""v3 的 SQLite 存储：app 维表 + day/hour 两张聚合表，写入即钳制。"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_NAME = "v3.db"
DAY_CAP = 86400
HOUR_CAP = 3600

SCHEMA = """
CREATE TABLE IF NOT EXISTS app (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,
    exe           TEXT NOT NULL DEFAULT '',
    category      TEXT NOT NULL DEFAULT '',
    total_seconds INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS day (
    app_id  INTEGER NOT NULL,
    date    TEXT NOT NULL,
    seconds INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (app_id, date)
);
CREATE TABLE IF NOT EXISTS hour (
    app_id  INTEGER NOT NULL,
    ts      TEXT NOT NULL,
    seconds INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (app_id, ts)
);
CREATE INDEX IF NOT EXISTS idx_day_date ON day(date);
CREATE INDEX IF NOT EXISTS idx_hour_ts ON hour(ts);
"""


def db_path(root):
    return Path(root) / DB_NAME


def connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(SCHEMA)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(app)")}
    if "alias" not in cols:
        conn.execute("ALTER TABLE app ADD COLUMN alias TEXT NOT NULL DEFAULT ''")
    _dedupe_apps(conn)
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_app_name_nocase "
                 "ON app(name COLLATE NOCASE)")
    conn.execute("PRAGMA user_version=3")
    conn.commit()
    return conn


def _total(conn, app_id):
    row = conn.execute("SELECT total_seconds FROM app WHERE id=?", (app_id,)).fetchone()
    return int(row[0]) if row else 0


def _dedupe_apps(conn):
    """把只有大小写不同的同一程序合并成一条（QuickLook.exe / quicklook.exe 这种）。

    之前按进程名原样入库，同一个程序偶尔以不同大小写出现，就变成两行、时长各半。
    """
    groups = {}
    for app_id, name in conn.execute("SELECT id, name FROM app").fetchall():
        groups.setdefault(name.lower(), []).append(app_id)

    merged = 0
    for ids in groups.values():
        if len(ids) < 2:
            continue
        # 主行按总时长选；显示名优先用大小写更"正式"的那个（QuickLook.exe 优于 quicklook.exe）
        names = dict(conn.execute(
            "SELECT id, name FROM app WHERE id IN (%s)" % ",".join("?" * len(ids)), ids).fetchall())
        ids.sort(key=lambda i: (-_total(conn, i), -sum(1 for c in names[i] if c.isupper())))
        keep, rest = ids[0], ids[1:]
        best = max(ids, key=lambda i: sum(1 for c in names[i] if c.isupper()))
        if names[best] != names[keep]:
            conn.execute("UPDATE app SET name=? WHERE id=?", (names[best], keep))
        for old in rest:
            for date, sec in conn.execute(
                    "SELECT date, seconds FROM day WHERE app_id=?", (old,)).fetchall():
                conn.execute(
                    "INSERT INTO day(app_id, date, seconds) VALUES(?,?,?) "
                    "ON CONFLICT(app_id, date) DO UPDATE SET seconds=MIN(?, seconds+excluded.seconds)",
                    (keep, date, sec, DAY_CAP))
            for ts, sec in conn.execute(
                    "SELECT ts, seconds FROM hour WHERE app_id=?", (old,)).fetchall():
                conn.execute(
                    "INSERT INTO hour(app_id, ts, seconds) VALUES(?,?,?) "
                    "ON CONFLICT(app_id, ts) DO UPDATE SET seconds=MIN(?, seconds+excluded.seconds)",
                    (keep, ts, sec, HOUR_CAP))
            conn.execute("UPDATE app SET total_seconds = total_seconds + ? WHERE id=?",
                         (_total(conn, old), keep))
            conn.execute(
                "UPDATE app SET alias = CASE WHEN alias='' THEN "
                "(SELECT alias FROM app WHERE id=?) ELSE alias END, "
                "category = CASE WHEN category='' THEN "
                "(SELECT category FROM app WHERE id=?) ELSE category END WHERE id=?",
                (old, old, keep))
            conn.execute("DELETE FROM day WHERE app_id=?", (old,))
            conn.execute("DELETE FROM hour WHERE app_id=?", (old,))
            conn.execute("DELETE FROM app WHERE id=?", (old,))
            merged += 1
    return merged


def _app_id(conn, name, exe=""):
    row = conn.execute("SELECT id FROM app WHERE name=? COLLATE NOCASE", (name,)).fetchone()
    if row:
        if exe:
            conn.execute("UPDATE app SET exe=? WHERE id=? AND exe=''", (exe, row[0]))
        return row[0]
    cur = conn.execute("INSERT INTO app(name, exe) VALUES(?,?)", (name, exe or ""))
    return cur.lastrowid


def add_duration(conn, name, seconds, when=None, exe=""):
    """把一段时长记到 app/day/hour 三张表，day 与 hour 各自钳制上限。"""
    seconds = int(round(seconds))
    if seconds <= 0 or not name:
        return 0
    when = when or datetime.now()
    date = when.strftime("%Y-%m-%d")
    hour = when.strftime("%Y-%m-%d %H:00")
    app_id = _app_id(conn, name, exe)
    conn.execute("UPDATE app SET total_seconds = total_seconds + ? WHERE id=?", (seconds, app_id))
    conn.execute(
        "INSERT INTO day(app_id, date, seconds) VALUES(?,?,?) "
        "ON CONFLICT(app_id, date) DO UPDATE SET seconds = min(seconds + excluded.seconds, ?)",
        (app_id, date, seconds, DAY_CAP))
    conn.execute(
        "INSERT INTO hour(app_id, ts, seconds) VALUES(?,?,?) "
        "ON CONFLICT(app_id, ts) DO UPDATE SET seconds = min(seconds + excluded.seconds, ?)",
        (app_id, hour, seconds, HOUR_CAP))
    return seconds


def today_usage(conn, date=None):
    date = date or datetime.now().strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT a.name, d.seconds FROM day d JOIN app a ON a.id = d.app_id "
        "WHERE d.date = ? ORDER BY d.seconds DESC", (date,)).fetchall()
    return {name: float(sec) for name, sec in rows}


def cumulative(conn):
    rows = conn.execute("SELECT name, total_seconds FROM app WHERE total_seconds > 0").fetchall()
    return {name: float(sec) for name, sec in rows}


def categories(conn):
    rows = conn.execute("SELECT name, category FROM app WHERE category <> ''").fetchall()
    return {name: cat for name, cat in rows}


def labels(conn):
    """{进程名: 显示名}，没设别名就等于进程名。"""
    rows = conn.execute("SELECT name, alias FROM app").fetchall()
    return {name: (alias or name) for name, alias in rows}


def exes(conn):
    rows = conn.execute("SELECT name, exe FROM app WHERE exe <> ''").fetchall()
    return {name: exe for name, exe in rows}


def set_alias(conn, name, alias):
    """按名字（不分大小写）设置显示别名。"""
    conn.execute("UPDATE app SET alias = ? WHERE name = ?", (alias or "", name))
    conn.commit()


def all_apps(conn):
    """全部应用：[(name, category, total_seconds, 今日秒数)]，按累计降序。"""
    rows = conn.execute(
        "SELECT a.name, a.category, a.total_seconds, "
        "COALESCE((SELECT d.seconds FROM day d WHERE d.app_id = a.id AND d.date = ?), 0) "
        "FROM app a WHERE a.total_seconds > 0 ORDER BY a.total_seconds DESC",
        (datetime.now().strftime("%Y-%m-%d"),)).fetchall()
    return [(name, cat or "", float(total or 0), float(today or 0)) for name, cat, total, today in rows]


def set_category(conn, name, category):
    conn.execute("UPDATE app SET category = ? WHERE name = ?", (category or "", name))
    conn.commit()


def app_daily(conn, name, days=30):
    """某应用最近 N 天逐日秒数，返回 [(date, seconds)] 升序（没有记录的日子不出现）。"""
    rows = conn.execute(
        "SELECT d.date, d.seconds FROM day d JOIN app a ON a.id = d.app_id "
        "WHERE a.name = ? ORDER BY d.date DESC LIMIT ?", (name, days)).fetchall()
    return [(date, float(sec)) for date, sec in reversed(rows)]


def daily_totals(conn, days=30):
    """最近 N 天每天全部应用合计，返回 [(date, seconds)] 升序。"""
    rows = conn.execute(
        "SELECT date, SUM(seconds) FROM day GROUP BY date ORDER BY date DESC LIMIT ?",
        (days,)).fetchall()
    return [(date, float(sec or 0)) for date, sec in reversed(rows)]


def recent_days(conn, limit=30):
    """有记录的最近 N 天，返回 [(date, seconds)] 降序。"""
    rows = conn.execute(
        "SELECT date, SUM(seconds) FROM day GROUP BY date ORDER BY date DESC LIMIT ?",
        (limit,)).fetchall()
    return [(date, float(sec or 0)) for date, sec in rows]


def day_apps(conn, date):
    """某天各应用秒数 {name: seconds}，按秒数降序。"""
    rows = conn.execute(
        "SELECT a.name, d.seconds FROM day d JOIN app a ON a.id = d.app_id "
        "WHERE d.date = ? ORDER BY d.seconds DESC", (date,)).fetchall()
    return {name: float(sec) for name, sec in rows}


def purge_older_than(conn, days, today=None):
    """删掉 N 天之前的 day/hour 记录，返回删除的天数。days<=0 表示不清理。"""
    if not days or days <= 0:
        return 0
    today = today or datetime.now()
    cutoff = (today - timedelta(days=int(days))).strftime("%Y-%m-%d")
    old_days = [row[0] for row in conn.execute(
        "SELECT DISTINCT date FROM day WHERE date < ?", (cutoff,)).fetchall()]
    if old_days:
        conn.execute("DELETE FROM day WHERE date < ?", (cutoff,))
        conn.execute("DELETE FROM hour WHERE substr(ts, 1, 10) < ?", (cutoff,))
        conn.commit()
    return len(old_days)


def recent_hours(conn, days=7):
    """最近 N 天逐小时合计：[{date: {hour(0-23): seconds}}]，按日期升序。"""
    rows = conn.execute(
        "SELECT substr(ts, 1, 10) AS d, substr(ts, 12, 2) AS h, SUM(seconds) "
        "FROM hour GROUP BY d, h ORDER BY d").fetchall()
    out = {}
    for d, h, sec in rows:
        out.setdefault(d, {})[int(h)] = float(sec or 0)
    dates = sorted(out)[-days:]
    return {d: out[d] for d in dates}


def day_hours(conn, date=None):
    """某天每个小时的合计，供后续时段分析用。"""
    date = date or datetime.now().strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT ts, SUM(seconds) FROM hour WHERE ts LIKE ? GROUP BY ts ORDER BY ts",
        (date + "%",)).fetchall()
    return [(ts, float(sec)) for ts, sec in rows]