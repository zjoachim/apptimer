"""位置切换与数据子目录自测：python v3/tools/selftest_dir.py"""
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from app import config, db, store, theme
from app.ui import overview, settings, shell

ok = True


def check(name, cond, extra=""):
    global ok
    ok = ok and bool(cond)
    print(("[PASS] " if cond else "[FAIL] ") + name + (" | " + str(extra) if extra else ""))


base = Path(tempfile.mkdtemp(prefix="v3loc_"))
today = datetime.now().strftime("%Y-%m-%d")
data_dir = base / config.DATA_SUBDIR
data_dir.mkdir(parents=True)
seed = db.connect(db.db_path(data_dir))
db.add_duration(seed, "demo.exe", 600.0)
seed.execute("UPDATE app SET category='测试' WHERE name='demo.exe'")
seed.commit()
seed.close()
(base / "无关文件.png").write_bytes(b"x" * 10)

prev = config.get_location()
prev_custom = config.is_custom()
config.set_location(None)
store.reset()
try:
    default_root = store.data_root()
    check("默认数据目录在 %LOCALAPPDATA% 下", str(default_root).startswith(os.environ.get("LOCALAPPDATA", "")), default_root)

    config.set_location(base)
    store.reset()
    check("位置生效", config.get_location() == base, config.get_location())
    check("数据目录 = 位置/程序使用记录", store.data_root() == data_dir, store.data_root())
    snap = store.load(force=True)
    check("读到数据", snap["total"] == 600.0, snap["total"])
    check("无关文件不计入", "无关文件.png" not in json.dumps(snap["usage"], ensure_ascii=False))

    config.set_location(None)
    store.reset()
    check("恢复默认后回到 LOCALAPPDATA", store.data_root() == default_root, store.data_root())
finally:
    config.set_location(prev if prev_custom else None)
    store.reset()

print("--- 结论:", "全部通过" if ok else "有失败项", "---")
sys.exit(0 if ok else 1)
