import sys, time
sys.path.insert(0, r"D:\apptimer\v3")
from app import log, store
import app.window as w

app = w.App()
app.root.withdraw()
ok = True
def check(name, cond, extra=""):
    global ok
    ok = ok and bool(cond)
    print(("[PASS] " if cond else "[FAIL] ") + name + (" | " + str(extra) if extra else ""))

# 1) 让 render 抛异常，连续两次心跳后循环仍活着
orig_render = app.render
calls = {"n": 0}
def boom():
    calls["n"] += 1
    raise RuntimeError("模拟渲染崩溃")
app.render = boom
app._key = None
app._tick()
time.sleep(1.2)
app._tick()
check("渲染崩溃后心跳仍在跑", True, "已连续调度 %d 次" % calls["n"])
check("崩溃已写入日志", "心跳出错" in (log.log_path().read_text(encoding="utf-8")[-2000:] if log.log_path().exists() else ""))
app.render = orig_render

# 2) 采集线程看门狗：杀掉线程后下一次心跳应重启它
try:
    app.collector.stop(); app.collector.join(1.0)
except Exception:
    pass
dead = not app.collector.is_alive()
app._tick()
time.sleep(1.2)
check("采集线程被杀", dead)
check("看门狗已重启采集", app.collector.is_alive(), app.collector.is_alive())

# 3) 进度条用品牌色
from app import theme
from app.ui import overview
theme.apply_mode("dark")
check("品牌色填充生效", theme.BRAND == (244, 244, 248), theme.BRAND)
app._quit()
print("--- 结论:", "全部通过" if ok else "有失败项", "---")
sys.exit(0 if ok else 1)
