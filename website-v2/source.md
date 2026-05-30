# 源代码

AppTimer v2 采用前后端分离架构，共约 1500 行代码。

## 项目结构

```
v2/
├── backend/
│   ├── main.py           # HTTP 服务入口 + API 路由
│   ├── tracker.py        # 使用追踪核心逻辑
│   ├── window_detect.py  # Windows API 窗口检测
│   └── startup.py        # 开机自启动管理
└── frontend/
    └── src/
        ├── App.vue       # 主界面（7 标签页）
        ├── api.js        # API 客户端
        ├── components/   # Vue 组件
        │   ├── TodayTab.vue
        │   ├── CumulativeTab.vue
        │   ├── ChartTab.vue
        │   ├── TrendTab.vue
        │   ├── CategoriesTab.vue
        │   ├── HistoryTab.vue
        │   └── SettingsTab.vue
        ├── main.js
        └── style.css
```

## 核心文件

### backend/tracker.py — 追踪引擎

<<< @/tracker.py

### backend/main.py — HTTP 服务

<<< @/main.py
