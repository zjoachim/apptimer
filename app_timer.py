"""
Windows 程序使用时间追踪器 v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
数据层面：
  ✓ 每日文件按日期子文件夹组织
  ✓ 自动清理过期数据（可配置保留天数）
  ✓ 周报 / 月报自动生成
  ✓ 使用趋势（跨天对比）
  ✓ 导出 CSV
  ✓ 程序分类标签（工作/学习/娱乐/其他）
UI 层面：
  ✓ 深色模式
  ✓ 饼图 / 柱状图可视化
  ✓ 每日使用目标设定 + 超时提醒
  ✓ 程序连续使用提醒（休息提示）
修复：
  ✓ last_save_time 初始化
  ✓ tk.BooleanVar 创建顺序
  ✓ 自启动状态标签
"""

import os
import sys
import time
import json
import csv
import ctypes
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# ════════════════════════════════════════════════════════
# 隐藏双击 .py 时的控制台窗口
# ════════════════════════════════════════════════════════
def _hide_console():
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        pass
_hide_console()

def _get_windows_accent():
    """从注册表读 Windows 主题色，失败返回默认蓝"""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\DWM")
        color_dword, _ = winreg.QueryValueEx(key, "AccentColor")
        winreg.CloseKey(key)
        r = color_dword & 0xFF
        g = (color_dword >> 8) & 0xFF
        b = (color_dword >> 16) & 0xFF
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return "#0078d4"

def _get_windows_dark_mode():
    """读取 Windows 深色偏好"""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return val == 0
    except Exception:
        return False

# ============================================================
# Windows API
# ============================================================
import ctypes.wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi
MAX_PATH = 260


def _get_exe_version_field(exe_path, field_name):
    """读取 exe 的版本信息字段（如 FileDescription），失败返回空"""
    try:
        size = ctypes.windll.version.GetFileVersionInfoSizeW(exe_path, None)
        if size == 0:
            return ""
        buf = ctypes.create_string_buffer(size)
        ctypes.windll.version.GetFileVersionInfoW(exe_path, 0, size, buf)
        # 获取语言/代码页
        lang_ptr = ctypes.c_void_p()
        lang_len = ctypes.c_uint()
        ctypes.windll.version.VerQueryValueW(buf, r"\VarFileInfo\Translation",
            ctypes.byref(lang_ptr), ctypes.byref(lang_len))
        if lang_len.value < 4:
            return ""
        lang, codepage = struct.unpack("<HH", ctypes.string_at(lang_ptr, 4))
        sub_path = rf"\StringFileInfo\{lang:04x}{codepage:04x}\{field_name}"
        ptr = ctypes.c_void_p()
        length = ctypes.c_uint()
        if ctypes.windll.version.VerQueryValueW(buf, sub_path, ctypes.byref(ptr), ctypes.byref(length)):
            return ctypes.wstring_at(ptr, length.value - 1) if length.value > 1 else ""
    except Exception:
        pass
    return ""


def get_active_window_process_name():
    hwnd = user32.GetForegroundWindow()
    if hwnd == 0:
        return "", ""
    pid = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    handle = kernel32.OpenProcess(0x0400 | 0x0010, False, pid.value)
    if handle == 0:
        return "", ""
    # 进程名
    name_buf = ctypes.create_unicode_buffer(MAX_PATH)
    name_size = ctypes.wintypes.DWORD(MAX_PATH)
    name = ""
    if psapi.GetModuleBaseNameW(handle, None, name_buf, name_size):
        name = name_buf.value.lower()
    # 完整路径
    path_buf = ctypes.create_unicode_buffer(MAX_PATH)
    path_size = ctypes.wintypes.DWORD(MAX_PATH)
    exe_path = ""
    if psapi.QueryFullProcessImageNameW(handle, 0, path_buf, ctypes.byref(path_size)):
        exe_path = path_buf.value
    kernel32.CloseHandle(handle)
    return name, exe_path


def get_active_window_title():
    hwnd = user32.GetForegroundWindow()
    if hwnd == 0:
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def get_idle_seconds():
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.wintypes.UINT),
            ("dwTime", ctypes.wintypes.DWORD),
        ]
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if user32.GetLastInputInfo(ctypes.byref(lii)):
        return (kernel32.GetTickCount64() - lii.dwTime) / 1000.0
    return 0.0


def get_desktop_path():
    desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
    if os.path.exists(desktop):
        return desktop
    return str(Path.home() / "Desktop")


# ============================================================
# 工具函数
# ============================================================

def fmt_duration(seconds):
    if seconds < 0:
        seconds = 0
    seconds = int(seconds)
    h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
    if h > 0:
        return f"{h}小时{m}分"
    elif m > 0:
        return f"{m}分{s}秒"
    return f"{s}秒"


