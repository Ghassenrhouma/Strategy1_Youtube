"""
coordination_s4.py — Strategy 4 state management.

Simple read/write — no file locking needed (single-process strategy).
"""

import json
import os
from datetime import datetime

_HERE        = os.path.dirname(os.path.abspath(__file__))
TARGETS_FILE = os.path.join(_HERE, "targets_s4.json")


def _read() -> dict:
    if not os.path.exists(TARGETS_FILE):
        return {"targets": []}
    with open(TARGETS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _write(data: dict) -> None:
    with open(TARGETS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_used_video_ids() -> set:
    return {t["video_id"] for t in _read()["targets"]}


def record_reply(
    video_id: str,
    video_title: str,
    comment_text: str,
    reply_text: str,
    comment_id: str,
) -> None:
    data = _read()
    data["targets"].append({
        "video_id":     video_id,
        "video_link":   f"https://www.youtube.com/watch?v={video_id}",
        "video_title":  video_title,
        "comment_text": comment_text,
        "reply_text":   reply_text,
        "comment_id":   comment_id,
        "status":       "complete",
        "timestamp":    datetime.now().isoformat(),
    })
    _write(data)
    print(f"[COORD-S4] Recorded reply for {video_id}")
