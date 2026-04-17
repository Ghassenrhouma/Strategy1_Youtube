"""
Strategy 4 — Single-Account Comment Engager

Finds videos in the niche, scrolls through existing real viewer comments,
picks a replyable one (question, opinion, or experience), generates a
contextual reply that mentions DocShipper as a personal reference, posts it,
waits, then repeats on the next video indefinitely.
"""

import os
import sys
import time
import random
from dotenv import load_dotenv

_HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_HERE, ".env"))

os.environ["PROFILE_PATH"] = os.environ.get("PROFILE_ACCOUNT1", "profiles/account1")
os.environ["ACCOUNT_ID"]   = "account1"

from comment_poster import scrape_and_reply, DRY_RUN, SKIP_DELAYS
from comment_generator_s4 import is_replyable, generate_comment_reply
from coordination_s4 import get_used_video_ids, record_reply
from tracker import log_action
from verify_cookies import verify_cookies
from video_finder import find_target_video

ROLE            = "engager"
LOOP_DELAY_MIN  = 3600   # 1 hour between videos
LOOP_DELAY_MAX  = 7200   # 2 hours
LOOP_DELAY_DRY  = 30     # 30 s in skip-delays mode


def _run_once() -> None:
    seen_ids    = get_used_video_ids()
    print(f"[S4] Searching for next video ({len(seen_ids)} used so far)")

    video       = find_target_video(seen_ids)
    video_id    = video["video_id"]
    video_title = video["title"]
    print(f"[S4] Target: {video_id} | {video_title[:65]}")

    if DRY_RUN:
        # Simulate without opening a browser — still tests the LLM generator
        mock_comment = (
            "Anyone know what the typical lead time is for sea freight from "
            "Shenzhen to Paris these days? Getting very different answers."
        )
        reply_text = generate_comment_reply(video_title, mock_comment)
        result = {
            "comment_text": mock_comment,
            "reply_text":   reply_text,
            "comment_id":   f"dry_run_{video_id}",
        }
        print(f"[S4] [DRY RUN] Would reply to: '{mock_comment[:80]}'")
        print(f"[S4] [DRY RUN] Generated reply: '{reply_text[:100]}'")
    else:
        result = scrape_and_reply(
            video_id          = video_id,
            video_title       = video_title,
            is_replyable_fn   = is_replyable,
            generate_reply_fn = generate_comment_reply,
        )

    record_reply(
        video_id      = video_id,
        video_title   = video_title,
        comment_text  = result["comment_text"],
        reply_text    = result["reply_text"],
        comment_id    = result["comment_id"],
    )

    log_action(
        video_id      = video_id,
        video_title   = video_title,
        role          = ROLE,
        comment_id    = result["comment_id"],
        text          = result["reply_text"],
        status        = "posted",
        replied_to_id = "",
        dry_run       = DRY_RUN,
    )
    print(f"[S4] Done — reply: '{result['reply_text'][:100]}'")


def main() -> None:
    print(f"[STARTUP] S4 Engager | DRY_RUN={DRY_RUN} | SKIP_DELAYS={SKIP_DELAYS}")

    if not DRY_RUN and not verify_cookies():
        print("[STARTUP] Profile check failed — re-run login.py for account1")
        sys.exit(1)

    while True:
        try:
            _run_once()
        except KeyboardInterrupt:
            print("\n[EXIT] Stopped by user")
            sys.exit(0)
        except Exception as exc:
            print(f"[ERROR] {exc}")
            print("[S4] Skipping this video — retrying in 5 min...")
            try:
                time.sleep(300)
            except KeyboardInterrupt:
                print("\n[EXIT] Stopped by user")
                sys.exit(0)
            continue

        delay = LOOP_DELAY_DRY if SKIP_DELAYS else random.uniform(LOOP_DELAY_MIN, LOOP_DELAY_MAX)
        print(f"[S4] Waiting {delay / 60:.0f} min before next video...")
        try:
            time.sleep(delay)
        except KeyboardInterrupt:
            print("\n[EXIT] Stopped by user")
            sys.exit(0)


if __name__ == "__main__":
    main()