def week_range(date):
    monday = date - timedelta(days=date.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def month_range(date):
    first = date.replace(day=1)
    if first.month == 12:
        last = first.replace(year=first.year + 1, month=1) - timedelta(days=1)
    else:
        last = first.replace(month=first.month + 1) - timedelta(days=1)
    return first, last


# ============================================================
# 核心追踪器
# ============================================================

class UsageTracker:
    DATA_FOLDER_NAME = "程序使用记录"

    def __init__(self, data_dir=None, on_data_changed=None, on_reminder=None):
        if data_dir is None:
            data_dir = Path(get_desktop_path()) / self.DATA_FOLDER_NAME
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.today_str = datetime.now().strftime("%Y-%m-%d")
        self.today_folder = self.data_dir / self.today_str
        self.today_folder.mkdir(parents=True, exist_ok=True)

        self.daily_data_file = self.today_folder / "数据.json"
        self.daily_report_file = self.today_folder / "报告.txt"
        self.cumulative_file = self.data_dir / "累计数据.json"
        self.categories_file = self.data_dir / "分类标签.json"
        self.goals_file = self.data_dir / "使用目标.json"
        self.settings_file = self.data_dir / "设置.json"

        self.current_app = ""
        self.current_window = ""
        self.app_start_time = datetime.now()
        self.today_usage = {}
        self.cumulative_usage = {}
        self.session_log = []
        self.last_save_time = datetime.now()           # ★ 修复：初始化

        self.idle_threshold = 120
        self.auto_save_interval = 30
        self.retention_days = 60
        self.reminder_interval = 45 * 60
        self.accent_color = _get_windows_accent()
        self.goals = {}
        self.categories = {}
        self.running = True
        self._dirty = False
        self._consecutive_errors = 0
        self.data_lock = threading.Lock()
        self.on_data_changed = on_data_changed
        self.on_reminder = on_reminder
        self._last_reminder = {}
        self._desc_cache = {}  # 进程名 → 版本信息 FileDescription

        self.ignore_list = [
            "", "explorer.exe", "searchhost.exe",
            "shellexperiencehost.exe", "systemsettings.exe",
            "textinputhost.exe", "applicationframehost.exe",
            "python.exe", "pythonw.exe", "py.exe",
            "cmd.exe", "powershell.exe",
        ]

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.FileHandler(self.today_folder / "日志.log", encoding="utf-8")]
        )
        self._log_handler = logging.getLogger().handlers[0] if logging.getLogger().handlers else None

        self._load_all()
        self._cleanup_old_files()

        logging.info(f"追踪器已启动 v1.0 → {self.data_dir}")

    def _load_all(self):
        self._load_json(self.daily_data_file, "usage", self.today_usage, filter_ignore=True)
        self._load_json(self.cumulative_file, "cumulative", self.cumulative_usage, filter_ignore=True)
        self._load_json(self.categories_file, "categories", self.categories)
        self._load_json(self.goals_file, "goals", self.goals)
        self._load_settings()

    def _load_json(self, path, key, target, filter_ignore=False):
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    raw = data.get(key, {})
                    if filter_ignore:
                        raw = {k: v for k, v in raw.items() if k not in self.ignore_list}
                    target.clear()
                    target.update(raw)
            except Exception as e:
                logging.warning(f"加载数据失败 {path}: {e}")

    def _load_settings(self):
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    s = json.load(f)
                    self.idle_threshold = s.get("idle_threshold", 120)
                    self.auto_save_interval = s.get("auto_save_interval", 30)
                    self.retention_days = s.get("retention_days", 60)
                    self.reminder_interval = s.get("reminder_interval", 45 * 60)
                    self.accent_color = s.get("accent_color", "#0078d4")
            except Exception:
                pass

    def _save_data(self):
        with self.data_lock:
            usage_snapshot = dict(self.today_usage)
            sessions_snapshot = list(self.session_log[-1000:])
            cum_snapshot = dict(self.cumulative_usage)
            self._dirty = False
        with open(self.daily_data_file, "w", encoding="utf-8") as f:
            json.dump({"date": self.today_str, "usage": usage_snapshot, "sessions": sessions_snapshot}, f, ensure_ascii=False, indent=2)
        with open(self.daily_report_file, "w", encoding="utf-8") as f:
            f.write(self._build_report())
        with open(self.cumulative_file, "w", encoding="utf-8") as f:
            json.dump({"cumulative": cum_snapshot}, f, ensure_ascii=False, indent=2)
        if len(self.session_log) > 2000:
            with self.data_lock:
                self.session_log = self.session_log[-1000:]

    def _save_settings(self):
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump({
                "idle_threshold": self.idle_threshold,
                "auto_save_interval": self.auto_save_interval,
                "retention_days": self.retention_days,
                "reminder_interval": self.reminder_interval,
                "accent_color": self.accent_color,
            }, f, ensure_ascii=False, indent=2)

    def save_categories(self):
        with self.data_lock:
            cat_snapshot = dict(self.categories)
        with open(self.categories_file, "w", encoding="utf-8") as f:
            json.dump({"categories": cat_snapshot}, f, ensure_ascii=False, indent=2)

    def save_goals(self):
        with self.data_lock:
            goals_snapshot = dict(self.goals)
        with open(self.goals_file, "w", encoding="utf-8") as f:
            json.dump({"goals": goals_snapshot}, f, ensure_ascii=False, indent=2)

    def _cleanup_old_files(self):
        if self.retention_days <= 0:
            return
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        for item in self.data_dir.iterdir():
            if item.is_dir() and item.name != self.today_str:
                try:
                    date = datetime.strptime(item.name, "%Y-%m-%d")
                    if date < cutoff:
                        import shutil
                        shutil.rmtree(item)
                        logging.info(f"清理过期数据: {item.name}")
                except ValueError:
                    pass

    def update(self):
        if not self.running:
            return
        now = datetime.now()

        new_today = now.strftime("%Y-%m-%d")
        if new_today != self.today_str:
            self._close_current_session(now)
            self._save_data()
            self._generate_weekly_report()
            self._generate_monthly_report()
            self.today_str = new_today
            self.today_folder = self.data_dir / self.today_str
            self.today_folder.mkdir(parents=True, exist_ok=True)
            self.daily_data_file = self.today_folder / "数据.json"
            self.daily_report_file = self.today_folder / "报告.txt"
            self.today_usage = {}
            self.session_log = []
            self._last_reminder = {}
            self._dirty = False
            self._cleanup_old_files()
            logger = logging.getLogger()
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s [%(levelname)s] %(message)s",
                handlers=[logging.FileHandler(self.today_folder / "日志.log", encoding="utf-8")]
            )
            self._log_handler = logger.handlers[0] if logger.handlers else None
            logging.info(f"日期切换 → {self.today_str}")

        if get_idle_seconds() > self.idle_threshold:
            self._close_current_session(now)
            if self._dirty:
                self._save_data()
                self.last_save_time = now
            return

        process_name, exe_path = get_active_window_process_name()
        if exe_path and process_name and process_name not in self._desc_cache:
            desc = _get_exe_version_field(exe_path, "FileDescription")
            self._desc_cache[process_name] = desc if desc else process_name
        window_title = get_active_window_title()

        if process_name in self.ignore_list or process_name.startswith("windows"):
            self._close_current_session(now)
            return

        app_id = process_name if process_name else "unknown"
        app_id = self._classify_window(app_id, window_title)

        if app_id != self.current_app:
            self._close_current_session(now)
            self.current_app = app_id
            self.current_window = window_title
            self.app_start_time = now
            if app_id not in self._last_reminder:
                self._last_reminder[app_id] = now

        self._check_reminder(now)

        if self._dirty and (now - self.last_save_time).total_seconds() >= self.auto_save_interval:
            self._save_data()
            self.last_save_time = now
            if self.on_data_changed:
                self.on_data_changed()

    def _close_current_session(self, now):
        if self.current_app:
            duration = (now - self.app_start_time).total_seconds()
            if duration >= 1.0:
                with self.data_lock:
                    self.today_usage[self.current_app] = self.today_usage.get(self.current_app, 0) + duration
                    self.cumulative_usage[self.current_app] = self.cumulative_usage.get(self.current_app, 0) + duration
                    self.session_log.append({
                        "app": self.current_app,
                        "window": self.current_window,
                        "start": self.app_start_time.isoformat(),
                        "end": now.isoformat(),
                        "duration_seconds": round(duration, 1),
                    })
                    self._dirty = True
        self.current_app = ""
        self.current_window = ""
        self.app_start_time = now

    def _localize_app(self, app):
        """翻译进程名：优先用 exe 版本信息中的 FileDescription，无则保留原名"""
        base = app
        tag = ""
        if " [" in app:
            base, tag = app.split(" [", 1)
            tag = " [" + tag
        friendly = self._desc_cache.get(base, base)
        return friendly + tag

    # 进程分组规则：浏览器 → 窗口标题关键词匹配
    SITE_RULES = [
        (["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"], [
            ("GitHub", "开发"), ("github", "开发"), ("GitLab", "开发"), ("Stack Overflow", "开发"),
            ("YouTube", "娱乐"), ("youtube", "娱乐"), ("Bilibili", "娱乐"), ("bilibili", "娱乐"),
            ("Netflix", "娱乐"), ("netflix", "娱乐"), ("iqiyi", "娱乐"), ("优酷", "娱乐"),
            ("腾讯视频", "娱乐"), ("斗鱼", "娱乐"), ("虎牙", "娱乐"),
            ("Google Docs", "工作"), ("Notion", "工作"), ("飞书", "工作"), ("钉钉", "工作"),
            ("微信", "社交"), ("WeChat", "社交"), ("知乎", "社交"), ("微博", "社交"),
            ("Twitter", "社交"), ("Reddit", "社交"), ("reddit", "社交"),
            ("百度", "搜索"), ("baidu", "搜索"), ("Google", "搜索"),
        ]),
        (["code.exe", "devenv.exe"], [
            ("app_timer.py", "开发·本工具"), ("app_timer", "开发·本工具"),
        ]),
    ]

    def _classify_window(self, app, title):
        for browsers, rules in self.SITE_RULES:
            if app in browsers and title:
                for keyword, tag in rules:
                    if keyword.lower() in title.lower():
                        return f"{app} [{tag}]"
        return app

    def _check_reminder(self, now):
        if not self.current_app or self.reminder_interval <= 0:
            return
        elapsed = (now - self.app_start_time).total_seconds()
        last = self._last_reminder.get(self.current_app, self.app_start_time)
        since_last = (now - last).total_seconds()
        if elapsed >= self.reminder_interval and since_last >= self.reminder_interval:
            self._last_reminder[self.current_app] = now
            if self.on_reminder:
                self.on_reminder(self.current_app, elapsed)

    def check_goals(self):
        with self.data_lock:
            goals = dict(self.goals)
            usage = dict(self.today_usage)
        exceeded = []
        for app, goal_sec in goals.items():
            used = usage.get(app, 0)
            if used > goal_sec:
                exceeded.append((app, used, goal_sec))
        return exceeded

    def _build_report(self):
        if not self.today_usage:
            return f"=== {self.today_str} 程序使用报告 ===\n\n今日暂无使用记录\n"
        sorted_apps = sorted(self.today_usage.items(), key=lambda x: x[1], reverse=True)
        total = sum(v for _, v in sorted_apps)
        lines = [
            f"=== {self.today_str} 程序使用报告 ===", "",
            f"今日总使用时间: {fmt_duration(total)}",
            f"记录会话数: {len(self.session_log)}",
            "-" * 70, "",
        ]
        for app, sec in sorted_apps:
            pct = (sec / total * 100) if total > 0 else 0
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            cat = self.categories.get(app, "未分类")
            cum = self.cumulative_usage.get(app, 0)
            lines.append(f"{bar} {app:<25s} [{cat}] 今日{fmt_duration(sec):>8s}  累计{fmt_duration(cum):>8s} ({pct:5.1f}%)")
        lines.append("")
        lines.append(f"报告生成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return "\n".join(lines)

    def _generate_weekly_report(self):
        yesterday = datetime.now() - timedelta(days=1)
        mon, sun = week_range(yesterday)
        self._generate_period_report("周报", mon, sun)

    def _generate_monthly_report(self):
        yesterday = datetime.now() - timedelta(days=1)
        if yesterday.day <= 2:
            first, last = month_range(yesterday)
            self._generate_period_report("月报", first, last)

    def _generate_period_report(self, prefix, start, end):
        merged = defaultdict(float)
        total_sessions = 0
        days_found = 0
        d = start
        while d <= end:
            data_file = self.data_dir / d.strftime("%Y-%m-%d") / "数据.json"
            if data_file.exists():
                try:
                    with open(data_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for app, sec in data.get("usage", {}).items():
                            merged[app] += sec
                        total_sessions += len(data.get("sessions", []))
                    days_found += 1
                except Exception:
                    pass
            d += timedelta(days=1)
        if not merged:
            return
        total = sum(merged.values())
        sorted_apps = sorted(merged.items(), key=lambda x: x[1], reverse=True)
        label = f"{start.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}"
        filename = f"{prefix}_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.txt"
        lines = [
            f"=== {prefix}: {label} ===", "",
            f"统计天数: {days_found}",
            f"总使用时间: {fmt_duration(total)}",
            f"总会话数: {total_sessions}",
            f"日均使用: {fmt_duration(total / max(days_found, 1))}",
            "-" * 70, "",
        ]
        for app, sec in sorted_apps[:30]:
            pct = (sec / total * 100) if total > 0 else 0
            cat = self.categories.get(app, "未分类")
            lines.append(f"  {app:<30s} [{cat}] {fmt_duration(sec):>10s} ({pct:5.1f}%)")
        lines.append("")
        lines.append(f"自动生成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_path = self.data_dir / filename
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logging.info(f"{prefix}已生成: {filename}")

    def get_trend_data(self, app, days=7):
        with self.data_lock:
            today_sec = self.today_usage.get(app, 0)
        trend = []
        for i in range(days - 1, -1, -1):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            if date_str == self.today_str:
                sec = today_sec
            else:
                data_file = self.data_dir / date_str / "数据.json"
                sec = 0
                if data_file.exists():
                    try:
                        with open(data_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            sec = data.get("usage", {}).get(app, 0)
                    except Exception:
                        pass
            trend.append((date_str, sec))
        return trend

    def get_all_available_dates(self):
        dates = []
        for item in sorted(self.data_dir.iterdir()):
            if item.is_dir():
                try:
                    datetime.strptime(item.name, "%Y-%m-%d")
                    dates.append(item.name)
                except ValueError:
                    pass
        return dates

    def export_csv(self, target_path=None):
        if target_path is None:
            target_path = self.today_folder / f"导出_{self.today_str}.csv"
        with self.data_lock:
            app_sessions = defaultdict(int)
            for s in self.session_log:
                app_sessions[s["app"]] += 1
            sorted_apps = sorted(self.today_usage.items(), key=lambda x: x[1], reverse=True)
            cum_snapshot = dict(self.cumulative_usage)
            cat_snapshot = dict(self.categories)
        rows = [["程序", "分类", "今日使用(秒)", "今日使用", "累计使用(秒)", "累计使用", "会话数"]]
        for app, sec in sorted_apps:
            cum = cum_snapshot.get(app, 0)
            cat = cat_snapshot.get(app, "")
            rows.append([app, cat, round(sec), fmt_duration(sec), round(cum), fmt_duration(cum), app_sessions[app]])
        with open(target_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        return str(target_path)

    def export_cumulative_csv(self, target_path=None):
        if target_path is None:
            target_path = self.data_dir / f"累计导出_{datetime.now().strftime('%Y%m%d')}.csv"
        with self.data_lock:
            sorted_apps = sorted(self.cumulative_usage.items(), key=lambda x: x[1], reverse=True)
            cat_snapshot = dict(self.categories)
        rows = [["程序", "分类", "累计使用(秒)", "累计使用"]]
        for app, sec in sorted_apps:
            cat = cat_snapshot.get(app, "")
            rows.append([app, cat, round(sec), fmt_duration(sec)])
        with open(target_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        return str(target_path)

    def get_sorted_usage(self):
        with self.data_lock:
            return sorted(self.today_usage.items(), key=lambda x: x[1], reverse=True)

    def get_sorted_cumulative(self):
        with self.data_lock:
            return sorted(self.cumulative_usage.items(), key=lambda x: x[1], reverse=True)

    def get_total_seconds(self):
        with self.data_lock:
            return sum(self.today_usage.values())

    def get_cumulative_total(self):
        with self.data_lock:
            return sum(self.cumulative_usage.values())

    def export_pdf(self, target_path=None):
        from fpdf import FPDF
        if target_path is None:
            target_path = self.today_folder / f"报告_{self.today_str}.pdf"
        pdf = FPDF()
        pdf.add_page()
        # 中文字体
        font_path = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts", "msyh.ttc")
        if os.path.exists(font_path):
            pdf.add_font("YaHei", "", font_path, uni=True)
            pdf.add_font("YaHei", "B", font_path, uni=True)
        else:
            pdf.add_font("YaHei", "", font_path, uni=True)  # will use default
        pdf.set_font("YaHei", "B", 18)
        pdf.cell(0, 12, f"程序使用报告 - {self.today_str}", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(6)
        with self.data_lock:
            usage = dict(self.today_usage)
            sessions = list(self.session_log)
            cum = dict(self.cumulative_usage)
            cats = dict(self.categories)
        total = sum(usage.values())
        pdf.set_font("YaHei", "", 11)
        pdf.cell(0, 8, f"总使用时间: {fmt_duration(total)}  会话数: {len(sessions)}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)
        # 表格头
        pdf.set_font("YaHei", "B", 10)
        pdf.set_fill_color(0, 120, 212)
        pdf.set_text_color(255, 255, 255)
        col_w = [60, 32, 40, 40, 24]
        headers = ["程序", "分类", "今日", "累计", "占比"]
        for i, h in enumerate(headers):
            pdf.cell(col_w[i], 8, h, border=1, fill=True, align="C")
        pdf.ln()
        # 表格行
        pdf.set_text_color(33, 33, 33)
        sorted_apps = sorted(usage.items(), key=lambda x: x[1], reverse=True)
        for j, (app, sec) in enumerate(sorted_apps):
            pdf.set_font("YaHei", "", 9)
            if j % 2 == 0:
                pdf.set_fill_color(240, 244, 248)
            else:
                pdf.set_fill_color(255, 255, 255)
            pct = f"{sec / total * 100:.1f}%" if total > 0 else "0%"
            row = [app[:28], cats.get(app, "")[:6], fmt_duration(sec), fmt_duration(cum.get(app, 0)), pct]
            for i, val in enumerate(row):
                pdf.cell(col_w[i], 7, val, border=1, fill=True, align="C" if i > 0 else "L")
            pdf.ln()
        pdf.ln(6)
        pdf.set_font("YaHei", "", 8)
        pdf.set_text_color(128, 128, 128)
        pdf.cell(0, 6, f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", align="R")
        pdf.output(str(target_path))
        return str(target_path)

    def get_category_stats(self):
        with self.data_lock:
            cat_stats = defaultdict(float)
            for app, sec in self.today_usage.items():
                cat = self.categories.get(app, "未分类")
                cat_stats[cat] += sec
        return dict(cat_stats)

    def close(self):
        self.running = False
        self._close_current_session(datetime.now())
        with self.data_lock:
            self._dirty = True
        self._save_data()
        logging.info("追踪器已关闭 v1.0")


# ============================================================
# 开机自启动
# ============================================================

def add_to_startup():
    import winreg
    script_path = os.path.abspath(sys.argv[0])
    if script_path.endswith(".py"):
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        command = f'"{pythonw}" "{script_path}" --silent'
    else:
        command = f'"{script_path}" --silent'
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "AppUsageTimer", 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)
        return True, ""
    except Exception as e:
        return False, str(e)


def remove_from_startup():
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, "AppUsageTimer")
        winreg.CloseKey(key)
        return True, ""
    except FileNotFoundError:
        return False, "未找到自启动项"
    except Exception as e:
        return False, str(e)


def is_startup_enabled():
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, "AppUsageTimer")
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


# ============================================================
# UI
# ============================================================

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import math
import sv_ttk


class AppTimerUI:
    def __init__(self, silent=False):
        # ★ 修复：root 必须在所有 tk 变量之前创建
        self.root = tk.Tk()
        self.root.title("程序使用时间追踪器 v1.0")
        self.root.geometry("800x680")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.dark_mode = tk.BooleanVar(value=_get_windows_dark_mode())

        # 窗口图标
        try:
            from PIL import Image, ImageDraw, ImageTk
            icon_img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            d = ImageDraw.Draw(icon_img)
            d.ellipse([2, 2, 61, 61], outline=(52, 152, 219), width=4)
            d.line([(32, 32), (32, 14)], fill=(52, 152, 219), width=4)
            d.line([(32, 32), (42, 32)], fill=(52, 152, 219), width=3)
            self._icon_tk = ImageTk.PhotoImage(icon_img)
            self.root.iconphoto(True, self._icon_tk)
        except Exception:
            self._icon_tk = None

        # 自启动状态标签（先占位）
        self.startup_status_label = None

        self.tracker = UsageTracker(on_data_changed=self.refresh, on_reminder=self._on_reminder)
        self.tray_icon = None
        self._init_tray()

        sv_ttk.set_theme("dark" if _get_windows_dark_mode() else "light")
        self._build_ui()
        self._apply_theme()
        self.refresh()

        if silent:
            self.root.after(500, self._minimize_to_tray)
        else:
            self.root.deiconify()
        self.root.after(100, self._pulse_dot)

    # ════════════════════════════════════════
    # 主题
    # ════════════════════════════════════════

    @property
    def colors(self):
        a = getattr(self.tracker, "accent_color", "#0078d4") if hasattr(self, "tracker") else "#0078d4"
        if self.dark_mode.get():
            return {
                "bg": "#16162b", "fg": "#cdd6f4", "card": "#1e1e3a",
                "accent": a, "warn": "#f9e2af", "danger": "#f38ba8",
                "bar_bg": "#313155", "text_secondary": "#a6adc8",
            }
        else:
            return {
                "bg": "#f0f4f8", "fg": "#1e293b", "card": "#ffffff",
                "accent": a, "warn": "#f59e0b", "danger": "#ef4444",
                "bar_bg": "#e2e8f0", "text_secondary": "#64748b",
            }

    def _apply_theme(self):
        c = self.colors
        self.root.configure(bg=c["bg"])
        sv_ttk.set_theme("dark" if self.dark_mode.get() else "light")

        def restyle(w):
            """递归更新所有 tk 控件配色"""
            if isinstance(w, tk.Label):
                try: w.configure(bg=c["bg"], fg=c["fg"])
                except: pass
            elif isinstance(w, tk.Frame):
                try: w.configure(bg=c["bg"])
                except: pass
            elif isinstance(w, tk.Text):
                try: w.configure(bg=c["card"], fg=c["fg"], insertbackground=c["fg"])
                except: pass
            elif isinstance(w, tk.Canvas):
                try: w.configure(bg=c["bg"])
                except: pass
            for child in w.winfo_children():
                restyle(child)

        restyle(self.root)

        # 标题栏 → accent 色
        self.header.configure(bg=c["accent"])
        for w in self.header.winfo_children():
            if isinstance(w, tk.Label):
                try: w.configure(bg=c["accent"], fg="white")
                except: pass
            elif isinstance(w, tk.Canvas):
                try: w.configure(bg=c["accent"])
                except: pass
        self.status_label.configure(
            fg="#cdd6f4" if self.dark_mode.get() else "white")

        # 图表 / 卡片 / 历史 → card 色
        for w in (self.today_card, self.chart_canvas, self.trend_canvas):
            try: w.configure(bg=c["card"])
            except: pass
        self.hist_text.configure(bg=c["card"], fg=c["fg"])
        self._draw_dot()
        self.refresh()

    def _draw_cat_bar(self, canvas, color, pct, cat):
        c = self.colors
        canvas.delete("all")
        cw = max(canvas.winfo_width(), 50)
        fill_w = max(int(cw * pct / 100), 6)
        self._rounded_rect(canvas, 0, 2, fill_w, 24, radius=6, fill=color, outline="")
        canvas.create_text(cw // 2, 13, text=f"{cat} {pct:.0f}%",
                           fill="white" if pct > 10 else c["fg"], font=("Microsoft YaHei", 8, "bold"))

    def _rounded_rect(self, canvas, x1, y1, x2, y2, radius=8, fill="", outline=""):
        """在 canvas 上画圆角矩形，返回所有 item id 的列表"""
        ids = []
        r = radius
        ids.append(canvas.create_arc(x1, y1, x1 + 2 * r, y1 + 2 * r, start=90, extent=90, fill=fill, outline=outline))
        ids.append(canvas.create_arc(x2 - 2 * r, y1, x2, y1 + 2 * r, start=0, extent=90, fill=fill, outline=outline))
        ids.append(canvas.create_arc(x1, y2 - 2 * r, x1 + 2 * r, y2, start=180, extent=90, fill=fill, outline=outline))
        ids.append(canvas.create_arc(x2 - 2 * r, y2 - 2 * r, x2, y2, start=270, extent=90, fill=fill, outline=outline))
        ids.append(canvas.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline=outline))
        ids.append(canvas.create_rectangle(x1, y1 + r, x2, y2 - r, fill=fill, outline=outline))
        return ids

    def _draw_today_card(self, total_sec):
        c = self.colors
        canvas = self.today_card
        w = (lambda v: v if v > 50 else 720)(canvas.winfo_width())
        h = 60
        canvas.delete("all")
        self._rounded_rect(canvas, 2, 4, w - 2, h - 4, radius=12, fill=c["accent"], outline="")
        canvas.create_text(w // 2, h // 2, text=f"今日总使用时间: {fmt_duration(total_sec)}",
                           fill="white", font=("Microsoft YaHei", 13, "bold"))

    def _draw_dot(self):
        canvas = self.status_dot
        canvas.delete("all")
        r = max(2, int(3.5 * self._pulse_val))
        canvas.create_oval(10 - r, 10 - r, 10 + r, 10 + r, fill="#4ade80", outline="")

    def _pulse_dot(self):
        step = 0.06
        if self._pulse_dir == 1:
            self._pulse_val = min(self._pulse_val + step, 1.0)
            if self._pulse_val >= 1.0:
                self._pulse_dir = -1
        else:
            self._pulse_val = max(self._pulse_val - step, 0.2)
            if self._pulse_val <= 0.2:
                self._pulse_dir = 1
        self._draw_dot()
        self.root.after(120, self._pulse_dot)

    # ════════════════════════════════════════
    # 构建界面
    # ════════════════════════════════════════

    def _build_ui(self):
        # 顶部标题栏
        self.header = tk.Frame(self.root, height=46)
        self.header.pack(fill=tk.X, padx=0, pady=0)
        self.header.pack_propagate(False)

        tk.Label(self.header, text="程序使用时间追踪器", font=("Microsoft YaHei", 12, "bold"),
                 bg=self.colors["accent"], fg="white").pack(side=tk.LEFT, padx=16, pady=10)

        self.time_label = tk.Label(self.header, text="", font=("Microsoft YaHei", 9),
                                   bg=self.colors["accent"], fg="white")
        self.time_label.pack(side=tk.RIGHT, padx=4)

        # 脉冲状态灯
        self.status_dot = tk.Canvas(self.header, width=20, height=20, highlightthickness=0,
                                    bg=self.colors["accent"])
        self.status_dot.pack(side=tk.RIGHT, padx=2)
        self._pulse_val = 1.0
        self._pulse_dir = -1

        self.status_label = tk.Label(self.header, text="追踪中", font=("Microsoft YaHei", 9),
                                     bg=self.colors["accent"], fg="#cdd6f4" if self.dark_mode.get() else "white")
        self.status_label.pack(side=tk.RIGHT, padx=2)

        self.dark_btn = ttk.Button(self.header, text="深色模式", command=self._toggle_dark_mode)
        self.dark_btn.pack(side=tk.RIGHT, padx=(16, 16))

        nb = ttk.Notebook(self.root)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self._build_today_tab(nb)
        self._build_cumulative_tab(nb)
        self._build_chart_tab(nb)
        self._build_trend_tab(nb)
        self._build_categories_tab(nb)
        self._build_history_tab(nb)
        self._build_settings_tab(nb)

        bottom = tk.Frame(self.root, bg=self.colors["bg"])
        bottom.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(bottom, text="打开文件夹", command=self._open_folder).pack(side=tk.LEFT, padx=3)
        ttk.Button(bottom, text="导出 CSV", command=self._export_csv).pack(side=tk.LEFT, padx=3)
        ttk.Button(bottom, text="导出 PDF", command=self._export_pdf).pack(side=tk.LEFT, padx=3)
        ttk.Button(bottom, text="最小化到托盘", command=self._minimize_to_tray).pack(side=tk.LEFT, padx=3)
        ttk.Button(bottom, text="退出", command=self._on_close).pack(side=tk.RIGHT, padx=3)

    def _build_today_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text="  今日概览  ")

        self.today_card = tk.Canvas(tab, height=60, highlightthickness=0)
        self.today_card.pack(fill=tk.X, padx=20, pady=8)

        self.cat_frame = tk.Frame(tab, bg=self.colors["bg"])
        self.cat_frame.pack(fill=tk.X, padx=20)

        ttk.Separator(tab, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=20, pady=5)

        hdr = tk.Frame(tab, bg=self.colors["bg"])
        hdr.pack(fill=tk.X, padx=20)
        for text, w, expand in [("程序", 14, True), ("分类", 6, False), ("今日", 8, False), ("累计", 8, False), ("占比", 5, False)]:
            kw = {"fill": tk.X, "expand": True} if expand else {}
            tk.Label(hdr, text=text, font=("Microsoft YaHei", 9, "bold"), width=w, anchor=tk.W,
                     bg=self.colors["bg"], fg=self.colors["fg"]).pack(side=tk.LEFT, **kw)

        canvas_frame = ttk.Frame(tab)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        self.canvas = tk.Canvas(canvas_frame, highlightthickness=0, bg=self.colors["bg"])
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.list_frame = tk.Frame(self.canvas, bg=self.colors["bg"])
        self.list_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))

    def _build_cumulative_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text="  累计统计  ")

        self.cum_total = tk.Label(tab, text="累计总使用时间: --", font=("Microsoft YaHei", 12, "bold"),
                                  bg=self.colors["bg"], fg=self.colors["fg"])
        self.cum_total.pack(pady=8)

        info = tk.Label(tab, text="（自首次使用以来的所有累计数据）", fg=self.colors["text_secondary"],
                        bg=self.colors["bg"])
        info.pack()

        ttk.Separator(tab, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=20, pady=5)

        hdr = tk.Frame(tab, bg=self.colors["bg"])
        hdr.pack(fill=tk.X, padx=20)
        for text, w, expand in [("程序", 18, True), ("累计使用", 12, False), ("占比", 5, False)]:
            kw = {"fill": tk.X, "expand": True} if expand else {}
            tk.Label(hdr, text=text, font=("Microsoft YaHei", 9, "bold"), width=w, anchor=tk.W,
                     bg=self.colors["bg"], fg=self.colors["fg"]).pack(side=tk.LEFT, **kw)

        cf = ttk.Frame(tab)
        cf.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        self.cum_canvas = tk.Canvas(cf, highlightthickness=0, bg=self.colors["bg"])
        sb = ttk.Scrollbar(cf, orient=tk.VERTICAL, command=self.cum_canvas.yview)
        self.cum_list = tk.Frame(self.cum_canvas, bg=self.colors["bg"])
        self.cum_list.bind("<Configure>", lambda e: self.cum_canvas.configure(scrollregion=self.cum_canvas.bbox("all")))
        self.cum_canvas.create_window((0, 0), window=self.cum_list, anchor="nw")
        self.cum_canvas.configure(yscrollcommand=sb.set)
        self.cum_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        ttk.Button(tab, text="导出累计 CSV", command=lambda: self._export_cumulative_csv()).pack(pady=5)

    def _build_chart_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text="  可视化  ")

        top_bar = ttk.Frame(tab)
        top_bar.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(top_bar, text="图表类型:").pack(side=tk.LEFT)
        self.chart_type = tk.StringVar(value="pie")
        ttk.Radiobutton(top_bar, text="饼图", variable=self.chart_type, value="pie",
                        command=self.refresh).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(top_bar, text="柱状图", variable=self.chart_type, value="bar",
                        command=self.refresh).pack(side=tk.LEFT, padx=5)
        ttk.Label(top_bar, text="  数据来源:").pack(side=tk.LEFT, padx=(15, 0))
        self.chart_source = tk.StringVar(value="today")
        ttk.Radiobutton(top_bar, text="今日", variable=self.chart_source, value="today",
                        command=self.refresh).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(top_bar, text="累计", variable=self.chart_source, value="cumulative",
                        command=self.refresh).pack(side=tk.LEFT, padx=5)

        self.chart_canvas = tk.Canvas(tab, bg=self.colors["card"], highlightthickness=0)
        self.chart_canvas.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

    def _build_trend_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text="  趋势  ")

        top = ttk.Frame(tab)
        top.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(top, text="程序1:").pack(side=tk.LEFT)
        self.trend_app_var = tk.StringVar()
        self.trend_combo = ttk.Combobox(top, textvariable=self.trend_app_var, width=20, state="readonly")
        self.trend_combo.pack(side=tk.LEFT, padx=5)
        self.trend_combo.bind("<<ComboboxSelected>>", lambda e: self._draw_trend())

        ttk.Label(top, text="对比:").pack(side=tk.LEFT, padx=(15, 0))
        self.trend_app2_var = tk.StringVar()
        self.trend_combo2 = ttk.Combobox(top, textvariable=self.trend_app2_var, width=20, state="readonly")
        self.trend_combo2.pack(side=tk.LEFT, padx=5)
        self.trend_combo2.bind("<<ComboboxSelected>>", lambda e: self._draw_trend())

        ttk.Label(top, text="天数:").pack(side=tk.LEFT, padx=(15, 0))
        self.trend_days_var = tk.IntVar(value=7)
        ttk.Spinbox(top, from_=3, to=30, textvariable=self.trend_days_var, width=4,
                    command=self._draw_trend).pack(side=tk.LEFT, padx=5)

        self.trend_canvas = tk.Canvas(tab, bg=self.colors["card"], highlightthickness=0)
        self.trend_canvas.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

    def _build_categories_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text="  分类&目标  ")

        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        left = ttk.LabelFrame(tab, text="程序分类", padding=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)

        ttk.Label(left, text="选择程序 → 设置分类").pack(anchor=tk.W)
        sel = ttk.Frame(left)
        sel.pack(fill=tk.X, pady=5)
        self.cat_app_var = tk.StringVar()
        self.cat_app_combo = ttk.Combobox(sel, textvariable=self.cat_app_var, width=18, state="readonly")
        self.cat_app_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.cat_val_var = tk.StringVar(value="未分类")
        cat_combo = ttk.Combobox(sel, textvariable=self.cat_val_var, width=10, state="readonly",
                                 values=["工作", "学习", "娱乐", "社交", "开发", "设计", "其他", "未分类"])
        cat_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(sel, text="设置", command=self._set_category).pack(side=tk.LEFT)

        self.cat_tree = ttk.Treeview(left, columns=("app", "cat"), show="headings", height=10)
        self.cat_tree.heading("app", text="程序")
        self.cat_tree.heading("cat", text="分类")
        self.cat_tree.column("app", width=140)
        self.cat_tree.column("cat", width=80)
        self.cat_tree.pack(fill=tk.BOTH, expand=True, pady=5)

        right = ttk.LabelFrame(tab, text="每日使用目标", padding=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)

        ttk.Label(right, text="设定每日最大使用时长，超出时提醒").pack(anchor=tk.W)

        goal_sel = ttk.Frame(right)
        goal_sel.pack(fill=tk.X, pady=5)
        self.goal_app_var = tk.StringVar()
        self.goal_app_combo = ttk.Combobox(goal_sel, textvariable=self.goal_app_var, width=16, state="readonly")
        self.goal_app_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.goal_min_var = tk.IntVar(value=60)
        ttk.Spinbox(goal_sel, from_=1, to=480, textvariable=self.goal_min_var, width=5).pack(side=tk.LEFT, padx=3)
        ttk.Label(goal_sel, text="分钟").pack(side=tk.LEFT)
        ttk.Button(goal_sel, text="设定", command=self._set_goal).pack(side=tk.LEFT, padx=5)
        ttk.Button(goal_sel, text="清除", command=self._clear_goal).pack(side=tk.LEFT)

        self.goal_tree = ttk.Treeview(right, columns=("app", "goal", "used", "status"), show="headings", height=10)
        self.goal_tree.heading("app", text="程序")
        self.goal_tree.heading("goal", text="目标")
        self.goal_tree.heading("used", text="已用")
        self.goal_tree.heading("status", text="状态")
        self.goal_tree.column("app", width=120)
        self.goal_tree.column("goal", width=60)
        self.goal_tree.column("used", width=60)
        self.goal_tree.column("status", width=60)
        self.goal_tree.pack(fill=tk.BOTH, expand=True, pady=5)

    def _build_history_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text="  历史  ")

        top = ttk.Frame(tab)
        top.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(top, text="选择日期:").pack(side=tk.LEFT)
        self.hist_date_var = tk.StringVar()
        self.hist_combo = ttk.Combobox(top, textvariable=self.hist_date_var, width=15, state="readonly")
        self.hist_combo.pack(side=tk.LEFT, padx=5)
        self.hist_combo.bind("<<ComboboxSelected>>", self._on_history_select)
        ttk.Button(top, text="刷新", command=self._refresh_history).pack(side=tk.LEFT, padx=5)

        self.hist_text = scrolledtext.ScrolledText(tab, font=("Consolas", 10), wrap=tk.WORD,
                                                   bg=self.colors["card"], fg=self.colors["fg"])
        self.hist_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self._refresh_history()

    def _build_settings_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text="  设置  ")

        f = ttk.Frame(tab, padding=20)
        f.pack(fill=tk.BOTH, expand=True)

        # 自启动
        r0 = ttk.Frame(f)
        r0.pack(fill=tk.X, pady=4)
        ttk.Label(r0, text="开机自启动", width=18, anchor=tk.W).pack(side=tk.LEFT)
        self.startup_var = tk.BooleanVar(value=is_startup_enabled())
        ttk.Checkbutton(r0, variable=self.startup_var, command=self._toggle_startup).pack(side=tk.LEFT)

        # ★ 状态标签
        self.startup_status_label = ttk.Label(r0, text="", foreground="gray")
        self.startup_status_label.pack(side=tk.LEFT, padx=8)

        # 空闲阈值
        r1 = ttk.Frame(f)
        r1.pack(fill=tk.X, pady=4)
        ttk.Label(r1, text="空闲阈值（秒）", width=18, anchor=tk.W).pack(side=tk.LEFT)
        self.idle_var = tk.IntVar(value=self.tracker.idle_threshold)
        ttk.Spinbox(r1, from_=30, to=600, textvariable=self.idle_var, width=6).pack(side=tk.LEFT)

        # 保存间隔
        r2 = ttk.Frame(f)
        r2.pack(fill=tk.X, pady=4)
        ttk.Label(r2, text="保存间隔（秒）", width=18, anchor=tk.W).pack(side=tk.LEFT)
        self.save_var = tk.IntVar(value=self.tracker.auto_save_interval)
        ttk.Spinbox(r2, from_=10, to=300, textvariable=self.save_var, width=6).pack(side=tk.LEFT)

        # 保留天数
        r3 = ttk.Frame(f)
        r3.pack(fill=tk.X, pady=4)
        ttk.Label(r3, text="数据保留天数", width=18, anchor=tk.W).pack(side=tk.LEFT)
        self.ret_var = tk.IntVar(value=self.tracker.retention_days)
        ttk.Spinbox(r3, from_=7, to=365, textvariable=self.ret_var, width=6).pack(side=tk.LEFT)
        ttk.Label(r3, text="（0=永不过期）", foreground=self.colors["text_secondary"]).pack(side=tk.LEFT, padx=5)

        # 提醒间隔
        r4 = ttk.Frame(f)
        r4.pack(fill=tk.X, pady=4)
        ttk.Label(r4, text="连续使用提醒（分钟）", width=18, anchor=tk.W).pack(side=tk.LEFT)
        self.rem_var = tk.IntVar(value=self.tracker.reminder_interval // 60)
        ttk.Spinbox(r4, from_=10, to=180, textvariable=self.rem_var, width=6).pack(side=tk.LEFT)
        ttk.Label(r4, text="（0=关闭提醒）", foreground=self.colors["text_secondary"]).pack(side=tk.LEFT, padx=5)

        # 忽略列表
        r5 = ttk.Frame(f)
        r5.pack(fill=tk.X, pady=4)
        ttk.Label(r5, text="忽略进程", width=18, anchor=tk.W).pack(side=tk.LEFT)
        self.ignore_var = tk.StringVar(value=", ".join(self.tracker.ignore_list))
        ttk.Entry(r5, textvariable=self.ignore_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 主题色
        r6 = ttk.Frame(f)
        r6.pack(fill=tk.X, pady=4)
        ttk.Label(r6, text="主题色", width=18, anchor=tk.W).pack(side=tk.LEFT)
        self.accent_var = tk.StringVar(value=self.tracker.accent_color)
        ACCENT_PRESETS = [
            "#0078d4", "#4CAF50", "#f59e0b", "#e91e63", "#9c27b0",
            "#00bcd4", "#ff5722", "#607d8b",
        ]
        self.accent_buttons = []
        for clr in ACCENT_PRESETS:
            btn = tk.Canvas(r6, width=22, height=22, highlightthickness=0, cursor="hand2")
            btn.pack(side=tk.LEFT, padx=2)
            btn.create_oval(2, 2, 20, 20, fill=clr, outline="#ccc" if not self.dark_mode.get() else "#555", width=1)
            btn.bind("<Button-1>", lambda e, c=clr: self._set_accent(c))
            self.accent_buttons.append((btn, clr))
        self.accent_color_label = ttk.Label(r6, text="", width=6)
        self.accent_color_label.pack(side=tk.LEFT, padx=6)

        ttk.Separator(f, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        ttk.Button(f, text="应用设置", command=self._apply_settings).pack()

        ttk.Separator(f, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        about = ttk.LabelFrame(f, text="关于", padding=10)
        about.pack(fill=tk.X)
        ttk.Label(about, text="程序使用时间追踪器 v1.0").pack(anchor=tk.W)
        ttk.Label(about, text=f"数据: {self.tracker.data_dir}",
                  foreground=self.colors["text_secondary"]).pack(anchor=tk.W)

        ttk.Separator(f, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        uninstall_frame = ttk.Frame(f)
        uninstall_frame.pack(fill=tk.X)
        uninstall_btn = tk.Button(uninstall_frame, text="卸载程序", command=self._uninstall,
                                  bg="#ef4444", fg="white", font=("Microsoft YaHei", 9),
                                  relief=tk.FLAT, padx=16, pady=4, cursor="hand2")
        uninstall_btn.pack(side=tk.LEFT)
        ttk.Label(uninstall_frame, text=" 删除注册表项及所有使用数据",
                  foreground=self.colors["text_secondary"]).pack(side=tk.LEFT, padx=8)

    # ════════════════════════════════════════
    # 深色模式
    # ════════════════════════════════════════

    def _set_accent(self, color):
        self.tracker.accent_color = color
        self.accent_var.set(color)
        self.accent_color_label.config(text="✓", foreground=color)
        self._apply_theme()

    def _toggle_dark_mode(self):
        self.dark_mode.set(not self.dark_mode.get())
        self.dark_btn.config(text="浅色模式" if self.dark_mode.get() else "深色模式")
        self._apply_theme()

    # ════════════════════════════════════════
    # 刷新 UI
    # ════════════════════════════════════════

    def refresh(self):
        self.root.after(0, self._refresh_ui)

    def _refresh_ui(self):
        c = self.colors
        total = self.tracker.get_total_seconds()
        self._draw_today_card(total)
        cum_total = self.tracker.get_cumulative_total()
        self.cum_total.config(text=f"累计总使用时间: {fmt_duration(cum_total)}", bg=c["bg"], fg=c["fg"])
        self.time_label.config(text=datetime.now().strftime('%H:%M:%S'))

        # ── 分类汇总条 ──
        for w in self.cat_frame.winfo_children():
            w.destroy()
        cat_stats = self.tracker.get_category_stats()
        total_cat = sum(cat_stats.values()) or 1
        cat_colors_map = {"工作": "#3b82f6", "学习": "#22c55e", "娱乐": "#f59e0b", "社交": "#8b5cf6",
                          "开发": "#06b6d4", "设计": "#ec4899", "其他": "#64748b", "未分类": "#94a3b8"}
        if not cat_stats:
            tk.Label(self.cat_frame, text="暂无分类数据", fg=c["text_secondary"],
                     bg=c["bg"]).pack(pady=4)
        for cat, sec in sorted(cat_stats.items(), key=lambda x: x[1], reverse=True):
            pct = sec / total_cat * 100
            color = cat_colors_map.get(cat, "#94a3b8")
            row = tk.Frame(self.cat_frame, bg=c["bg"], height=28)
            row.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
            can = tk.Canvas(row, height=26, highlightthickness=0, bg=c["bg"])
            can.pack(fill=tk.X, expand=True)
            # 延迟绘制等待布局完成
            can.after(10, lambda c=can, cl=color, p=pct, ct=cat: self._draw_cat_bar(c, cl, p, ct))

        # ── 今日列表 ──
        for w in self.list_frame.winfo_children():
            w.destroy()
        usage = self.tracker.get_sorted_usage()
        if not usage:
            tk.Label(self.list_frame, text="暂无数据，等待程序活动...", fg=c["text_secondary"],
                     bg=c["bg"]).pack(pady=30)
        else:
            for app, sec in usage:
                self._add_app_row(self.list_frame, app, sec, self.tracker.cumulative_usage.get(app, 0), total)

        # ── 累计列表 ──
        for w in self.cum_list.winfo_children():
            w.destroy()
        cum_usage = self.tracker.get_sorted_cumulative()
        if not cum_usage:
            tk.Label(self.cum_list, text="暂无累计数据...", fg=c["text_secondary"],
                     bg=c["bg"]).pack(pady=30)
        else:
            for app, sec in cum_usage:
                self._add_cum_row(self.cum_list, app, sec, cum_total)

        # ── 图表 ──
        self._draw_chart()

        # ── 趋势下拉 ──
        apps = [a for a, _ in self.tracker.get_sorted_cumulative()]
        self.trend_combo["values"] = apps
        self.trend_combo2["values"] = ["(无对比)"] + apps
        if apps and not self.trend_app_var.get():
            self.trend_app_var.set(apps[0])
        if not self.trend_app2_var.get():
            self.trend_app2_var.set("(无对比)")
        self._draw_trend()

        # ── 分类/目标下拉 ──
        self.cat_app_combo["values"] = apps
        self.goal_app_combo["values"] = apps
        self._refresh_cat_tree()
        self._refresh_goal_tree()

        # ★ 自启动状态更新
        if self.startup_status_label is not None:
            if self.startup_var.get():
                self.startup_status_label.config(text="✅ 已启用", foreground="green")
            else:
                self.startup_status_label.config(text="❌ 已禁用", foreground="gray")

        self.root.after(1000, self._refresh_time_only)

    def _refresh_time_only(self):
        c = self.colors
        self.time_label.config(text=datetime.now().strftime('%H:%M:%S'))
        self._tray_update_count += 1
        if self.tray_icon and self._tray_update_count % 30 == 0:
            total = fmt_duration(self.tracker.get_total_seconds())
            app = self.tracker.current_app or "空闲"
            self.tray_icon.title = f"今日 {total} | {app}"
        self.root.after(1000, self._refresh_time_only)

    def _add_app_row(self, parent, app, sec, cum, total):
        c = self.colors
        pct = (sec / total * 100) if total > 0 else 0
        cat = self.tracker.categories.get(app, "")
        cat_short = {"工作": "💼", "学习": "📚", "娱乐": "🎮", "社交": "💬", "开发": "💻", "设计": "🎨", "其他": "📌"}
        cat_icon = cat_short.get(cat, "")
        row = tk.Frame(parent, bg=c["bg"])
        row.pack(fill=tk.X, pady=1)
        tk.Label(row, text=self.tracker._localize_app(app), width=14, anchor=tk.W, bg=c["bg"], fg=c["fg"]).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(row, text=f"{cat_icon} {cat}" if cat else "", width=6, anchor=tk.W,
                 bg=c["bg"], fg=c["text_secondary"]).pack(side=tk.LEFT)
        tk.Label(row, text=fmt_duration(sec), width=8, anchor=tk.CENTER, bg=c["bg"], fg=c["fg"]).pack(side=tk.LEFT)
        tk.Label(row, text=fmt_duration(cum), width=8, anchor=tk.CENTER, bg=c["bg"],
                 fg=c["text_secondary"]).pack(side=tk.LEFT)
        tk.Label(row, text=f"{pct:.1f}%", width=5, anchor=tk.CENTER, bg=c["bg"], fg=c["fg"]).pack(side=tk.LEFT)
        bar = tk.Canvas(row, height=14, highlightthickness=0, bg=c["bar_bg"])
        bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        self.root.after(10, lambda b=bar, p=pct: self._draw_bar(b, p))

    def _add_cum_row(self, parent, app, sec, total):
        c = self.colors
        pct = (sec / total * 100) if total > 0 else 0
        cat = self.tracker.categories.get(app, "")
        row = tk.Frame(parent, bg=c["bg"])
        row.pack(fill=tk.X, pady=1)
        tk.Label(row, text=self.tracker._localize_app(app), width=18, anchor=tk.W, bg=c["bg"], fg=c["fg"]).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(row, text=f"[{cat}]" if cat else "", width=6, anchor=tk.W, bg=c["bg"],
                 fg=c["text_secondary"]).pack(side=tk.LEFT)
        tk.Label(row, text=fmt_duration(sec), width=12, anchor=tk.CENTER, bg=c["bg"], fg=c["fg"]).pack(side=tk.LEFT)
        tk.Label(row, text=f"{pct:.1f}%", width=5, anchor=tk.CENTER, bg=c["bg"], fg=c["fg"]).pack(side=tk.LEFT)
        bar = tk.Canvas(row, height=14, highlightthickness=0, bg=c["bar_bg"])
        bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        self.root.after(10, lambda b=bar, p=pct: self._draw_bar(b, p))

    def _draw_bar(self, canvas, pct):
        try:
            w = max(canvas.winfo_width(), 200)
        except Exception:
            return
        if w < 10:
            w = 200
        fill_w = max(int(w * pct / 100), 1)
        if pct > 30:
            color = "#4CAF50"
        elif pct > 10:
            color = "#FF9800"
        else:
            color = "#2196F3"
        try:
            canvas.delete("all")
            canvas.create_rectangle(0, 0, fill_w, 16, fill=color, outline="")
        except Exception:
            pass

    # ════════════════════════════════════════
    # 图表
    # ════════════════════════════════════════

    def _draw_chart(self):
        canvas = self.chart_canvas
        canvas.delete("all")
        c = self.colors

        if self.chart_source.get() == "today":
            data = self.tracker.today_usage
        else:
            data = self.tracker.cumulative_usage

        if not data:
            canvas.create_text(350, 150, text="暂无数据", fill=c["text_secondary"], font=("Microsoft YaHei", 14))
            return

        sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
        total = sum(v for _, v in sorted_data) or 1

        w = (lambda v: v if v > 50 else 700)(canvas.winfo_width())
        h = (lambda v: v if v > 50 else 350)(canvas.winfo_height())
        colors_palette = ["#2196F3", "#4CAF50", "#FF9800", "#9C27B0", "#00BCD4",
                          "#E91E63", "#FF5722", "#3F51B5", "#009688", "#795548"]

        if self.chart_type.get() == "pie":
            cx, cy, r = w // 2, h // 2, min(w, h) // 2 - 40
            angle = -90
            for i, (app, sec) in enumerate(sorted_data):
                extent = sec / total * 360
                color = colors_palette[i % len(colors_palette)]
                canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=angle, extent=extent,
                                  fill=color, outline=c["card"], width=2)
                mid_angle = math.radians(angle + extent / 2)
                lx = cx + (r * 0.7) * math.cos(mid_angle)
                ly = cy - (r * 0.7) * math.sin(mid_angle)
                pct = sec / total * 100
                if pct >= 4:
                    canvas.create_text(lx, ly, text=f"{pct:.0f}%", fill="white",
                                       font=("Microsoft YaHei", 9, "bold"))
                angle += extent
            # 图例：最多 10 项，两列布局防溢出
            legend_items = sorted_data[:10]
            col_w = 180
            cols = 1 if len(legend_items) <= 5 else 2
            base_y = max(h - 20 - (len(legend_items) + cols - 1) // cols * 20, 10)
            for i, (app, sec) in enumerate(legend_items):
                col = i // 5
                row = i % 5
                x = 10 + col * col_w
                y = base_y + row * 20
                color = colors_palette[i % len(colors_palette)]
                canvas.create_rectangle(x, y, x + 12, y + 12, fill=color, outline="")
                short_app = app[:16] + ".." if len(app) > 16 else app
                canvas.create_text(x + 16, y + 6, text=f"{short_app}", anchor=tk.W,
                                   fill=c["fg"], font=("Microsoft YaHei", 8))
            if len(sorted_data) > 10:
                canvas.create_text(10, h - 8, text=f"... 还有 {len(sorted_data) - 10} 项",
                                   fill=c["text_secondary"], anchor=tk.W, font=("Microsoft YaHei", 7))
        else:
            margin_l, margin_r, margin_t, margin_b = 80, 20, 30, 60
            chart_w = w - margin_l - margin_r
            chart_h = h - margin_t - margin_b
            max_val = sorted_data[0][1] if sorted_data else 1
            bar_w = min(chart_w / len(sorted_data) - 10, 60)

            for i, (app, sec) in enumerate(sorted_data):
                x = margin_l + i * (chart_w / len(sorted_data))
                bar_h = (sec / max_val) * chart_h
                y = margin_t + chart_h - bar_h
                color = colors_palette[i % len(colors_palette)]
                canvas.create_rectangle(x + 5, y, x + 5 + bar_w, margin_t + chart_h,
                                        fill=color, outline="")
                val_text = fmt_duration(sec)
                canvas.create_text(x + 5 + bar_w / 2, y - 10, text=val_text,
                                   fill=c["fg"], font=("Microsoft YaHei", 9), angle=0)
                short_app = app[:8] + ".." if len(app) > 8 else app
                canvas.create_text(x + 5 + bar_w / 2, margin_t + chart_h + 15, text=short_app,
                                   fill=c["fg"], font=("Microsoft YaHei", 8), angle=45, anchor=tk.W)

    # ════════════════════════════════════════
    # 趋势
    # ════════════════════════════════════════

    def _draw_trend(self):
        canvas = self.trend_canvas
        canvas.delete("all")
        c = self.colors
        app = self.trend_app_var.get()
        if not app:
            return
        days = self.trend_days_var.get()
        data1 = self.tracker.get_trend_data(app, days)
        if not data1:
            return

        app2 = self.trend_app2_var.get()
        data2 = None
        if app2 and app2 != "(无对比)":
            data2 = self.tracker.get_trend_data(app2, days)

        w = (lambda v: v if v > 50 else 700)(canvas.winfo_width())
        h = (lambda v: v if v > 50 else 300)(canvas.winfo_height())
        ml, mr, mt, mb = 60, 20, 30, 50
        cw, ch = w - ml - mr, h - mt - mb

        max_val = max(s for _, s in data1) or 1
        if data2:
            max_val = max(max_val, max(s for _, s in data2)) or 1
        if max_val == 0:
            max_val = 1

        for i in range(5):
            y = mt + ch * (1 - i / 4)
            canvas.create_line(ml, y, ml + cw, y, fill=c["bar_bg"], dash=(2, 4))
            canvas.create_text(ml - 5, y, text=fmt_duration(max_val * i / 4), anchor=tk.E,
                               fill=c["text_secondary"], font=("Microsoft YaHei", 7))

        def draw_line(data, color, label):
            points = []
            for i, (date_str, sec) in enumerate(data):
                x = ml + (i + 0.5) * (cw / len(data))
                y = mt + ch * (1 - sec / max_val)
                points.extend([x, y])
            if len(points) >= 4:
                canvas.create_line(*points, fill=color, width=2, smooth=True)
            for i, (date_str, sec) in enumerate(data):
                x = ml + (i + 0.5) * (cw / len(data))
                y = mt + ch * (1 - sec / max_val)
                r = 4
                canvas.create_oval(x - r, y - r, x + r, y + r, fill=color, outline=c["card"], width=2)
                canvas.create_text(x, y - 12, text=fmt_duration(sec), fill=c["fg"],
                                   font=("Microsoft YaHei", 8, "bold"))
                short_date = date_str[-5:]
                canvas.create_text(x, mt + ch + 15, text=short_date, fill=c["text_secondary"],
                                   font=("Microsoft YaHei", 7))
            return points

        draw_line(data1, c["accent"], app)
        if data2:
            draw_line(data2, "#FF9800", app2)

        title = f"{app} 最近{days}天趋势"
        if data2:
            title += f"  vs  {app2}"
            canvas.create_text(ml + 10, mt + 5, text=f"── {app}", fill=c["accent"],
                               font=("Microsoft YaHei", 8), anchor=tk.W)
            canvas.create_text(ml + 10, mt + 22, text=f"── {app2}", fill="#FF9800",
                               font=("Microsoft YaHei", 8), anchor=tk.W)
        canvas.create_text(w // 2, h - 5, text=title, fill=c["text_secondary"],
                           font=("Microsoft YaHei", 8))

    # ════════════════════════════════════════
    # 分类 & 目标
    # ════════════════════════════════════════

    def _set_category(self):
        app = self.cat_app_var.get()
        cat = self.cat_val_var.get()
        if app:
            with self.tracker.data_lock:
                self.tracker.categories[app] = cat
            self.tracker.save_categories()
            self._refresh_cat_tree()
            self.refresh()

    def _refresh_cat_tree(self):
        for row in self.cat_tree.get_children():
            self.cat_tree.delete(row)
        for app, cat in sorted(self.tracker.categories.items()):
            self.cat_tree.insert("", tk.END, values=(app, cat))

    def _set_goal(self):
        app = self.goal_app_var.get()
        minutes = self.goal_min_var.get()
        if app and minutes > 0:
            with self.tracker.data_lock:
                self.tracker.goals[app] = minutes * 60
            self.tracker.save_goals()
            self._refresh_goal_tree()

    def _clear_goal(self):
        app = self.goal_app_var.get()
        if app and app in self.tracker.goals:
            with self.tracker.data_lock:
                if app in self.tracker.goals:
                    del self.tracker.goals[app]
            self.tracker.save_goals()
            self._refresh_goal_tree()

    def _refresh_goal_tree(self):
        for row in self.goal_tree.get_children():
            self.goal_tree.delete(row)
        for app, goal_sec in sorted(self.tracker.goals.items()):
            used = self.tracker.today_usage.get(app, 0)
            status = "⚠ 超标" if used > goal_sec else "✓ 正常"
            self.goal_tree.insert("", tk.END, values=(app, fmt_duration(goal_sec), fmt_duration(used), status))

    # ════════════════════════════════════════
    # 提醒
    # ════════════════════════════════════════

    def _on_reminder(self, app, elapsed):
        msg = f"⏰ 提醒：你已连续使用 {app} 超过 {fmt_duration(elapsed)}，建议休息一下！"
        self.root.after(0, lambda: self._show_reminder(app, msg))

    def _show_reminder(self, app, msg):
        exceeded = self.tracker.check_goals()
        for ex_app, used, goal in exceeded:
            if ex_app == app:
                msg += f"\n\n⚠ 今日目标: {fmt_duration(goal)}, 已使用: {fmt_duration(used)} (超标!)"
                break

        self.root.after(0, lambda m=msg: messagebox.showwarning("休息提醒", m))

    # ════════════════════════════════════════
    # 历史
    # ════════════════════════════════════════

    def _refresh_history(self):
        dates = self.tracker.get_all_available_dates()
        self.hist_combo["values"] = dates
        if dates:
            self.hist_date_var.set(dates[-1])
            self._on_history_select()

    def _on_history_select(self, event=None):
        date = self.hist_date_var.get()
        if not date:
            return
        report_file = self.tracker.data_dir / date / "报告.txt"
        if report_file.exists():
            text = report_file.read_text(encoding="utf-8")
        else:
            text = "该日期无记录。"
        self.hist_text.delete("1.0", tk.END)
        self.hist_text.insert("1.0", text)

    # ════════════════════════════════════════
    # 设置 & 自启动
    # ════════════════════════════════════════

    def _apply_settings(self):
        self.tracker.idle_threshold = self.idle_var.get()
        self.tracker.auto_save_interval = self.save_var.get()
        self.tracker.retention_days = self.ret_var.get()
        self.tracker.reminder_interval = self.rem_var.get() * 60
        self.tracker.ignore_list = [s.strip() for s in self.ignore_var.get().split(",") if s.strip()]
        self.tracker._save_settings()
        self.tracker._cleanup_old_files()
        messagebox.showinfo("设置", "✅ 设置已应用！")

    def _toggle_startup(self):
        if self.startup_var.get():
            ok, err = add_to_startup()
            if ok:
                if self.startup_status_label is not None:
                    self.startup_status_label.config(text="✅ 已启用", foreground="green")
            else:
                messagebox.showerror("错误", f"添加失败:\n{err}")
                self.startup_var.set(False)
        else:
            ok, err = remove_from_startup()
            if self.startup_status_label is not None:
                self.startup_status_label.config(text="❌ 已禁用", foreground="gray")

    # ════════════════════════════════════════
    # 导出
    # ════════════════════════════════════════

    def _export_pdf(self):
        try:
            path = self.tracker.export_pdf()
            messagebox.showinfo("导出成功", f"✅ PDF 已导出到:\n{path}")
        except Exception as e:
            messagebox.showerror("导出失败", f"PDF 导出错误:\n{e}")

    def _export_csv(self):
        path = self.tracker.export_csv()
        messagebox.showinfo("导出成功", f"✅ 已导出到:\n{path}")

    def _export_cumulative_csv(self):
        path = self.tracker.export_cumulative_csv()
        messagebox.showinfo("导出成功", f"✅ 已导出到:\n{path}")

    # ════════════════════════════════════════
    # 托盘
    # ════════════════════════════════════════

    def _init_tray(self):
        try:
            import pystray
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (64, 64), color=(52, 152, 219))
            d = ImageDraw.Draw(img)
            d.rectangle([12, 12, 52, 52], fill="white")
            d.text((18, 16), "⏱", fill=(52, 152, 219))
            menu = pystray.Menu(
                pystray.MenuItem("显示窗口", self._show_window, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", self._tray_exit),
            )
            self._tray_title = "程序使用时间追踪"
            self.tray_icon = pystray.Icon("AppTimer", img, self._tray_title, menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except ImportError:
            self.tray_icon = None
        self._tray_update_count = 0

    def _show_window(self, icon=None, item=None):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _minimize_to_tray(self):
        if self.tray_icon:
            self.root.withdraw()
        else:
            self.root.iconify()

    def _tray_exit(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        self._do_exit()

    def _uninstall(self):
        data_dir = str(self.tracker.data_dir)
        script_path = os.path.abspath(sys.argv[0])
        msg = (
            "⚠ 确认卸载\n\n"
            "此操作将：\n"
            "  1. 移除开机自启动项\n"
            "  2. 删除所有使用记录数据\n"
            f"\n数据目录: {data_dir}"
            f"\n\n程序文件 ({script_path}) 不会被删除，请手动处理。"
        )
        if not messagebox.askyesno("确认卸载", msg, icon="warning"):
            return

        # 清理注册表
        remove_from_startup()

        # 删除数据目录
        import shutil
        data_path = self.tracker.data_dir
        if data_path.exists():
            try:
                shutil.rmtree(data_path)
            except Exception as e:
                messagebox.showwarning("提示", f"数据目录删除失败: {e}\n请手动删除: {data_dir}")

        messagebox.showinfo("卸载完成", "程序已清理完毕，即将退出。\n\n请手动删除程序文件。")
        self._do_exit()

    def _open_folder(self):
        os.startfile(str(self.tracker.data_dir))

    def _on_close(self):
        if self.tray_icon:
            self._minimize_to_tray()
        else:
            self._do_exit()

    def _do_exit(self):
        self.tracker.close()
        self.root.destroy()
        sys.exit(0)

    def run(self):
        def loop():
            while self.tracker.running:
                try:
                    self.tracker.update()
                    self.tracker._consecutive_errors = 0
                    time.sleep(2)
                except Exception as e:
                    self.tracker._consecutive_errors += 1
                    backoff = min(2 ** self.tracker._consecutive_errors, 60)
                    logging.error(f"追踪错误 (连续{self.tracker._consecutive_errors}次, 等待{backoff}s): {e}")
                    time.sleep(backoff)
        threading.Thread(target=loop, daemon=True).start()
        self.root.mainloop()


# ============================================================
# 入口
# ============================================================

def main():
    if "--install" in sys.argv:
        ok, err = add_to_startup()
        func = messagebox.showinfo if ok else messagebox.showerror
        func("结果", f"{'✅ 已添加' if ok else '❌ 失败: ' + err}")
        return

    if "--uninstall" in sys.argv:
        ok, err = remove_from_startup()
        func = messagebox.showinfo if ok else messagebox.showerror
        func("结果", f"{'✅ 已移除' if ok else '❌ 失败: ' + err}")
        return

    if "--report" in sys.argv:
        t = UsageTracker()
        print(t._build_report())
        return

    if "--open" in sys.argv:
        os.startfile(str(Path(get_desktop_path()) / UsageTracker.DATA_FOLDER_NAME))
        return

    silent = "--silent" in sys.argv
    AppTimerUI(silent=silent).run()


if __name__ == "__main__":
    main()
