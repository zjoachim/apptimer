"""数据目录迁移：只搬 AppTimer 自己的文件，复制 + 逐文件校验，源目录保留。"""
import re
import shutil
from pathlib import Path

DAY_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATA_FILES = {"数据.json", "累计数据.json", "分类标签.json", "使用目标.json", "设置.json",
              "v3.db", "v3.db-wal", "v3.db-shm"}


def is_data_entry(path):
    """只认 AppTimer 自己的目录/文件，目录里其它东西一律不碰。"""
    path = Path(path)
    if path.is_dir():
        return bool(DAY_DIR.match(path.name))
    name = path.name
    return (name in DATA_FILES
            or name.startswith("周报_")
            or name.startswith("累计导出_")
            or name.endswith(".json.bak"))


def entries(root):
    root = Path(root)
    if not root.is_dir():
        return []
    try:
        return [p for p in root.iterdir() if is_data_entry(p)]
    except OSError:
        return []


def snapshot(root):
    """相对路径 -> 文件大小，只统计 AppTimer 自己的条目。"""
    root = Path(root)
    out = {}
    for item in entries(root):
        if item.is_dir():
            for p in item.rglob("*"):
                if p.is_file():
                    out[p.relative_to(root).as_posix()] = p.stat().st_size
        else:
            out[item.relative_to(root).as_posix()] = item.stat().st_size
    return out


def stats(root):
    snap = snapshot(root)
    return len(snap), sum(snap.values())


def purge(root):
    """只删除 root 里 AppTimer 自己的条目，返回 (条目数, 释放字节数, 目录是否已删除)。

    目录里还有别的文件时保留目录本身。
    """
    root = Path(root)
    removed = freed = 0
    for item in entries(root):
        try:
            if item.is_dir():
                size = sum(p.stat().st_size for p in item.rglob("*") if p.is_file())
                shutil.rmtree(item)
            else:
                size = item.stat().st_size
                item.unlink()
            removed += 1
            freed += size
        except OSError:
            continue

    dir_removed = False
    if root.is_dir():
        try:
            empty = not any(root.iterdir())
        except OSError:
            empty = False
        if empty:
            try:
                root.rmdir()
                dir_removed = True
            except OSError:
                dir_removed = False
    return removed, freed, dir_removed


def _inside(child, parent):
    try:
        Path(child).resolve().relative_to(Path(parent).resolve())
        return True
    except ValueError:
        return False


def migrate(src, dst):
    """把 src 下 AppTimer 自己的数据复制到 dst 并校验。返回 {'ok','files','bytes','error'}。"""
    src, dst = Path(src), Path(dst)
    if not src.is_dir():
        return {"ok": False, "error": "源目录不存在：%s" % src}
    if src.resolve() == dst.resolve():
        return {"ok": False, "error": "目标与当前是同一个目录"}
    if _inside(dst, src) or _inside(src, dst):
        return {"ok": False, "error": "目标目录不能与当前目录互相嵌套"}
    moves = entries(src)
    if not moves:
        return {"ok": False, "error": "源目录里没有 AppTimer 数据"}
    try:
        dst.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return {"ok": False, "error": "无法创建目标目录：%s" % exc}
    if any(dst.iterdir()):
        return {"ok": False, "error": "目标目录不是空目录，请换一个空文件夹"}

    try:
        for item in moves:
            target = dst / item.name
            if item.is_dir():
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)
    except (OSError, shutil.Error) as exc:
        return {"ok": False, "error": "复制失败：%s" % exc}

    before, after = snapshot(src), snapshot(dst)
    missing = [k for k, v in before.items() if after.get(k) != v]
    if missing:
        return {"ok": False, "error": "校验失败，%d 个文件不一致（首个：%s）" % (len(missing), missing[0])}

    return {"ok": True, "files": len(after), "bytes": sum(after.values()), "error": ""}
