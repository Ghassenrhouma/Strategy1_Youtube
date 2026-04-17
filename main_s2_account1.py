"""
Strategy 2 — Account 1 (Observer)
Finds a video, drops a short surface-level observation, then exits.
Account 2 will reply hours later with a data-backed layer.
"""

import os
import sys
from dotenv import load_dotenv

# ── Load .env then override account-specific vars BEFORE any local import ──
_HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_HERE, ".env"))

os.environ["PROFILE_PATH"] = os.environ.get("PROFILE_ACCOUNT1", "profiles/account1")
os.environ["ACCOUNT_ID"]   = "account1"
os.environ["TARGETS_FILE"] = os.path.join(_HERE, "targets_s2.json")

# ── Local imports ──────────────────────────────────────────────────────────
from comment_poster import post_comment, DRY_RUN, SKIP_DELAYS
from comment_generator_s2 import generate_observer_comment
from coordination import add_target, get_all_video_ids, update_target
from tracker import log_action
from verify_cookies import verify_cookies
from video_finder import find_target_video

ROLE = "observer"


def _run_once() -> None:
    # 1. Find a video not already in targets_s2.json
    seen_ids = get_all_video_ids()
    print(f"[S2-A1] Searching for a new target ({len(seen_ids)} video(s) already used)")
    video = find_target_video(seen_ids)

    video_id    = video["video_id"]
    video_title = video["title"]
    video_desc  = video.get("description", "")
    print(f"[S2-A1] Target: {video_id} | {video_title[:65]}")

    # 2. Reserve the slot in targets_s2.json
    add_target(video_id, video_title)

    # 3. Generate observer comment
    comment_text = generate_observer_comment(video_title, video_desc)
    print(f"[S2-A1] Generated comment: {comment_text[:100]}")

    # 4. Post as a top-level comment
    comment_id = post_comment(video_id, comment_text, video_title=video_title)
    print(f"[S2-A1] Posted — comment_id: {comment_id}")

    # 5. Update coordination state
    update_target(
        video_id,
        account1_comment_id=comment_id,
        account1_comment_text=comment_text,
        status="account1_done",
    )

    # 6. Log to Google Sheet
    log_action(
        video_id=video_id,
        video_title=video_title,
        role=ROLE,
        comment_id=comment_id,
        text=comment_text,
        status="posted",
        replied_to_id="",
        dry_run=DRY_RUN,
    )
    print(f"[S2-A1] Done — handed off to Account 2")


def main() -> None:
    print(f"[STARTUP] S2 Account 1 | Observer | DRY_RUN={DRY_RUN} | SKIP_DELAYS={SKIP_DELAYS}")

    if not DRY_RUN and not verify_cookies():
        print("[STARTUP] Profile check failed - re-run login.py for account1")
        sys.exit(1)

    try:
        _run_once()
    except KeyboardInterrupt:
        print("\n[EXIT] Stopped by user")
        sys.exit(0)
    except Exception as exc:
        print(f"[ERROR] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
