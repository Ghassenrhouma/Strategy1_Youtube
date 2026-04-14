import contextlib
import json
import os
import time
from dotenv import load_dotenv

load_dotenv()

TARGETS_FILE = os.getenv("TARGETS_FILE", "targets.json")
LOCK_FILE = TARGETS_FILE + ".lock"

_LOCK_TIMEOUT = 15   # seconds to wait before giving up
_LOCK_STALE   = 30   # seconds before treating an existing lock as stale


# ---------------------------------------------------------------------------
# File locking
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def _file_lock():
    """
    Exclusive lock via a companion .lock file.

    Uses open(..., 'x') which is atomic on all major filesystems — it only
    succeeds if the file does not yet exist, so two concurrent writers cannot
    both succeed. Stale locks (left by a crashed process) are cleared after
    _LOCK_STALE seconds.
    """
    deadline = time.time() + _LOCK_TIMEOUT

    while True:
        try:
            fh = open(LOCK_FILE, "x")
            fh.close()
            break                           # acquired
        except FileExistsError:
            # Remove lock if it is older than _LOCK_STALE seconds
            try:
                age = time.time() - os.path.getmtime(LOCK_FILE)
                if age > _LOCK_STALE:
                    os.remove(LOCK_FILE)
                    continue                # retry immediately
            except FileNotFoundError:
                continue                    # another process just cleared it

            if time.time() >= deadline:
                raise TimeoutError(
                    f"Could not acquire {LOCK_FILE} within {_LOCK_TIMEOUT}s. "
                    "Delete the file manually if a previous run crashed."
                )
            time.sleep(0.15)

    try:
        yield
    finally:
        try:
            os.remove(LOCK_FILE)
        except FileNotFoundError:
            pass                            # already removed — safe to ignore


# ---------------------------------------------------------------------------
# Raw I/O (always called inside _file_lock)
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

def add_target(video_id: str, video_title: str) -> None:
    """
    Append a new pending entry to targets.json.
    Silently skips if video_id is already present.
    """
    with _file_lock():
        data = _read()
        existing = {t["video_id"] for t in data["targets"]}
        if video_id in existing:
            print(f"[COORD] Already in targets — skipping: {video_id}")
            return
        data["targets"].append({
            "video_id":            video_id,
            "video_link":          f"https://www.youtube.com/watch?v={video_id}",
            "video_title":         video_title,
            "status":              "pending",
            "account1_comment_id":   "",
            "account1_comment_text": "",
            "account2_comment_id":   "",
            "account2_comment_text": "",
            "account3_comment_id":   "",
        })
        _write(data)
    print(f"[COORD] Added target: {video_id} | {video_title[:60]}")


def get_pending_target() -> dict | None:
    """
    Return the first target with status 'pending' (Account 1 not yet posted),
    or None if there are no pending targets.
    """
    with _file_lock():
        data = _read()
        for entry in data["targets"]:
            if entry.get("status") == "pending":
                return dict(entry)
    return None


def get_account1_done_target() -> dict | None:
    """
    Return the first target with status 'account1_done' (Account 2 not yet replied),
    or None if there are none.
    """
    with _file_lock():
        data = _read()
        for entry in data["targets"]:
            if entry.get("status") == "account1_done":
                return dict(entry)
    return None


def get_account2_done_target() -> dict | None:
    """
    Return the first target with status 'account2_done' (Account 3 not yet replied),
    or None if there are none.
    """
    with _file_lock():
        data = _read()
        for entry in data["targets"]:
            if entry.get("status") == "account2_done":
                return dict(entry)
    return None


def update_target(
    video_id: str,
    account1_comment_id:   str | None = None,
    account1_comment_text: str | None = None,
    account2_comment_id:   str | None = None,
    account2_comment_text: str | None = None,
    account3_comment_id:   str | None = None,
    status: str | None = None,
) -> None:
    """
    Update one or more fields on a target identified by video_id.
    Only non-None arguments overwrite existing values.
    """
    with _file_lock():
        data = _read()
        for entry in data["targets"]:
            if entry["video_id"] != video_id:
                continue
            if account1_comment_id is not None:
                entry["account1_comment_id"]   = account1_comment_id
            if account1_comment_text is not None:
                entry["account1_comment_text"] = account1_comment_text
            if account2_comment_id is not None:
                entry["account2_comment_id"]   = account2_comment_id
            if account2_comment_text is not None:
                entry["account2_comment_text"] = account2_comment_text
            if account3_comment_id is not None:
                entry["account3_comment_id"]   = account3_comment_id
            if status is not None:
                entry["status"] = status
            _write(data)
            print(f"[COORD] Updated {video_id}: status={entry['status']}")
            return
    print(f"[COORD] WARNING: video_id not found in targets — {video_id}")


def get_all_video_ids() -> set:
    """
    Return every video_id already in targets.json regardless of status.
    Used by the video finder to avoid picking the same video twice.
    """
    with _file_lock():
        data = _read()
    return {t["video_id"] for t in data["targets"] if t.get("video_id")}


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import tempfile, shutil

    # Work in a temp copy so the real targets.json is untouched
    orig = TARGETS_FILE
    tmp_dir = tempfile.mkdtemp()
    tmp_file = os.path.join(tmp_dir, "targets.json")
    if os.path.exists(orig):
        shutil.copy(orig, tmp_file)
    else:
        with open(tmp_file, "w") as f:
            json.dump({"targets": []}, f)

    # Monkey-patch module-level paths for the test
    import coordination as _self
    _self.TARGETS_FILE = tmp_file
    _self.LOCK_FILE    = tmp_file + ".lock"

    print("--- add_target ---")
    add_target("abc123", "How to Import from China: Full Guide")
    add_target("abc123", "duplicate — should be skipped")
    add_target("xyz789", "Amazon FBA Freight Forwarder Tips")

    print("\n--- get_all_video_ids ---")
    print(get_all_video_ids())

    print("\n--- get_pending_target ---")
    print(get_pending_target())

    print("\n--- update_target: account1 posts ---")
    update_target("abc123", account1_comment_id="comment_id_001", status="account1_done")

    print("\n--- get_account1_done_target ---")
    print(get_account1_done_target())

    print("\n--- update_target: account2 replies ---")
    update_target("abc123", account2_comment_id="comment_id_002", status="account2_done")

    print("\n--- get_account2_done_target ---")
    print(get_account2_done_target())

    print("\n--- update_target: account3 synthesizes ---")
    update_target("abc123", account3_comment_id="comment_id_003", status="complete")

    print("\n--- final state ---")
    with open(tmp_file) as f:
        print(json.dumps(json.load(f), indent=2))

    shutil.rmtree(tmp_dir)
    print("\n[OK] coordination smoke test passed")
