"""一条命令跑全部自测：py -3.14 v3/tools/run_tests.py

每个 selftest_*.py 在独立子进程里跑（互不污染），失败退出码非零。
"""
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
PY = sys.executable


def main():
    scripts = sorted(HERE.glob("selftest_*.py"))
    if not scripts:
        print("没有找到自测脚本")
        return 1
    failed = []
    total = time.monotonic()
    for script in scripts:
        start = time.monotonic()
        proc = subprocess.run([PY, str(script)], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", cwd=str(HERE.parent.parent))
        took = time.monotonic() - start
        name = script.stem
        if proc.returncode == 0:
            print("[ OK ] %-22s %5.1fs" % (name, took))
        else:
            failed.append((name, proc))
            print("[FAIL] %-22s %5.1fs" % (name, took))
    if failed:
        print("\n失败详情：")
        for name, proc in failed:
            print("=" * 60)
            print(name)
            print("-" * 60)
            print((proc.stdout or "").strip()[-1500:])
            if proc.stderr:
                print("[stderr]", proc.stderr.strip()[-800:])
    print("\n%d/%d 通过，用时 %.1fs" % (len(scripts) - len(failed), len(scripts),
                                        time.monotonic() - total))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
