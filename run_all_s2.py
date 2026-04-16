"""
run_all_s2.py — Strategy 2 launcher (2-account escalation thread).

Account 1 drops a surface-level observation and exits.
Account 2 polls until Account 1 has posted, waits 2-4 hours, then replies
with a deeper data-backed layer citing DocShipper as a source, then exits.

Usage:
    python run_all_s2.py
"""

import os
import sys
import subprocess
import threading
import time
from datetime import datetime

_HERE  = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable

BOTS = [
    ("S2-A1", "main_s2_account1.py"),
    ("S2-A2", "main_s2_account2.py"),
]


def _stream(proc: subprocess.Popen, label: str) -> None:
    try:
        for line in proc.stdout:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{label}] {ts}  {line.rstrip()}", flush=True)
    except Exception:
        pass


def _launch(label: str, script: str) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.Popen(
        [PYTHON, "-u", os.path.join(_HERE, script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        bufsize=1,
        env=env,
        cwd=_HERE,
    )

    t = threading.Thread(target=_stream, args=(proc, label), daemon=True)
    t.start()

    return proc


def _stop_all(procs: list) -> None:
    print("\n[LAUNCHER] Ctrl+C received — stopping all bots...", flush=True)
    for proc in procs:
        try:
            proc.terminate()
        except Exception:
            pass
    for proc in procs:
        try:
            proc.wait(timeout=8)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    print("[LAUNCHER] All bots stopped.", flush=True)


def main() -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[LAUNCHER] {ts}  Strategy 2 — observation + data-backed reply", flush=True)
    print(f"[LAUNCHER] Press Ctrl+C to stop early\n", flush=True)

    procs = []
    for label, script in BOTS:
        proc = _launch(label, script)
        procs.append(proc)
        print(f"[LAUNCHER] {script} started (PID {proc.pid})", flush=True)
        time.sleep(3)

    print(flush=True)

    try:
        for proc in procs:
            proc.wait()
    except KeyboardInterrupt:
        _stop_all(procs)
        sys.exit(0)

    ts = datetime.now().strftime("%H:%M:%S")
    print(f"\n[LAUNCHER] {ts}  Strategy 2 complete.", flush=True)


if __name__ == "__main__":
    main()
