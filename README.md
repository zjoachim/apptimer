# AppTimer · 程序使用时间追踪器

一个只跑在 Windows 上的程序使用时间追踪器：自动记录你在每个程序上花了多久，按天、按小时、按应用统计，支持分类、别名、趋势、番茄钟和今日预算。
纯本地运行，不联网、不需要账号，数据就是一个 SQLite 文件。

> **English** — AppTimer is a Windows-only app usage tracker. It records how long you spend in each program,
> aggregates by day / hour / app, and adds categories, aliases, trend charts, a Pomodoro timer and a daily budget.
> Everything runs locally: no network, no account, and all data lives in a single SQLite file.

---

## 三个版本 · Three versions

| 目录 / Folder | 技术栈 / Stack | 说明 / Notes |
|---|---|---|
| `v1/` | Python + Tkinter（单文件） | 最早的原型，单文件 Tkinter app，已归档 |
| `v2/` | Python + pywebview + Vue 3 + Tailwind + ECharts | 网页技术栈重写；`v2/frontend` 是前端源码，`v2/app` 是可打包的完整应用 |
| `v3/` | Python + Tkinter 单画布 + SQLite | **现役版本**，见下 |

仓库只包含这三个版本目录；网站、素材和构建中间产物不在此仓库内。
The repository only tracks the three app versions — the website, media assets and build artefacts are kept elsewhere.

---

## v3 功能 · Features

- **自动计时**：前台窗口 + 空闲检测（默认无输入 120 秒停表），看视频有声时继续计时
- **多维统计**：日 / 小时 / 应用三个维度，SQLite 存储，写入即钳制（天 ≤ 24h、时 ≤ 1h）
- **8 个页面**：概览、累计、图表、时段、趋势、分类、历史、番茄钟
- **分类与别名**：右键应用改显示名，点分类切换类别，颜色小圆点区分
- **今日预算**：设定每日时长预算，超了变红 + 托盘气泡提醒（每天一次）
- **番茄钟**：25/5/15 分钟可自定义，专注/休息结束分别可开关通知
- **深浅色 + 自定义主题色**：默认跟随系统，可选任意 RGB
- **托盘常驻**：点 X 最小化到任务栏继续计时，托盘菜单可显示/退出
- **数据可迁移**：设置里换数据位置（复制 + 逐文件校验），支持从 v2 的 JSON 历史导入
- **报告导出**：导出当日 PDF 报告

> **English** — Automatic timing from the foreground window with idle detection (stops after 120 s of no input,
> keeps counting while video audio is playing); day/hour/app aggregation in SQLite with hard caps;
> eight pages (overview, cumulative, chart, hours, trend, categories, history, Pomodoro);
> aliases and category colours; a daily budget with a one-per-day notification; a configurable Pomodoro timer
> with per-phase notification toggles; dark/light themes with a custom brand colour; a tray icon with
> close-to-minimise; relocatable data directory with v2 JSON import; and PDF export.

---

## 数据位置 · Where the data lives

| 内容 | 位置 |
|---|---|
| 配置（主题、预算、番茄钟、数据位置） | `%LOCALAPPDATA%\AppTimer\v3-settings.json` |
| 使用记录 | `<数据位置>\程序使用记录\v3.db`（默认数据位置是 `%LOCALAPPDATA%\AppTimer`） |
| 图标缓存、日志 | 同一数据目录下的 `v3.log` |

首次启动会自动建库，不需要任何配置；设置页里可以随时更换数据目录（旧的会标记为「旧数据」，可一键清理）。

---

## 已知限制 · Known limitations

- **未签名程序**：首次运行可能弹 SmartScreen「Windows 已保护你的电脑」，点「仍要运行」即可
- **开机自启**写 HKCU Run 键，部分安全软件会拦截（提示"请以管理员身份运行"），以管理员运行一次即可写入
- **托盘图标与系统通知**依赖 `Shell_NotifyIcon`，被安全软件拒绝时程序会自动退化：通知改用自绘的小窗、点 X 仍是最小化
- **DPI**：布局按 100% 缩放调校，高分屏缩放异常请提 issue

> **English** — The executable is unsigned, so SmartScreen may warn on first run (choose "Run anyway").
> Autostart writes to `HKCU\...\Run` and may need one elevated run if a security product blocks it.
> Tray icon and system notifications fall back to a self-drawn toast when the shell refuses the registration.
> Layouts are tuned for 100% display scaling.

---

## 目录结构 · Repository layout

```
v1/           单文件 Tkinter 版本（归档）/ single-file Tkinter version (archived)
v2/           前端源码 / frontend source
v2/app/       可打包的完整应用 / the packaged app + PyInstaller spec
v3/           现役版本 / current version
v3/app/       窗口、渲染、采集、存储 / window, renderer, collector, storage
v3/app/ui/    各页面 / page modules
v3/tools/     自测与预览脚本 / self-tests and preview tools
v3/dist/      打包产物（不入库）/ build output (git-ignored)
```

## 技术栈 · Tech stack

- Python 3.14，Tkinter 单画布 + Pillow 离屏合成（2× 超采样）
- SQLite（WAL），三张表：`app` / `day` / `hour`
- Win32 via ctypes：`SetWinEventHook` 前台窗口、Core Audio 音量、`Shell_NotifyIcon` 托盘、`SHGetFileInfo` 图标
- 打包：PyInstaller。对外发单文件（onefile），装进 zip 分发；目录版（onedir）留作启动更快的备选

## 许可证 · License

未声明开源协议，作者保留所有权利。/ No license specified; all rights reserved.
