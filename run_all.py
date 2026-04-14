"""
run_all.py — Runs one full 3-account conversation on a single video.

Starts all 3 bots in parallel:
  Account 1 finds a video and posts the initiator comment, then exits.
  Account 2 waits for Account 1, posts the challenger reply, then exits.
  Account 3 waits for Account 2, posts the synthesizer reply, then exits.

When all three have finished, run_all.py exits.
Press Ctrl+C to stop everything early.

Usage:
    python run_all.py
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
    ("A1", "main_account1.py"),
    ("A2", "main_account2.py"),
    ("A3", "main_account3.py"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Output streaming
# ─────────────────────────────────────────────────────────────────────────────

def _stream(proc: subprocess.Popen, label: str) -> None:
    """Read lines from a subprocess stdout and print with prefix + timestamp."""
    try:
        for line in proc.stdout:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{label}] {ts}  {line.rstrip()}", flush=True)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Launch
# ─────────────────────────────────────────────────────────────────────────────

def _launch(label: str, script: str) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"]  = "1"
    env["PYTHONIOENCODING"]  = "utf-8"

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


# ─────────────────────────────────────────────────────────────────────────────
# Shutdown
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[LAUNCHER] {ts}  Starting — one conversation on one video", flush=True)
    print(f"[LAUNCHER] Press Ctrl+C to stop early\n", flush=True)

    procs = []
    for label, script in BOTS:
        proc = _launch(label, script)
        procs.append(proc)
        print(f"[LAUNCHER] {script} started (PID {proc.pid})", flush=True)
        time.sleep(3)   # small stagger so bots don't all connect simultaneously

    print(flush=True)

    # Wait for all three to finish naturally
    try:
        for proc in procs:
            proc.wait()
    except KeyboardInterrupt:
        _stop_all(procs)
        sys.exit(0)

    ts = datetime.now().strftime("%H:%M:%S")
    print(f"\n[LAUNCHER] {ts}  All bots finished — conversation complete.", flush=True)


if __name__ == "__main__":
    main()
