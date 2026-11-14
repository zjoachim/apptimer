"""把 v3 的数据位置指到实验目录：python v3/tools/set_experiment_dir.py [位置]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config, migrate, store

target = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Joachim\Desktop\chaos")
target.mkdir(parents=True, exist_ok=True)
config.set_location(target)
config.ensure_data_dir()
store.reset()
snap = store.load(force=True)
data_dir = store.data_root()
files, total = migrate.stats(data_dir)
print("位置       =", config.get_location())
print("数据目录   =", data_dir, "| 存在:", data_dir.is_dir())
print("数据文件数 =", files, "| 合计 %.1f KB" % (total / 1024))
print("今日行数   =", len(snap["usage"]), "| 今日总时长 =", snap["total"])
print("位置下的无关文件数 =", sum(1 for p in target.iterdir() if p.is_file()))
