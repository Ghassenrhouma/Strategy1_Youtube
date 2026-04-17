"""
run_s4.py — Strategy 4 launcher (single-account comment engager).

Runs continuously until stopped with Ctrl+C.

Usage:
    python run_s4.py
"""

import os
import sys
import subprocess
import threading
from datetime import datetime

_HERE  = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable


def _stream(proc: subprocess.Popen, label: str) -> None:
    try:
        for line in proc.stdout:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{label}] {ts}  {line.rstrip()}", flush=True)
    except Exception:
        pass


def main() -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[LAUNCHER] {ts}  Strategy 4 — comment engager (continuous loop)", flush=True)
    print(f"[LAUNCHER] Press Ctrl+C to stop\n", flush=True)

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.Popen(
        [PYTHON, "-u", os.path.join(_HERE, "main_s4.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        bufsize=1,
        env=env,
        cwd=_HERE,
    )

    t = threading.Thread(target=_stream, args=(proc, "S4"), daemon=True)
    t.start()

    print(f"[LAUNCHER] main_s4.py started (PID {proc.pid})", flush=True)

    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n[LAUNCHER] Ctrl+C received — stopping...", flush=True)
        try:
            proc.terminate()
            proc.wait(timeout=8)
        except Exception:
            proc.kill()
        print("[LAUNCHER] Stopped.", flush=True)
        sys.exit(0)

    ts = datetime.now().strftime("%H:%M:%S")
    print(f"\n[LAUNCHER] {ts}  Strategy 4 exited.", flush=True)


if __name__ == "__main__":
    main()
