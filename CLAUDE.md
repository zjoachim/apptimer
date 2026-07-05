# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AppTimer 是一个 Windows 程序使用时间追踪器，有两个版本：
- **v1**：单文件 Tkinter 应用（`apptimer/app_timer.py`），Python 3.14
- **v2**：pywebview + Vue3 + Tailwind + ECharts，Python 3.14（pythonnet 3.1.0+ 已支持）

## 目录结构

| 目录 | 用途 |
|------|------|
| `apptimer/` | v1 源码（单文件 `app_timer.py` + `clock.ico`） |
| `v2/frontend/` | v2 前端源码（Vue3 + Vite + Tailwind） |
| `v2-app/` | v2 完整应用（后端 + 前端 dist + 打包配置） |
| `v2-app/backend/` | v2 Python 后端（main.py, tracker.py, window_detect.py, startup.py） |
| `v2-app/frontend/` | v2 前端副本（**打包用**，需从 `v2/frontend/` 同步） |
| `website-v2/` | 项目官网（VitePress），通过 GitHub Pages 部署 |

**关键**：`v2/frontend/src/` 是前端源码，`v2-app/frontend/` 是打包用副本。修改前端后必须同步到 `v2-app/frontend/` 再重新构建。

## 构建命令

### v2 前端开发
```bash
cd v2/frontend
npm install          # 首次安装
npm run build        # 构建到 dist/
```

### v2 exe 打包
```bash
# 1. 同步前端源码到 v2-app
# （手动复制 v2/frontend/src/ 到 v2-app/frontend/src/）

# 2. 在 v2-app/frontend/ 构建
cd v2-app/frontend
npm run build

# 3. 打包 exe（必须在 v2-app/ 目录执行）
cd v2-app
py -3.14 -m PyInstaller AppTimer.spec --noconfirm
# 输出: v2-app/dist/AppTimer.exe
```

### 本地运行 v2（开发模式）
```bash
cd v2-app
py -3.14 run.py
```

### 网站
```bash
cd website-v2
npm install
npx vitepress dev     # 本地开发
npx vitepress build --base /apptimer/  # 生产构建
```

## v2 架构

### 后端（Python）
- `backend/main.py`：入口，包含 HTTP 服务器、pywebview 窗口、托盘图标、单实例检测
- `backend/tracker.py`：`UsageTracker` 类，数据采集核心，无 UI 依赖
- `backend/window_detect.py`：Windows API 三级降级进程检测（OpenProcess → LimitedInfo → CreateToolhelp32Snapshot）
- `backend/startup.py`：注册表开机自启动管理
- `run.py`：PyInstaller 入口，处理 MEIPASS 路径

### 前端（Vue3）
- `App.vue`：主布局，3 秒轮询 `getSnapshot()`，tab 切换用 `v-if`
- `api.js`：HTTP 客户端，相对路径 `/api/` 调用后端
- 组件：TodayTab, CumulativeTab, ChartTab, TrendTab, CategoriesTab, HistoryTab, SettingsTab
- 深色主题：`--bg: #08080d`，`font-weight: 300`，白色调

### 数据流
```
前端 fetch("/api/xxx") → HTTP 服务器 → _call_api() → UsageTracker 方法 → JSON 响应
```

### 单实例机制
- 互斥体名：`Local\AppTimer_SingleInstance`（v1/v2 共用）
- `_is_duplicate_instance()`：创建 mutex → 若已存在则用 `EnumWindows` 找旧窗口 → 找到则恢复，找不到则强杀僵尸进程后接管
- `_g_mutex` 必须是模块级变量（防止 GC 释放 handle）

### 托盘图标
- pystray 在非 daemon 线程运行（`daemon=False`）
- `_init_tray()` 在 `webview.start()` 之前调用
- X 按钮 → `_on_closing()` 返回 `False` + `window.minimize()`

### Windows API 使用
- `ctypes.windll.user32`：FindWindowW, ShowWindow, EnumWindows, SendMessageW, SetForegroundWindow
- `ctypes.windll.kernel32`：CreateMutexW, GetLastError, OpenProcess, CreateToolhelp32Snapshot
- 窗口标题固定为 `"程序使用时间追踪器 v2.0"`（用于 FindWindowW）

## 数据存储

数据目录：`{Desktop}\程序使用记录\`
```
程序使用记录/
├── 2026-05-30/
│   ├── 数据.json        # 今日使用记录
│   └── 报告.txt         # 今日文本报告
├── 累计数据.json         # 跨天累计
├── 分类标签.json         # 程序分类
├── 使用目标.json         # 每日目标
└── 设置.json            # 用户设置
```

## 依赖

- Python 3.14，关键包：pywebview, pythonnet, pystray, Pillow, fpdf2
- 前端：Vue 3.5, ECharts 5.6, Tailwind CSS 4, Vite 6
- 网站：VitePress

## 注意事项

- PyInstaller 打包必须在 `v2-app/` 目录执行（spec 使用相对路径）
- `fpdf` 中文字体依赖 `C:\Windows\Fonts\msyh.ttc`（微软雅黑）
- v2 exe 窗口固定 900×680，`resizable=False`
- HTTP 服务器端口从 17778 开始，冲突自动 +1
- `os._exit(0)` 用于强制退出（pywebview 事件循环可能不响应 `sys.exit()`）
