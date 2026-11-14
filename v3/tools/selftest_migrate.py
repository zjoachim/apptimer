"""迁移与配置自测：python v3/tools/selftest.py"""
import os
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from app import config, migrate

ok = True


def check(name, cond, extra=""):
    global ok
    ok = ok and bool(cond)
    print(("[PASS] " if cond else "[FAIL] ") + name + (" | " + str(extra) if extra else ""))


base = Path(tempfile.mkdtemp(prefix="v3mig_"))
src = base / "src"
(src / "2026-11-14").mkdir(parents=True)
(src / "数据.json").write_text('{"usage":{"a.exe":10}}', encoding="utf-8")
(src / "累计数据.json").write_text('{"cumulative":{"a.exe":99}}', encoding="utf-8")
(src / "2026-11-14" / "报告.txt").write_text("hello", encoding="utf-8")

print("--- 正常迁移 ---")
dst = base / "dst"
r = migrate.migrate(src, dst)
check("迁移成功", r["ok"], r.get("error"))
check("文件数=3", r.get("files") == 3, r.get("files"))
check("内容一致", migrate.snapshot(src) == migrate.snapshot(dst))
check("源目录保留", src.is_dir() and len(list(src.iterdir())) == 3)

print("--- 拒绝场景 ---")
r2 = migrate.migrate(src, base / "dst")
check("目标非空被拒", not r2["ok"], r2.get("error"))
r3 = migrate.migrate(src, src)
check("同目录被拒", not r3["ok"], r3.get("error"))
r4 = migrate.migrate(src, src / "inner")
check("嵌套被拒", not r4["ok"], r4.get("error"))
r5 = migrate.migrate(base / "nope", base / "dst2")
check("源不存在被拒", not r5["ok"], r5.get("error"))

print("--- 清理旧数据 ---")
mix = base / "mix"
(mix / "2026-11-14").mkdir(parents=True)
(mix / "2026-11-14" / "数据.json").write_text("{}", encoding="utf-8")
(mix / "累计数据.json").write_text("{}", encoding="utf-8")
(mix / "我的照片.png").write_bytes(b"x" * 5)
removed, freed, dir_removed = migrate.purge(mix)
check("只删 AppTimer 条目", removed == 2, removed)
check("无关文件保留", (mix / "我的照片.png").exists())
check("数据条目已删", not (mix / "2026-11-14").exists() and not (mix / "累计数据.json").exists())
check("有其它文件时目录保留", mix.is_dir() and not dir_removed)

pure = base / "pure"
pure.mkdir()
(pure / "累计数据.json").write_text("{}", encoding="utf-8")
(pure / "2026-11-12").mkdir()
(pure / "2026-11-12" / "数据.json").write_text("{}", encoding="utf-8")
removed2, _, dir_removed2 = migrate.purge(pure)
check("纯数据目录删完即移除", removed2 == 2 and dir_removed2 and not pure.exists(),
      "%s/%s" % (removed2, dir_removed2))

print("--- 配置读写 ---")
before = config.get_location()
before_custom = config.is_custom()
try:
    config.set_location(str(base))
    check("写入后读回", config.get_location() == base, config.get_location())
    check("数据目录跟着走", config.data_dir() == base / config.DATA_SUBDIR, config.data_dir())
    config.set_location(None)
    check("清空后回到默认", config.is_custom() is False, config.get_location())
finally:
    config.set_location(before if before_custom else None)
    check("已恢复原配置", config.is_custom() == before_custom, config.get_location())

print("--- 结论:", "全部通过" if ok else "有失败项", "---")
sys.exit(0 if ok else 1)
