"""
Account 3 — Synthesizer
Waits for Account 2 to post, then ties both sides together and closes the loop.
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

os.environ["COOKIES_PATH"] = os.environ.get("COOKIES_ACCOUNT3", "cookies_account3.json")
os.environ["ACCOUNT_ID"]   = "account3"

# ── Local imports (browser_helper / comment_poster read env at import time) ──
from comment_poster import post_reply, DRY_RUN, SKIP_DELAYS
from comment_generator import generate_synthesizer_comment
from coordination import get_account2_done_target, update_target
from tracker import log_action
from verify_cookies import verify_cookies

ROLE             = "synthesizer"
WAIT_MIN         = 1200   # 20 min  — between consecutive runs of this account
WAIT_MAX         = 2400   # 40 min
REPLY_DELAY_MIN  = 1200   # 20 min  — after spotting A2's comment, before replying
REPLY_DELAY_MAX  = 1800   # 30 min
NO_TARGET_WAIT   = 600    # 10 min — how long to sleep when queue is empty
NO_TARGET_WAIT_DRY = 30  # shorter wait in dry-run / skip-delays mode


def _is_night_hours() -> bool:
    return 0 <= datetime.now().hour < 8


def _inter_run_wait() -> None:
    if SKIP_DELAYS:
        print("[SLEEP] SKIP_DELAYS=True — skipping inter-run wait")
        return
    delay = random.uniform(WAIT_MIN, WAIT_MAX)
    print(f"[SLEEP] Waiting {delay / 60:.1f} min before next run...")
    time.sleep(delay)


def _run_once() -> bool:
    """
    Attempt one synthesizer reply cycle.
    Returns True if a reply was posted, False if the queue was empty.
    """
    target = get_account2_done_target()
    if not target:
        return False

    video_id    = target["video_id"]
    video_title = target["video_title"]
    a1_text     = target["account1_comment_text"]
    a2_id       = target["account2_comment_id"]
    a2_text     = target["account2_comment_text"]

    print(f"[A3] Target: {video_id} | {video_title[:65]}")
    print(f"[A3] Synthesizing over: '{a1_text[:60]}' / '{a2_text[:60]}'")

    # Wait before replying — simulates a real viewer noticing the comment later
    if not SKIP_DELAYS:
        delay = random.uniform(REPLY_DELAY_MIN, REPLY_DELAY_MAX)
        print(f"[A3] Waiting {delay / 60:.1f} min before replying...")
        time.sleep(delay)

    # 1. Generate synthesizer reply bridging both sides
    reply_text = generate_synthesizer_comment(video_title, a1_text, a2_text)
    print(f"[A3] Generated reply: {reply_text[:100]}")

    # 2. Post as a reply to Account 2's comment
    #    comment_text tells post_reply how to find the thread on the page
    comment_id = post_reply(
        video_id,
        parent_comment_id=a2_id,
        reply_text=reply_text,
        comment_text=a2_text,
    )
    print(f"[A3] Posted — comment_id: {comment_id}")

    # 3. Mark conversation complete
    update_target(
        video_id,
        account3_comment_id=comment_id,
        status="complete",
    )

    # 4. Log to Google Sheet
    log_action(
        video_id=video_id,
        video_title=video_title,
        role=ROLE,
        comment_id=comment_id,
        text=reply_text,
        status="posted",
        replied_to_id=a2_id,
        dry_run=DRY_RUN,
    )
    print(f"[A3] ✓ Conversation complete for {video_id}")
    return True


def main() -> None:
    print(f"[STARTUP] Account 3 | Synthesizer | DRY_RUN={DRY_RUN} | SKIP_DELAYS={SKIP_DELAYS}")

    if not DRY_RUN and not verify_cookies():
        print("[STARTUP] ✗ Cookie check failed — re-run save_cookies.py for account3")
        sys.exit(1)

    while True:
        try:
            if _is_night_hours():
                print(f"[SLEEP] Night hours ({datetime.now().strftime('%H:%M')}) — sleeping 30 min")
                time.sleep(1800)
                continue

            posted = _run_once()

            if not posted:
                wait = NO_TARGET_WAIT_DRY if SKIP_DELAYS else NO_TARGET_WAIT
                print(f"[A3] No account2_done target yet — checking again in {wait // 60} min")
                time.sleep(wait)
                continue

        except KeyboardInterrupt:
            print("\n[EXIT] Stopped by user")
            sys.exit(0)
        except Exception as exc:
            print(f"[ERROR] {exc}")
            print("[ERROR] Waiting 5 min before retrying...")
            time.sleep(300)
            continue

        _inter_run_wait()


if __name__ == "__main__":
    main()
