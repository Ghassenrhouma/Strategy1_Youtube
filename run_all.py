"""
run_all.py — Single entry point for the 3-account conversation bot.

Starts main_account1.py, main_account2.py, and main_account3.py as parallel
subprocesses. Their output is merged into one stream, prefixed with which
account produced each line and a timestamp.

If a bot crashes unexpectedly it is automatically restarted after 60 seconds.
Press Ctrl+C once to stop everything cleanly.

Usage:
    python run_all.py
"""

import os
import sys
import subprocess
import threading
import time
from datetime import datetime

_HERE   = os.path.dirname(os.path.abspath(__file__))
PYTHON  = sys.executable

BOTS = [
    ("A1", "main_account1.py"),
    ("A2", "main_account2.py"),
    ("A3", "main_account3.py"),
]

RESTART_DELAY = 60   # seconds before restarting a crashed bot
_shutdown     = False
_procs        = {}   # label → subprocess.Popen
_lock         = threading.Lock()


# ─────────────────────────────────────────────────────────────────────────────
# Output streaming
# ─────────────────────────────────────────────────────────────────────────────

def _stream(proc: subprocess.Popen, label: str) -> None:
    """Read lines from a subprocess and print them with prefix + timestamp."""
    try:
        for line in proc.stdout:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{label}] {ts}  {line.rstrip()}", flush=True)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Process management
# ─────────────────────────────────────────────────────────────────────────────

def _launch(label: str, script: str) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"   # force line-buffered output from subprocesses

    proc = subprocess.Popen(
        [PYTHON, "-u", os.path.join(_HERE, script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,   # merge stderr into stdout
        text=True,
        bufsize=1,
        env=env,
        cwd=_HERE,
    )

    t = threading.Thread(target=_stream, args=(proc, label), daemon=True)
    t.start()

    with _lock:
        _procs[label] = proc

    return proc


def _watchdog(label: str, script: str) -> None:
    """
    Runs in its own thread. Waits for the bot process to exit; if it exits
    while we are not shutting down it restarts the process after RESTART_DELAY
    seconds. Exit code 0 (clean Ctrl+C) and exit code 1 (cookie failure) are
    both restarted — cookie failures surface in the log output so the operator
    can intervene.
    """
    global _shutdown

    while not _shutdown:
        with _lock:
            proc = _procs.get(label)

        if proc is None:
            time.sleep(1)
            continue

        exit_code = proc.wait()   # blocks until the process exits

        if _shutdown:
            break

        ts = datetime.now().strftime("%H:%M:%S")
        print(
            f"[LAUNCHER] {ts}  [{label}] exited (code {exit_code}) "
            f"— restarting in {RESTART_DELAY}s...",
            flush=True,
        )

        # Sleep in small chunks so Ctrl+C is responsive during the wait
        for _ in range(RESTART_DELAY * 10):
            if _shutdown:
                return
            time.sleep(0.1)

        if _shutdown:
            break

        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[LAUNCHER] {ts}  [{label}] restarting {script}", flush=True)
        _launch(label, script)


# ─────────────────────────────────────────────────────────────────────────────
# Shutdown
# ─────────────────────────────────────────────────────────────────────────────

def _stop_all() -> None:
    global _shutdown
    _shutdown = True

    print("\n[LAUNCHER] Ctrl+C received — stopping all bots...", flush=True)

    with _lock:
        snapshot = list(_procs.values())

    for proc in snapshot:
        try:
            proc.terminate()
        except Exception:
            pass

    for proc in snapshot:
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
    print(f"[LAUNCHER] {ts}  Starting 3-account bot system", flush=True)
    print(f"[LAUNCHER] Python: {PYTHON}", flush=True)
    print(f"[LAUNCHER] Working dir: {_HERE}", flush=True)
    print(f"[LAUNCHER] Press Ctrl+C to stop all bots\n", flush=True)

    # Launch all bots and their watchdogs
    for label, script in BOTS:
        _launch(label, script)
        print(f"[LAUNCHER] {script} started (PID {_procs[label].pid})", flush=True)

        # Small stagger so bots don't all hit YouTube simultaneously at startup
        time.sleep(3)

    # Start watchdog threads (daemon=True so they don't block clean exit)
    for label, script in BOTS:
        t = threading.Thread(target=_watchdog, args=(label, script), daemon=True)
        t.start()

    print(flush=True)

    # Main thread just waits — watchdogs and stream threads do all the work
    try:
        while not _shutdown:
            time.sleep(1)
    except KeyboardInterrupt:
        _stop_all()
        sys.exit(0)


if __name__ == "__main__":
    main()
