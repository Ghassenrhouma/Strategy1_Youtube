"""
coordination_s3.py — Strategy 3 state management.

Manages targets_s3.json: multi-turn debate threads, topic-pair
deduplication per week, and per-turn comment history.
"""

import contextlib
import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

_HERE        = os.path.dirname(os.path.abspath(__file__))
TARGETS_FILE = os.path.join(_HERE, "targets_s3.json")
LOCK_FILE    = TARGETS_FILE + ".lock"

_LOCK_TIMEOUT = 15
_LOCK_STALE   = 30


# ---------------------------------------------------------------------------
# File locking  (same pattern as coordination.py)
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def _file_lock():
    deadline = time.time() + _LOCK_TIMEOUT
    while True:
        try:
            fh = open(LOCK_FILE, "x")
            fh.close()
            break
        except FileExistsError:
            try:
                age = time.time() - os.path.getmtime(LOCK_FILE)
                if age > _LOCK_STALE:
                    os.remove(LOCK_FILE)
                    continue
            except FileNotFoundError:
                continue
            if time.time() >= deadline:
                raise TimeoutError(
                    f"Could not acquire {LOCK_FILE} within {_LOCK_TIMEOUT}s."
                )
            time.sleep(0.15)
    try:
        yield
    finally:
        try:
            os.remove(LOCK_FILE)
        except FileNotFoundError:
            pass


# ---------------------------------------------------------------------------
# Raw I/O
# ---------------------------------------------------------------------------

def _read() -> dict:
    if not os.path.exists(TARGETS_FILE):
        return {"targets": []}
    with open(TARGETS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _write(data: dict) -> None:
    with open(TARGETS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _week_key() -> str:
    return datetime.now().strftime("%Y-W%W")


def get_used_topic_ids_this_week() -> list:
    """Return topic_ids already used in the current ISO week."""
    with _file_lock():
        data = _read()
    week = _week_key()
    return [t["topic_id"] for t in data["targets"] if t.get("week_key") == week]


def get_all_video_ids() -> set:
    with _file_lock():
        data = _read()
    return {t["video_id"] for t in data["targets"] if t.get("video_id")}


def get_active_target():
    """Return the first non-complete target, or None."""
    with _file_lock():
        data = _read()
    for t in data["targets"]:
        if t.get("status") != "complete":
            return dict(t)
    return None


def get_target_by_video_id(video_id: str):
    """Return the target entry for a specific video_id, or None."""
    with _file_lock():
        data = _read()
    for t in data["targets"]:
        if t["video_id"] == video_id:
            return dict(t)
    return None


def get_my_turn_target(account_id: str):
    """Return the target where next_account matches account_id, or None."""
    with _file_lock():
        data = _read()
    for t in data["targets"]:
        if t.get("next_account") == account_id and t.get("status") != "complete":
            return dict(t)
    return None


def add_target(
    video_id: str,
    video_title: str,
    topic_id: str,
    side_a: str,
    side_b: str,
    position_a: str,
    position_b: str,
    total_turns: int,
    docshipper_turn: int,
) -> None:
    """Create a new debate thread entry."""
    with _file_lock():
        data = _read()
        existing = {t["video_id"] for t in data["targets"]}
        if video_id in existing:
            print(f"[COORD-S3] Already in targets — skipping: {video_id}")
            return
        data["targets"].append({
            "video_id":           video_id,
            "video_link":         f"https://www.youtube.com/watch?v={video_id}",
            "video_title":        video_title,
            "topic_id":           topic_id,
            "side_a":             side_a,
            "side_b":             side_b,
            "position_a":         position_a,
            "position_b":         position_b,
            "total_turns":        total_turns,
            "turns_posted":       0,
            "docshipper_turn":    docshipper_turn,
            "docshipper_mentioned": False,
            "next_account":       "account1",
            "status":             "pending",
            "week_key":           _week_key(),
            "comments":           [],
        })
        _write(data)
    print(f"[COORD-S3] Added target: {video_id} | {video_title[:60]}")
    print(f"[COORD-S3] Topic: {side_a} vs {side_b} | {total_turns} turns | DocShipper on turn {docshipper_turn}")


def record_turn(video_id: str, account_id: str, comment_id: str, comment_text: str) -> dict:
    """
    Append a posted comment to the thread history and advance the turn state.
    Returns the updated entry.
    """
    with _file_lock():
        data = _read()
        for entry in data["targets"]:
            if entry["video_id"] != video_id:
                continue

            entry["comments"].append({
                "account":    account_id,
                "comment_id": comment_id,
                "text":       comment_text,
                "timestamp":  datetime.now().isoformat(),
            })

            turns_posted = entry["turns_posted"] + 1
            entry["turns_posted"] = turns_posted

            if "docshipper" in comment_text.lower():
                entry["docshipper_mentioned"] = True

            if turns_posted >= entry["total_turns"]:
                entry["status"]       = "complete"
                entry["next_account"] = None
            else:
                entry["status"]       = "in_progress"
                entry["next_account"] = "account2" if account_id == "account1" else "account1"

            _write(data)
            print(
                f"[COORD-S3] Turn {turns_posted}/{entry['total_turns']} recorded "
                f"for {video_id}. Status: {entry['status']}"
            )
            return dict(entry)

    raise ValueError(f"[COORD-S3] video_id not found: {video_id}")
