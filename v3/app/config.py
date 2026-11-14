r"""v3 自己的配置：只记录「位置」，数据固定放在该位置下的 程序使用记录\。"""
import json
import os
from pathlib import Path

APP_DIR = "AppTimer"
FILE_NAME = "v3-settings.json"
DATA_SUBDIR = "程序使用记录"

last_error = ""


def config_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    d = Path(base) / APP_DIR
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return d


def default_location():
    r"""默认位置：%LOCALAPPDATA%\AppTimer，数据落在其下的 程序使用记录\。"""
    return config_dir()


def config_path():
    return config_dir() / FILE_NAME


def _fallback_path():
    """主路径不可写时的备用位置（与主路径同盘、固定、不依赖配置本身）。"""
    return config_dir() / DATA_SUBDIR / FILE_NAME


def _data_path():
    r"""把配置放在数据目录里——打包版对 %LOCALAPPDATA%\AppTimer 可能无写权限，
    但数据目录（数据库就在那儿）一定是可写的。直接从主文件里读 location，避免递归。"""
    data = _read(config_path()) or {}
    loc = data.get("location")
    base = Path(loc) if isinstance(loc, str) and loc.strip() else default_location()
    return Path(base) / DATA_SUBDIR / FILE_NAME


def _candidates():
    primary = config_path()
    out = [primary]
    try:
        alt = _data_path()
    except Exception:
        alt = None
    if alt and alt != primary:
        out.append(alt)
    fb = _fallback_path()
    if fb not in out:
        out.append(fb)
    return out


