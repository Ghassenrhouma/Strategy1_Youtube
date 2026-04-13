"""
test_dry_run.py — End-to-end dry-run test for the 3-account conversation bot.

Simulates the full Account1 → Account2 → Account3 pipeline without opening
a browser or posting anything real:

  DRY_RUN=True      no Playwright, post_comment / post_reply return stubs
  SKIP_DELAYS=True  no time.sleep calls
  Temp targets.json real targets.json is never touched

Usage:
  python test_dry_run.py
"""

# ─────────────────────────────────────────────────────────────────────────────
# ALL env setup must happen before ANY local import.
# browser_helper captures COOKIES_PATH + HEADLESS at import time.
# comment_poster captures DRY_RUN + SKIP_DELAYS at import time.
# coordination captures TARGETS_FILE at import time.
# ─────────────────────────────────────────────────────────────────────────────
import os
import sys
import json
import shutil
import tempfile
from datetime import datetime
from dotenv import load_dotenv

_HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_HERE, ".env"))

# Force test flags (override whatever .env says)
os.environ["DRY_RUN"]      = "True"
os.environ["SKIP_DELAYS"]  = "True"
os.environ["HEADLESS"]     = "True"
os.environ["COOKIES_PATH"] = os.environ.get("COOKIES_ACCOUNT1", "cookies_account1.json")
os.environ["ACCOUNT_ID"]   = "account1"

# Isolated targets.json so the real file is never touched
_TMP_DIR     = tempfile.mkdtemp(prefix="bot_dryrun_")
_TMP_TARGETS = os.path.join(_TMP_DIR, "targets.json")
with open(_TMP_TARGETS, "w", encoding="utf-8") as _f:
    json.dump({"targets": []}, _f)
os.environ["TARGETS_FILE"] = _TMP_TARGETS  # read by coordination at import time

# ─────────────────────────────────────────────────────────────────────────────
# Local imports
# ─────────────────────────────────────────────────────────────────────────────
from comment_poster import post_comment, post_reply, DRY_RUN, SKIP_DELAYS
from comment_generator import (
    generate_initiator_comment,
    generate_challenger_comment,
    generate_synthesizer_comment,
)
import coordination as _coord
# Belt-and-suspenders: patch module vars in case coordination was already
# imported transitively before TARGETS_FILE was set
_coord.TARGETS_FILE = _TMP_TARGETS
_coord.LOCK_FILE    = _TMP_TARGETS + ".lock"

from coordination import (
    add_target,
    get_all_video_ids,
    get_account1_done_target,
    get_account2_done_target,
    update_target,
)
from tracker import log_action

# ─────────────────────────────────────────────────────────────────────────────
# Test helpers
# ─────────────────────────────────────────────────────────────────────────────
_PASS = 0
_FAIL = 0


def _check(condition: bool, label: str) -> None:
    global _PASS, _FAIL
    if condition:
        _PASS += 1
        print(f"  ✓  {label}")
    else:
        _FAIL += 1
        print(f"  ✗  FAIL: {label}")


def _has_dash(text: str) -> bool:
    """Returns True if text contains any kind of dash."""
    return any(c in text for c in ("-", "\u2013", "\u2014"))


def _generate_safe(fn, *args) -> str:
    """
    Call an LLM generator function.
    Falls back to a minimal mock string if the API call fails, so the test
    can verify coordination and posting logic even without a live API key.
    """
    try:
        result = fn(*args)
        preview = result[:90].replace("\n", " ")
        print(f"    [LLM] {fn.__name__}: {preview}")
        return result
    except Exception as exc:
        mock = f"[MOCK {fn.__name__}] test comment about shipping costs and import paperwork"
        print(f"    [LLM] {fn.__name__} failed ({exc})")
        print(f"    [LLM] Using mock: {mock[:70]}")
        return mock


# Stub video — stands in for what find_target_video() would return
TEST_VIDEO = {
    "video_id":    "DRY_RUN_TEST_001",
    "title":       "How to Import from China: Shipping, Customs and Duties Explained",
    "description": "Full guide to importing goods from China including freight forwarding and customs.",
}


