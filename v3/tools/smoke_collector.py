"""采集器冒烟测试：跑 N 秒，看是否落库。"""
import sys
import time
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import collector, db

seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 20
root = Path(tempfile.mkdtemp(prefix="v3run_"))
c = collector.Collector(root, flush_seconds=2)
print("foreground at start:", collector.foreground_app())
c.start()
for _ in range(seconds):
    time.sleep(1)
    print("  %2ds current=%r buffer=%.1fs written=%d errors=%d %s" % (
        _ + 1, c.current[0], sum(c.buffer.values()), c.written, c.errors, c.last_error))
c.stop()
c.join(3)

conn = db.connect(db.db_path(root))
usage = db.today_usage(conn)
print("usage:", {k: round(v, 1) for k, v in usage.items()})
print("total:", round(sum(usage.values()), 1), "sec (ran %ds)" % seconds)
print("hours:", db.day_hours(conn))
