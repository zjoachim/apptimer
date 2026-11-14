"""新用户流程自检：完全空白的环境下走一遍首次启动。

用临时 LOCALAPPDATA + 临时数据位置，避免碰用户真实数据。
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(r"D:\apptimer\v3")
sys.path.insert(0, str(ROOT))

SANDBOX = Path(tempfile.mkdtemp(prefix="v3newuser_"))
os.environ["LOCALAPPDATA"] = str(SANDBOX / "localappdata")
(SANDBOX / "localappdata").mkdir(parents=True, exist_ok=True)

from app import config, db, export, icons, import_v2, store, theme  # noqa: E402
from app.ui import pages, shell  # noqa: E402

ok = True
def check(name, cond, extra=""):
    global ok
    ok = ok and bool(cond)
    print(("[PASS] " if cond else "[FAIL] ") + name + (" | " + str(extra) if extra else ""))

print("沙盒:", SANDBOX)
check("1 默认位置在 LOCALAPPDATA 下", str(config.get_location()).startswith(str(SANDBOX)),
      config.get_location())
check("2 数据目录名是 程序使用记录", config.data_dir().name == config.DATA_SUBDIR,
      config.data_dir())

cfg = config.load()
check("3 首次没有配置文件时给默认值",
      cfg == {} or set(cfg) <= {"theme", "location"},
      cfg)
check("4 主题默认深色", config.get_theme() == "dark", config.get_theme())
check("5 预算默认未设定", config.get_goal() == 0 and not config.goal_enabled())
check("6 番茄钟默认 25/5/15", config.get_pomodoro()[:3] == (1500, 300, 900),
      config.get_pomodoro()[:3])
check("7 提醒默认开", config.get_remind() is True)
check("8 数据保留默认永久", config.get_retention_days() == 0)
check("9 空闲阈值/保存间隔默认值", (config.get_idle_threshold(), config.get_save_interval()) == (120, 5))
check("10 主题色默认跟随模式", config.get_brand() is None)

config.ensure_data_dir()
conn = store.connection()
apps = conn.execute("SELECT COUNT(*) FROM app").fetchone()[0]
check("11 首次启动自动建库（0 应用）", apps == 0, apps)
check("12 数据库在数据目录里", (store.data_root() / "v3.db").exists(), store.data_root() / "v3.db")
check("13 schema 版本 3", conn.execute("PRAGMA user_version").fetchone()[0] == 3)

snap = store.load(force=True)
check("14 空快照结构完整",
      snap.get("total") == 0 and snap.get("usage") == {} and snap.get("labels") == {},
      {k: snap.get(k) for k in ("total", "usage", "labels")})

# 各页面在空数据下的表现
frames = {}
for tab in ("概览", "累计", "图表", "时段", "趋势", "分类", "历史", "设置", "番茄钟"):
    f = theme.Frame()
    shell.draw_shell(f, tab, {"date": snap["date"], "current_app": "空闲", "total_text": "0 秒"})
    try:
        if tab == "概览":
            from app.ui import overview
            overview.draw(f, snap)
        elif tab == "设置":
            from app.ui import settings
            settings.draw(f)
        elif pages.has_page(tab):
            pages.draw(f, tab, snap, {})
        frames[tab] = f.finish()
    except Exception as exc:
        check("页面「%s」空数据不崩" % tab, False, "%s: %s" % (type(exc).__name__, exc))
        continue
check("15 九个页面空数据都能渲染", len(frames) == 9, len(frames))
out = SANDBOX / "empty_pages"
out.mkdir(exist_ok=True)
for tab, img in frames.items():
    img.save(out / ("%s.png" % tab))

# 导出 PDF（空数据）
ok_pdf, info = export.export_pdf()
check("16 空数据导出 PDF 不崩", isinstance(ok_pdf, bool), info)

# 图标提取：exe 不存在时返回 None 而不是抛
check("17 图标缺失时安全返回", icons.load("nope.exe", "", SANDBOX / "icons") is None)

# 旧数据导入：目录不存在
rep = import_v2.import_from(SANDBOX / "nope", store.connection())
check("18 导入不存在的旧目录返回错误信息", rep["ok"] is False and "不存在" in rep["error"], rep["error"])

# 采集器：空目录启动、跑一秒、停
from app import collector
c = collector.Collector(store.data_root())
c.start()
import time
time.sleep(1.2)
alive = c.is_alive()
c.stop()
c.join(2.0)
check("19 采集器能在新目录启动", alive)

print("\n空数据页面截图:", out)
print("--- 结论:", "全部通过" if ok else "有失败项", "---")
sys.exit(0 if ok else 1)