# ─────────────────────────────────────────────────────────────────────────────
# Preflight
# ─────────────────────────────────────────────────────────────────────────────
def _preflight() -> None:
    print("=== PREFLIGHT ===")
    _check(DRY_RUN,     "DRY_RUN is True")
    _check(SKIP_DELAYS, "SKIP_DELAYS is True")
    _check(
        os.environ.get("TARGETS_FILE") == _TMP_TARGETS,
        "TARGETS_FILE points to isolated temp file",
    )
    _check(
        _coord.TARGETS_FILE == _TMP_TARGETS,
        "coordination.TARGETS_FILE patched to temp file",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Account 1 (Initiator)
# ─────────────────────────────────────────────────────────────────────────────
def _phase_account1() -> tuple[str, str]:
    print("\n=== PHASE 1: Account 1 — Initiator ===")
    os.environ["ACCOUNT_ID"] = "account1"

    video_id    = TEST_VIDEO["video_id"]
    video_title = TEST_VIDEO["title"]
    video_desc  = TEST_VIDEO["description"]

    # get_all_video_ids — should be empty at start
    seen = get_all_video_ids()
    _check(isinstance(seen, set), "get_all_video_ids() returns a set")
    _check(video_id not in seen,  "test video not yet in targets")

    # add_target
    add_target(video_id, video_title)
    _check(video_id in get_all_video_ids(), "add_target() registers the video")

    # duplicate add must be silently ignored
    add_target(video_id, video_title)
    _check(len(get_all_video_ids()) == 1, "add_target() ignores duplicate video_id")

    # generate comment (calls Groq or falls back to mock)
    comment_text = _generate_safe(generate_initiator_comment, video_title, video_desc)
    _check(isinstance(comment_text, str) and len(comment_text) > 10,
           "initiator comment is non-empty")
    _check(not _has_dash(comment_text), "initiator comment contains no dashes")

    # post_comment in DRY_RUN mode
    comment_id = post_comment(video_id, comment_text, video_title=video_title)
    _check(comment_id == "dry_run_comment_id",
           f"post_comment() returns dry-run stub ID ({comment_id})")

    # update coordination
    update_target(
        video_id,
        account1_comment_id=comment_id,
        account1_comment_text=comment_text,
        status="account1_done",
    )
    target = get_account1_done_target()
    _check(target is not None,                               "target is now account1_done")
    _check(target["account1_comment_id"]   == comment_id,   "account1_comment_id persisted")
    _check(target["account1_comment_text"] == comment_text, "account1_comment_text persisted")

    # log_action (dry_run=True just prints)
    log_action(
        video_id=video_id, video_title=video_title, role="initiator",
        comment_id=comment_id, text=comment_text, status="posted",
        replied_to_id="", dry_run=True,
    )
    _check(True, "log_action() ran without raising")

    return comment_text, comment_id


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Account 2 (Challenger)
# ─────────────────────────────────────────────────────────────────────────────
def _phase_account2(a1_text: str, a1_id: str) -> tuple[str, str]:
    print("\n=== PHASE 2: Account 2 — Challenger ===")
    os.environ["ACCOUNT_ID"] = "account2"

    target = get_account1_done_target()
    _check(target is not None, "get_account1_done_target() finds the entry")

    video_id    = target["video_id"]
    video_title = target["video_title"]

    # generate challenger reply
    reply_text = _generate_safe(generate_challenger_comment, video_title, a1_text)
    _check(isinstance(reply_text, str) and len(reply_text) > 10,
           "challenger reply is non-empty")
    _check(not _has_dash(reply_text), "challenger reply contains no dashes")

    # post_reply in DRY_RUN mode
    comment_id = post_reply(
        video_id,
        parent_comment_id=a1_id,
        reply_text=reply_text,
        comment_text=a1_text,
    )
    _check(comment_id == "dry_run_reply_id",
           f"post_reply() returns dry-run stub ID ({comment_id})")

    # update coordination
    update_target(
        video_id,
        account2_comment_id=comment_id,
        account2_comment_text=reply_text,
        status="account2_done",
    )
    target2 = get_account2_done_target()
    _check(target2 is not None,                              "target is now account2_done")
    _check(target2["account2_comment_id"]   == comment_id,  "account2_comment_id persisted")
    _check(target2["account2_comment_text"] == reply_text,  "account2_comment_text persisted")

    log_action(
        video_id=video_id, video_title=video_title, role="challenger",
        comment_id=comment_id, text=reply_text, status="posted",
        replied_to_id=a1_id, dry_run=True,
    )
    _check(True, "log_action() ran without raising")

    return reply_text, comment_id


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Account 3 (Synthesizer)
# ─────────────────────────────────────────────────────────────────────────────
def _phase_account3(a1_text: str, a2_text: str, a2_id: str) -> None:
    print("\n=== PHASE 3: Account 3 — Synthesizer ===")
    os.environ["ACCOUNT_ID"] = "account3"

    target = get_account2_done_target()
    _check(target is not None, "get_account2_done_target() finds the entry")

    video_id    = target["video_id"]
    video_title = target["video_title"]

    # generate synthesizer reply
    reply_text = _generate_safe(generate_synthesizer_comment, video_title, a1_text, a2_text)
    _check(isinstance(reply_text, str) and len(reply_text) > 10,
           "synthesizer reply is non-empty")
    _check(not _has_dash(reply_text), "synthesizer reply contains no dashes")

    # post_reply in DRY_RUN mode
    comment_id = post_reply(
        video_id,
        parent_comment_id=a2_id,
        reply_text=reply_text,
        comment_text=a2_text,
    )
    _check(comment_id == "dry_run_reply_id",
           f"post_reply() returns dry-run stub ID ({comment_id})")

    # update coordination — marks conversation complete
    update_target(
        video_id,
        account3_comment_id=comment_id,
        status="complete",
    )

    log_action(
        video_id=video_id, video_title=video_title, role="synthesizer",
        comment_id=comment_id, text=reply_text, status="posted",
        replied_to_id=a2_id, dry_run=True,
    )
    _check(True, "log_action() ran without raising")


# ─────────────────────────────────────────────────────────────────────────────
# Final state verification
# ─────────────────────────────────────────────────────────────────────────────
def _verify_final_state() -> None:
    print("\n=== FINAL STATE: targets.json ===")
    with open(_TMP_TARGETS, encoding="utf-8") as f:
        data = json.load(f)

    targets = data.get("targets", [])
    _check(len(targets) == 1, "targets.json has exactly 1 entry")

    if targets:
        t = targets[0]
        _check(t.get("status") == "complete",             "status is 'complete'")
        _check(bool(t.get("account1_comment_id")),        "account1_comment_id set")
        _check(bool(t.get("account1_comment_text")),      "account1_comment_text set")
        _check(bool(t.get("account2_comment_id")),        "account2_comment_id set")
        _check(bool(t.get("account2_comment_text")),      "account2_comment_text set")
        _check(bool(t.get("account3_comment_id")),        "account3_comment_id set")
        _check(t.get("video_id")    == TEST_VIDEO["video_id"], "video_id matches")
        _check(t.get("video_title") == TEST_VIDEO["title"],    "video_title matches")

    print("\nFull targets.json content:")
    print(json.dumps(data, indent=2, ensure_ascii=False))


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    print(f"\n{'='*62}")
    print(f"  3-ACCOUNT BOT — DRY RUN TEST")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*62}")

    try:
        _preflight()
        a1_text, a1_id = _phase_account1()
        a2_text, a2_id = _phase_account2(a1_text, a1_id)
        _phase_account3(a1_text, a2_text, a2_id)
        _verify_final_state()
    except Exception as exc:
        import traceback
        print(f"\n[FATAL] Unexpected error during test: {exc}")
        traceback.print_exc()
        _check(False, f"no unexpected exceptions ({exc})")
    finally:
        shutil.rmtree(_TMP_DIR, ignore_errors=True)

    print(f"\n{'='*62}")
    print(f"  Results: {_PASS} passed  |  {_FAIL} failed")
    print(f"{'='*62}\n")

    sys.exit(0 if _FAIL == 0 else 1)


if __name__ == "__main__":
    main()
