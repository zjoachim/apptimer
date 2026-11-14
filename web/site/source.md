# 源代码

AppTimer 用 Python 3.14 同时写界面和采集，没有前端构建链：窗口是原生的，界面由 Pillow 画好后贴到 tkinter 画布上。

## 目录结构

```
v3/
├── run.py                  打包入口（处理 PyInstaller 的临时目录）
├── app/
│   ├── theme.py            设计令牌 + 帧合成器（超采样、文字直绘、DPI）
│   ├── window.py           Tk 窗口、刷新循环、鼠标与滚轮分发
│   ├── db.py               SQLite：应用 / 天 / 小时三张表
│   ├── collector.py        SetWinEventHook 事件驱动采集
│   ├── foreground.py       前台进程名（含 UWP 穿透）
│   ├── audio.py            默认播放设备是否在出声（Core Audio）
│   ├── config.py           设置读写（v3-settings.json）
│   ├── store.py            只读查询（带 mtime 缓存）
│   ├── export.py           PDF 报告（fpdf2 + 微软雅黑，惰性导入）
│   ├── tray.py             原生 Shell_NotifyIconW 托盘
│   ├── import_v2.py        旧版 JSON 导入
│   ├── migrate.py          数据目录迁移（复制 + 逐文件校验）
│   └── ui/
│       ├── shell.py        顶栏 + tab 导航
│       ├── pages.py        页面注册表
│       └── ...             概览 / 累计 / 图表 / 时段 / 趋势 / 分类 / 历史 / 番茄钟 / 设置
└── tools/                  无窗口预览渲染、自动化验收脚本
```

## 界面怎么画

一帧的流程：`Frame` 先在超采样画布上画形状，缩到目标尺寸后再逐条画文字，最后贴进 `tk.PhotoImage`。静止时如果数据没有变化，这一帧直接跳过。

```python
# app/theme.py 节选
def finish(self):
    pw, ph = pixel_size()
    img = self.img.resize((pw, ph), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    for x, y, s, size, color, anchor, spacing, mono, bold, light, centered in self._texts:
        ...
```

所有圆角、胶囊、扇形都走 `Frame` 的封装，页面里不直接调 `ImageDraw`——这样配色和超采样参数只在一处生效。

## 采集怎么算

前台切换走系统事件，不轮询窗口：

```python
# app/collector.py 节选
EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0000

user32.SetWinEventHook.restype = c_void_p
self._hook_ref = WINEVENTPROC(self._on_foreground)
self._hook = user32.SetWinEventHook(EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_FOREGROUND,
                                    0, self._hook_ref, 0, 0, WINEVENT_OUTOFCONTEXT)
```

回到窗口后按秒累加，应用切换、退出时强制落盘，平时缓冲 5 秒一写。

## 数据

- 数据库：`{数据目录}\v3.db`（SQLite，WAL 模式）
- 表：`app` 应用（名字、别名、分类）、`day` 每天每应用秒数、`hour` 每小时每应用秒数
- 钳制发生在写入路径上：单天 86400 秒、单小时 3600 秒；累计值不钳制

## 打包

```bat
v3\build.bat                      :: 目录版，产物 v3\dist\AppTimer\
py -3.14 -m PyInstaller v3\AppTimer.spec --noconfirm \
    --distpath v3\dist-onefile --workpath v3\build-onefile   :: 单文件版
```

对外发的是单文件版 `v3\dist-onefile\AppTimer.exe`，装进 `AppTimer-v3.zip` 再分发：exe 没有代码签名，网页直接下发会被浏览器拦一道，压缩包不触发。

## 上一代

v2 是「Python HTTP 服务 + Vue 3 前端 + Edge 无边框窗口」的架构，源码留在仓库的 `v2/frontend/` 与 `v2/app/` 目录，本页不再展开。