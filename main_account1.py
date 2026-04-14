"""
Account 1 — Initiator
Finds a fresh target video, posts a top-level comment, and hands off to Account 2.
"""

import os
import sys
import time
import random
from datetime import datetime
from dotenv import load_dotenv

# ── Load .env then override account-specific vars BEFORE any local import ──
_HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_HERE, ".env"))

os.environ["COOKIES_PATH"] = os.environ.get("COOKIES_ACCOUNT1", "cookies_account1.json")
os.environ["ACCOUNT_ID"]   = "account1"

# ── Local imports (browser_helper / comment_poster read env at import time) ──
from comment_poster import post_comment, DRY_RUN, SKIP_DELAYS
from comment_generator import generate_initiator_comment
from coordination import add_target, get_all_video_ids, update_target
from tracker import log_action
from verify_cookies import verify_cookies
from video_finder import find_target_video

ROLE     = "initiator"
WAIT_MIN = 1200   # 20 min
WAIT_MAX = 2400   # 40 min


def _is_night_hours() -> bool:
    return 0 <= datetime.now().hour < 8


def _inter_run_wait() -> None:
    if SKIP_DELAYS:
        print("[SLEEP] SKIP_DELAYS=True — skipping inter-run wait")
        return
    delay = random.uniform(WAIT_MIN, WAIT_MAX)
    print(f"[SLEEP] Waiting {delay / 60:.1f} min before next run...")
    time.sleep(delay)


def _run_once() -> None:
    # 1. Find a video not already in targets.json
    seen_ids = get_all_video_ids()
    print(f"[A1] Searching for a new target ({len(seen_ids)} video(s) already used)")
    video = find_target_video(seen_ids)
    video_id    = video["video_id"]
    video_title = video["title"]
    video_desc  = video.get("description", "")
    print(f"[A1] Target: {video_id} | {video_title[:65]}")

    # 2. Reserve the slot in targets.json
    add_target(video_id, video_title)

    # 3. Generate initiator comment
    comment_text = generate_initiator_comment(video_title, video_desc)
    print(f"[A1] Generated comment: {comment_text[:100]}")

    # 4. Post as a top-level comment
    comment_id = post_comment(video_id, comment_text, video_title=video_title)
    print(f"[A1] Posted — comment_id: {comment_id}")

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
    print(f"[A1] Done - handed off to Account 2")


def main() -> None:
    print(f"[STARTUP] Account 1 | Initiator | DRY_RUN={DRY_RUN} | SKIP_DELAYS={SKIP_DELAYS}")

    if not DRY_RUN and not verify_cookies():
        print("[STARTUP] Cookie check failed - re-run save_cookies.py for account1")
        sys.exit(1)

    while True:
        try:
            if _is_night_hours():
                print(f"[SLEEP] Night hours ({datetime.now().strftime('%H:%M')}) — sleeping 30 min")
                time.sleep(1800)
                continue

            _run_once()

        except KeyboardInterrupt:
            print("\n[EXIT] Stopped by user")
            sys.exit(0)
        except Exception as exc:
            print(f"[ERROR] {exc}")
            print("[ERROR] Waiting 5 min before retrying...")
            time.sleep(300)

        _inter_run_wait()


if __name__ == "__main__":
    main()
