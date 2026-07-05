# AppTimer

Windows 程序使用时间追踪器。自动记录每个程序的使用时长，支持分类标签、每日目标、趋势图表、数据导出。

## 下载

- [下载 v2（推荐）](https://github.com/zjoachim/apptimer/releases/latest) — pywebview + Vue3 深色界面
- [下载 v1](https://github.com/zjoachim/apptimer/releases/latest) — Tkinter 经典界面

## 功能

- **自动追踪**：后台静默记录前台程序使用时间，2 秒检测一次
- **空闲检测**：超过阈值自动暂停计时（默认 120 秒）
- **分类标签**：按程序分类（工作/学习/娱乐/其他），支持浏览器网站识别
- **每日目标**：设定使用目标，超时提醒
- **趋势图表**：ECharts 可视化，柱状图/饼图/趋势线
- **数据导出**：PDF 报告、CSV 表格
- **累计统计**：跨天累计使用数据，自动校验防丢失
- **开机自启**：注册表自启动，后台常驻

## 界面（v2）

深色主题，7 个标签页：

| 标签 | 内容 |
|------|------|
| 概览 | 今日使用总览，当前程序，实时进度条 |
| 累计 | 跨天累计统计，柱状图/饼图 |
| 图表 | 累计使用分布可视化 |
| 趋势 | 单程序多日趋势线 |
| 分类 | 程序分类管理 + 每日目标设定 |
| 历史 | 按日期查看历史报告 |
| 设置 | 空闲阈值、保存间隔、自启动、卸载 |

## 架构

```
v2/frontend/          Vue3 + Tailwind + ECharts 前端源码
v2-app/               完整应用（后端 + 前端 dist + 打包配置）
v2-app/backend/       Python 后端（HTTP 服务器 + 数据追踪）
v2-app/backend/main.py    入口：pywebview 窗口 + HTTP API + 托盘图标
v2-app/backend/tracker.py 数据核心：UsageTracker 类
apptimer/             v1 源码（单文件 Tkinter）
website-v2/           项目官网（VitePress）
```

### 数据流

```
前端 fetch("/api/xxx") → HTTP 服务器 → _call_api() → UsageTracker → JSON 响应
```

### 数据存储

```
{桌面}/程序使用记录/
├── 2026-06-28/数据.json    今日使用记录
├── 累计数据.json           跨天累计
├── 分类标签.json           程序分类
├── 使用目标.json           每日目标
└── 设置.json              用户设置
```

## 开发

### 环境

- Python 3.14
- Node.js 18+

### v2 前端

```bash
cd v2/frontend
npm install
npm run build
```

### v2 exe 打包

```bash
# 同步前端到 v2-app
cp -r v2/frontend/src/* v2-app/frontend/src/

# 构建前端
cd v2-app/frontend && npm run build

# 打包 exe
cd v2-app
py -3.14 -m PyInstaller AppTimer.spec --noconfirm
```

### 本地运行

```bash
cd v2-app
py -3.14 run.py
```

### 网站

```bash
cd website-v2
npm install
npx vitepress dev
```

## 依赖

**Python**：pywebview, pythonnet, pystray, Pillow, fpdf2

**前端**：Vue 3.5, ECharts 5.6, Tailwind CSS 4, Vite 6

## 许可

MIT