def _read(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


_target = None


def active_path():
    """唯一生效的配置文件：第一个真能写的候选（打包版主路径只读时会落到数据目录）。

    只认一份，避免"读 A 写 B"导致设置看起来不生效。
    """
    global _target
    if _target is not None:
        return _target
    for path in _candidates():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            probe = path.with_suffix(".probe")
            probe.write_text("x", encoding="utf-8")
            probe.unlink()
            _target = path
            return _target
        except OSError:
            continue
    _target = config_path()
    return _target


def _seed_if_empty(target):
    """目标文件还没有内容时，从其它候选里挑最新的一份搬过去。"""
    existing = []
    for path in _candidates():
        if path == target:
            continue
        try:
            existing.append((path.stat().st_mtime, path))
        except OSError:
            continue
    for _mtime, path in sorted(existing, reverse=True):
        data = _read(path)
        if data is not None and save(data):
            return data
    return None


def load():
    target = active_path()
    data = _read(target)
    if data is not None:
        return data
    seeded = _seed_if_empty(target)
    return seeded if seeded is not None else {}


def save(cfg):
    """按候选顺序写：主路径 → 数据目录 → 备用；全都失败才返回 False。"""
    global last_error
    errors = []
    for path in [active_path()] + [p for p in _candidates() if p != active_path()]:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
            if path != active_path():
                global _target
                _target = path
            last_error = ""
            return True
        except OSError as exc:
            errors.append("%s: %s" % (path, exc))
    last_error = " ; ".join(errors)
    return False


def get_location():
    value = load().get("location")
    if isinstance(value, str) and value.strip():
        return Path(value)
    return default_location()


def set_location(path):
    cfg = load()
    if path:
        cfg["location"] = str(path)
    else:
        cfg.pop("location", None)
    return save(cfg)


def is_custom():
    return bool(load().get("location"))


def data_dir(location=None):
    return Path(location or get_location()) / DATA_SUBDIR


def ensure_data_dir(location=None):
    path = data_dir(location)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        global last_error
        last_error = "%s: %s" % (path, exc)
    return path


def _int_value(key, default=0):
    try:
        return max(0, int(load().get(key) or default))
    except (TypeError, ValueError):
        return default


def get_goal():
    """每日目标秒数；0 表示未设定。"""
    return _int_value("daily_goal")


def set_goal(seconds):
    cfg = load()
    seconds = max(0, int(seconds or 0))
    if seconds:
        cfg["daily_goal"] = seconds
    else:
        cfg.pop("daily_goal", None)
    return save(cfg)


def goal_enabled():
    """每日目标是否启用（未设定目标时视为关闭）。"""
    return get_goal() > 0 and bool(load().get("goal_enabled", True))


def set_goal_enabled(on):
    cfg = load()
    cfg["goal_enabled"] = bool(on)
    return save(cfg)


def toggle_goal_enabled():
    return set_goal_enabled(not goal_enabled())


def get_theme():
    value = load().get("theme")
    return "light" if value == "light" else "dark"


def set_theme(mode):
    cfg = load()
    cfg["theme"] = "light" if mode == "light" else "dark"
    return save(cfg)


def get_brand():
    """自定义主题色 (r,g,b)；None 表示跟随模式（深色底白、亮色底黑）。"""
    value = load().get("brand")
    if isinstance(value, (list, tuple)) and len(value) == 3:
        try:
            return tuple(max(0, min(255, int(c))) for c in value)
        except (TypeError, ValueError):
            return None
    return None


def set_brand(rgb):
    cfg = load()
    if rgb:
        cfg["brand"] = [int(rgb[0]), int(rgb[1]), int(rgb[2])]
    else:
        cfg.pop("brand", None)
    return save(cfg)


def get_idle_threshold():
    """空闲多少秒后停止计时（v2 同名设置，默认 120）。"""
    return max(10, _int_value("idle_threshold", 120))


def set_idle_threshold(seconds):
    cfg = load()
    cfg["idle_threshold"] = max(10, int(seconds or 120))
    return save(cfg)


def get_save_interval():
    """采集器多少秒落一次库（默认 5）。"""
    return max(1, _int_value("save_interval", 5))


def set_save_interval(seconds):
    cfg = load()
    cfg["save_interval"] = max(1, int(seconds or 5))
    return save(cfg)


def get_retention_days():
    """数据保留天数，0 = 永久保留。"""
    return _int_value("retention_days", 0)


def set_retention_days(days):
    cfg = load()
    days = max(0, int(days or 0))
    if days:
        cfg["retention_days"] = days
    else:
        cfg.pop("retention_days", None)
    return save(cfg)


def get_remind():
    return bool(load().get("goal_remind", True))


def set_remind(on):
    cfg = load()
    cfg["goal_remind"] = bool(on)
    return save(cfg)


def get_goal_alert_date():
    value = load().get("goal_alert_date")
    return value if isinstance(value, str) else ""


def set_goal_alert_date(date_str):
    cfg = load()
    if date_str:
        cfg["goal_alert_date"] = date_str
    else:
        cfg.pop("goal_alert_date", None)
    return save(cfg)


def get_pomodoro():
    """(专注秒, 休息秒, 长休息秒, 专注结束提醒, 休息结束提醒)"""
    cfg = load()
    def _m(key, default_min):
        try:
            return max(1, int(cfg.get(key) or default_min)) * 60
        except (TypeError, ValueError):
            return default_min * 60
    return (_m("pomo_work", 25), _m("pomo_break", 5), _m("pomo_long", 15),
            bool(cfg.get("pomo_notify_work", True)), bool(cfg.get("pomo_notify_break", True)))


def set_pomodoro(work_min=None, break_min=None, long_min=None):
    cfg = load()
    for key, value in (("pomo_work", work_min), ("pomo_break", break_min),
                       ("pomo_long", long_min)):
        if value is None:
            continue
        if value > 0:
            cfg[key] = int(value)
        else:
            cfg.pop(key, None)
    return save(cfg)


def set_pomo_notify(kind, on):
    """kind: 'work' 专注结束 / 'break' 休息结束。"""
    cfg = load()
    cfg["pomo_notify_%s" % kind] = bool(on)
    return save(cfg)


def get_previous_data_dir():
    value = load().get("previous_data_dir")
    return Path(value) if isinstance(value, str) and value.strip() else None


def set_previous_data_dir(path):
    cfg = load()
    if path:
        cfg["previous_data_dir"] = str(path)
    else:
        cfg.pop("previous_data_dir", None)
    return save(cfg)