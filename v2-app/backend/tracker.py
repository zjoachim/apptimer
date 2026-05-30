"""生命周期纯数据追踪器：不依赖任何 UI 框架"""

import csv
import json
import logging
import os
import threading
import time
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

from .window_detect import get_active_window_process_name, get_active_window_title, get_idle_seconds, get_exe_version_field, get_desktop_path


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


class UsageTracker:
    DATA_FOLDER_NAME = "程序使用记录"

    def __init__(self, data_dir=None):
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
        self.app_start_time = datetime.now()
        self.today_usage = {}
        self.cumulative_usage = {}
        self.session_log = []
        self.last_save_time = datetime.now()

        self.idle_threshold = 120
        self.auto_save_interval = 30
        self.retention_days = 60
        self.reminder_interval = 45 * 60
        self.goals = {}
        self.categories = {}
        self.running = True
        self._dirty = False
        self._consecutive_errors = 0
        self.data_lock = threading.Lock()
        self._last_reminder = {}
        self._desc_cache = {}

        self.ignore_list = [
            "", "explorer.exe", "searchhost.exe",
            "shellexperiencehost.exe", "systemsettings.exe",
            "textinputhost.exe", "applicationframehost.exe",
            "python.exe", "pythonw.exe", "py.exe",
            "cmd.exe", "powershell.exe",
        ]

        self._setup_logging()
        self._load_all()
        self._cleanup_old_files()

    def _setup_logging(self):
        logger = logging.getLogger()
        for h in logger.handlers[:]:
            h.close()
            logger.removeHandler(h)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.FileHandler(self.today_folder / "日志.log", encoding="utf-8")]
        )
        logging.info(f"追踪器已启动 v2.0 → {self.data_dir}")

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

    def save_settings(self, settings_dict):
        self.idle_threshold = settings_dict.get("idle_threshold", self.idle_threshold)
        self.auto_save_interval = settings_dict.get("auto_save_interval", self.auto_save_interval)
        self.retention_days = settings_dict.get("retention_days", self.retention_days)
        self.reminder_interval = settings_dict.get("reminder_interval", self.reminder_interval)
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump({
                "idle_threshold": self.idle_threshold,
                "auto_save_interval": self.auto_save_interval,
                "retention_days": self.retention_days,
                "reminder_interval": self.reminder_interval,
            }, f, ensure_ascii=False, indent=2)

    def save_categories(self, categories_dict):
        with self.data_lock:
            self.categories = dict(categories_dict)
        with open(self.categories_file, "w", encoding="utf-8") as f:
            json.dump({"categories": self.categories}, f, ensure_ascii=False, indent=2)

    def save_goals(self, goals_dict):
        with self.data_lock:
            self.goals = dict(goals_dict)
        with open(self.goals_file, "w", encoding="utf-8") as f:
            json.dump({"goals": self.goals}, f, ensure_ascii=False, indent=2)

    def _cleanup_old_files(self):
        if self.retention_days <= 0:
            return
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        for item in self.data_dir.iterdir():
            if item.is_dir() and item.name != self.today_str:
                try:
                    date = datetime.strptime(item.name, "%Y-%m-%d")
                    if date < cutoff:
                        shutil.rmtree(item)
                        logging.info(f"清理过期数据: {item.name}")
                except ValueError:
                    pass

    def _close_current_session(self, now):
        if self.current_app:
            duration = (now - self.app_start_time).total_seconds()
            if duration >= 1.0:
                with self.data_lock:
                    self.today_usage[self.current_app] = self.today_usage.get(self.current_app, 0) + duration
                    self.cumulative_usage[self.current_app] = self.cumulative_usage.get(self.current_app, 0) + duration
                    self.session_log.append({
                        "app": self.current_app,
                        "window": getattr(self, "current_window", ""),
                        "start": self.app_start_time.isoformat(),
                        "end": now.isoformat(),
                        "duration_seconds": round(duration, 1),
                    })
                    self._dirty = True
        self.current_app = ""
        self.app_start_time = now

    SITE_RULES = [
        (["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"], [
            ("GitHub", "开发"), ("github", "开发"), ("GitLab", "开发"),
            ("Stack Overflow", "开发"), ("YouTube", "娱乐"), ("youtube", "娱乐"),
            ("Bilibili", "娱乐"), ("bilibili", "娱乐"), ("Netflix", "娱乐"),
            ("iqiyi", "娱乐"), ("斗鱼", "娱乐"), ("虎牙", "娱乐"),
            ("Google Docs", "工作"), ("Notion", "工作"), ("飞书", "工作"),
            ("钉钉", "工作"), ("微信", "社交"), ("WeChat", "社交"),
            ("知乎", "社交"), ("微博", "社交"), ("Twitter", "社交"),
            ("Reddit", "社交"), ("百度", "搜索"), ("Google", "搜索"),
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

    def update(self):
        if not self.running:
            return
        now = datetime.now()

        # 日期切换
        new_today = now.strftime("%Y-%m-%d")
        if new_today != self.today_str:
            self._close_current_session(now)
            self._save_data()
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
            self._setup_logging()

        # 空闲检测
        if get_idle_seconds() > self.idle_threshold:
            self._close_current_session(now)
            if self._dirty:
                self._save_data()
                self.last_save_time = now
            return

        process_name, exe_path = get_active_window_process_name()
        if exe_path and process_name and process_name not in self._desc_cache:
            desc = get_exe_version_field(exe_path, "FileDescription")
            self._desc_cache[process_name] = desc if desc else process_name
        self.current_window = get_active_window_title()

        if process_name in self.ignore_list or process_name.startswith("windows"):
            self._close_current_session(now)
            return

        app_id = self._classify_window(process_name, self.current_window) if process_name else "unknown"

        if app_id != self.current_app:
            self._close_current_session(now)
            self.current_app = app_id
            self.app_start_time = now
            if app_id not in self._last_reminder:
                self._last_reminder[app_id] = now

        if self._dirty and (now - self.last_save_time).total_seconds() >= self.auto_save_interval:
            self._save_data()
            self.last_save_time = now

    def get_snapshot(self):
        """供前端调用的数据快照"""
        with self.data_lock:
            return {
                "today_str": self.today_str,
                "total_seconds": sum(self.today_usage.values()),
                "total_cumulative": sum(self.cumulative_usage.values()),
                "today_usage": dict(sorted(self.today_usage.items(), key=lambda x: x[1], reverse=True)),
                "cumulative_usage": dict(sorted(self.cumulative_usage.items(), key=lambda x: x[1], reverse=True)),
                "categories": dict(self.categories),
                "goals": dict(self.goals),
                "current_app": self.current_app,
                "session_count": len(self.session_log),
                "desc_cache": dict(self._desc_cache),
            }

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
                            sec = json.load(f).get("usage", {}).get(app, 0)
                    except Exception:
                        pass
            trend.append((date_str, sec))
        return trend

    def get_all_dates(self):
        dates = []
        for item in sorted(self.data_dir.iterdir()):
            if item.is_dir():
                try:
                    datetime.strptime(item.name, "%Y-%m-%d")
                    dates.append(item.name)
                except ValueError:
                    pass
        return dates

    def get_history_report(self, date_str):
        report_file = self.data_dir / date_str / "报告.txt"
        if report_file.exists():
            return report_file.read_text(encoding="utf-8")
        return "该日期无记录。"

    def get_category_stats(self):
        cat_stats = defaultdict(float)
        with self.data_lock:
            for app, sec in self.today_usage.items():
                cat = self.categories.get(app, "未分类")
                cat_stats[cat] += sec
        return dict(cat_stats)

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
            logging.warning("微软雅黑字体未找到，PDF 将使用默认字体")
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

    def close(self):
        self.running = False
        self._close_current_session(datetime.now())
        with self.data_lock:
            self._dirty = True
        self._save_data()
        logging.info("追踪器已关闭 v2.0")
