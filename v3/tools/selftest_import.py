"""v2 导入自测：合成数据 + 真实 v2 目录 dry-run。"""
import json, os, sys, tempfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(r"D:\apptimer\v3")
sys.path.insert(0, str(ROOT))
from app import db, import_v2

ok = True
def check(name, cond, extra=""):
    global ok
    ok = ok and bool(cond)
    print(("[PASS] " if cond else "[FAIL] ") + name + (" | " + str(extra) if extra else ""))

base = Path(tempfile.mkdtemp(prefix="v2imp_"))
day = "2026-11-10"
(base / day).mkdir(parents=True)
t0 = datetime(2026, 11, 10, 23, 40, 0)
t1 = datetime(2026, 11, 11, 0, 20, 0)
(base / day / "数据.json").write_text(json.dumps({
    "date": day,
    "usage": {"a.exe": 2400.0, "b.exe": 60.0},
    "sessions": [
        {"app": "a.exe", "window": "x", "start": t0.isoformat(), "end": t1.isoformat(),
         "duration_seconds": 2400.0},
    ],
}, ensure_ascii=False), encoding="utf-8")
(base / "累计数据.json").write_text(json.dumps({"cumulative": {"a.exe": 9999.0}}), encoding="utf-8")
(base / "分类标签.json").write_text(json.dumps({"categories": {"a.exe": "工作"}}, ensure_ascii=False), encoding="utf-8")

print("scan ->", import_v2.scan(base))
conn = db.connect(db.db_path(base / "v3data"))
r1 = import_v2.import_from(base, conn)
check("导入成功", r1["ok"], r1)
check("导入 1 天", r1["days"] == 1, r1["days"])
day_rows = db.today_usage(conn, day)
check("日合计写入", abs(day_rows.get("a.exe", 0) - 2400) < 1, day_rows.get("a.exe"))
hours = dict(db.day_hours(conn, day))
check("小时桶按会话切分", len(hours) == 1 and abs(list(hours.values())[0] - 1200) < 1,
      hours)
prev = [r for r in db.all_apps(conn) if r[0] == "a.exe"]
check("累计写入", prev and prev[0][2] >= 9999, prev[:1])
check("分类写入", prev and prev[0][1] == "工作", prev[:1])

r2 = import_v2.import_from(base, conn)
day_rows2 = db.today_usage(conn, day)
check("重复导入不翻倍", abs(day_rows2.get("a.exe", 0) - 2400) < 1, day_rows2.get("a.exe"))

print("\n--- 真实 v2 目录 dry-run（写到临时库，不动用户数据）---")
real = Path(r"C:\Users\Joachim\Desktop\程序使用记录")
if real.is_dir():
    s = import_v2.scan(real)
    print("可导入: %d 天, %d 个应用, %d 条会话" % (len(s["days"]), s["apps"], s["sessions"]))
    tmp2 = db.connect(db.db_path(Path(tempfile.mkdtemp(prefix="v2real_"))))
    rr = import_v2.import_from(real, tmp2)
    print("导入结果:", rr)
    print("库内应用数:", len(db.cumulative(tmp2)), "| 小时桶数:",
          len(db.day_hours(tmp2, s["days"][-1])) if s["days"] else 0)
    tmp2.close()

print("--- 结论:", "全部通过" if ok else "有失败项", "---")
sys.exit(0 if ok else 1)
