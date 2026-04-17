"""
Strategy 2 — Account 2 (Analyst)
Waits for Account 1's observation, then replies hours later with a
deeper, data-backed layer that cites DocShipper as an information source.
"""

import os
import sys
import time
import random
from dotenv import load_dotenv

# ── Load .env then override account-specific vars BEFORE any local import ──
_HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_HERE, ".env"))

os.environ["PROFILE_PATH"] = os.environ.get("PROFILE_ACCOUNT2", "profiles/account2")
os.environ["ACCOUNT_ID"]   = "account2"
os.environ["TARGETS_FILE"] = os.path.join(_HERE, "targets_s2.json")

# ── Local imports ──────────────────────────────────────────────────────────
from comment_poster import post_reply, DRY_RUN, SKIP_DELAYS
from comment_generator_s2 import generate_analyst_reply
from coordination import get_account1_done_target, update_target
from tracker import log_action
from verify_cookies import verify_cookies

ROLE             = "analyst"
REPLY_DELAY_MIN  = 7200    # 2 hours — simulates reading the comment later in the day
REPLY_DELAY_MAX  = 14400   # 4 hours
NO_TARGET_WAIT   = 600     # 10 min — poll interval when A1 hasn't posted yet
NO_TARGET_WAIT_DRY = 30   # shorter poll in skip-delays mode


def _run_once() -> bool:
    target = get_account1_done_target()
    if not target:
        return False

    video_id    = target["video_id"]
    video_title = target["video_title"]
    a1_id       = target["account1_comment_id"]
    a1_text     = target["account1_comment_text"]

    print(f"[S2-A2] Target: {video_id} | {video_title[:65]}")
    print(f"[S2-A2] Replying to observation: {a1_text[:80]}")

    # Wait before replying — simulates coming back hours later
    if not SKIP_DELAYS:
        delay = random.uniform(REPLY_DELAY_MIN, REPLY_DELAY_MAX)
        print(f"[S2-A2] Waiting {delay / 3600:.1f}h before replying...")
        time.sleep(delay)

    # 1. Generate data-backed analyst reply (mentions DocShipper as data source)
    reply_text = generate_analyst_reply(video_title, a1_text)
    print(f"[S2-A2] Generated reply: {reply_text[:100]}")

    # 2. Post as a reply to Account 1's comment
    comment_id = post_reply(
        video_id,
        parent_comment_id=a1_id,
        reply_text=reply_text,
        comment_text=a1_text,
    )
    print(f"[S2-A2] Posted — comment_id: {comment_id}")

    # 3. Mark conversation complete
    update_target(
        video_id,
        account2_comment_id=comment_id,
        account2_comment_text=reply_text,
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
        replied_to_id=a1_id,
        dry_run=DRY_RUN,
    )
    print(f"[S2-A2] Conversation complete for {video_id}")
    return True


def main() -> None:
    print(f"[STARTUP] S2 Account 2 | Analyst | DRY_RUN={DRY_RUN} | SKIP_DELAYS={SKIP_DELAYS}")

    if not DRY_RUN and not verify_cookies():
        print("[STARTUP] Profile check failed - re-run login.py for account2")
        sys.exit(1)

    while True:
        try:
            posted = _run_once()

            if posted:
                break  # one reply done — exit

            wait = NO_TARGET_WAIT_DRY if SKIP_DELAYS else NO_TARGET_WAIT
            print(f"[S2-A2] No account1_done target yet — checking again in {wait // 60} min")
            time.sleep(wait)

        except KeyboardInterrupt:
            print("\n[EXIT] Stopped by user")
            sys.exit(0)
        except Exception as exc:
            print(f"[ERROR] {exc}")
            print("[ERROR] Waiting 5 min before retrying...")
            time.sleep(300)


if __name__ == "__main__":
    main()
