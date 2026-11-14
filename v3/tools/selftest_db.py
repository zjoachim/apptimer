"""SQLite 层自测：写入累加、天/时钳制、查询。"""
import os
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from app import db

ok = True


def check(name, cond, extra=""):
    global ok
    ok = ok and bool(cond)
    print(("[PASS] " if cond else "[FAIL] ") + name + (" | " + str(extra) if extra else ""))


root = Path(tempfile.mkdtemp(prefix="v3db_"))
conn = db.connect(db.db_path(root))
check("建库成功", db.db_path(root).exists())

db.add_duration(conn, "a.exe", 10)
db.add_duration(conn, "a.exe", 10.4)
day = db.today_usage(conn)
check("同日累加", abs(day["a.exe"] - 20) <= 1, day.get("a.exe"))
check("累计累加", abs(db.cumulative(conn)["a.exe"] - 20) <= 1, db.cumulative(conn).get("a.exe"))
check("小时桶有 1 条", len(db.day_hours(conn)) == 1, db.day_hours(conn))

db.add_duration(conn, "a.exe", 100000)
row = conn.execute("SELECT seconds FROM day WHERE app_id=1").fetchone()[0]
check("单日钳到 86400", row == db.DAY_CAP, row)
hours = db.day_hours(conn)
check("单小时钳到 3600", hours[0][1] == db.HOUR_CAP, hours[0][1])
check("累计不受钳制", db.cumulative(conn)["a.exe"] > db.DAY_CAP, db.cumulative(conn)["a.exe"])

db.add_duration(conn, "b.exe", 5, )
check("第二个应用独立", len(db.today_usage(conn)) == 2, db.today_usage(conn).keys())
check("分类默认空", db.categories(conn) == {}, db.categories(conn))
check("0 秒不写", db.add_duration(conn, "c.exe", 0) == 0)

print("--- 结论:", "全部通过" if ok else "有失败项", "---")
sys.exit(0 if ok else 1)
