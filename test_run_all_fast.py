"""
test_run_all_fast.py — Runs the full A1→A2→A3 pipeline without video watch time.

Sets NO_WATCH=True so _variable_video_behavior is skipped entirely.
Uses real cookies and posts real comments unless DRY_RUN=True (default).

Usage:
    python test_run_all_fast.py              # dry run (no real posts)
    DRY_RUN=False python test_run_all_fast.py  # real posts, no watch time
"""

import os
import sys
import subprocess
import threading
import time
from datetime import datetime

_HERE  = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable

# ── env flags passed to all subprocesses ──────────────────────────────────────
_ENV = os.environ.copy()
_ENV["PYTHONUNBUFFERED"] = "1"
_ENV["PYTHONIOENCODING"] = "utf-8"
_ENV["SKIP_DELAYS"]      = "True"   # no time.sleep delays
_ENV["NO_WATCH"]         = "True"   # skip _variable_video_behavior
_ENV["DRY_RUN"]          = _ENV.get("DRY_RUN", "True")

BOTS = [
    ("A3", "main_account3.py"),
]


def _stream(proc: subprocess.Popen, label: str) -> None:
    try:
        for line in proc.stdout:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{label}] {ts}  {line.rstrip()}", flush=True)
    except Exception:
        pass


def main():
    print(f"[LAUNCHER] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  "
          f"Fast test — DRY_RUN={_ENV['DRY_RUN']} | NO_WATCH=True | SKIP_DELAYS=True")
    print("[LAUNCHER] Press Ctrl+C to stop early\n")

    procs = []
    threads = []

    for label, script in BOTS:
        proc = subprocess.Popen(
            [PYTHON, "-u", os.path.join(_HERE, script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=_ENV,
        )
        t = threading.Thread(target=_stream, args=(proc, label), daemon=True)
        t.start()
        procs.append((label, proc))
        threads.append(t)
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[LAUNCHER] {script} started (PID {proc.pid})")
        time.sleep(3)   # stagger starts slightly

    try:
        while any(p.poll() is None for _, p in procs):
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[LAUNCHER] Ctrl+C received — stopping all bots...")
        for _, p in procs:
            try:
                p.terminate()
            except Exception:
                pass

    for t in threads:
        t.join(timeout=5)

    print("\n[LAUNCHER] All bots stopped.")
    codes = {label: p.returncode for label, p in procs}
    for label, code in codes.items():
        status = "OK" if code in (0, None) else f"EXIT {code}"
        print(f"  [{label}] {status}")


if __name__ == "__main__":
    main()
