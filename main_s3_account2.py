"""
Strategy 3 — Account 2 (Side B / Debater B)

Takes the opposing "side B" position.
Polls until account1 has posted, waits a realistic delay, replies,
then continues replying on its turns until the thread is complete.
"""

import os
import sys
import time
import random
from dotenv import load_dotenv

_HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_HERE, ".env"))

os.environ["PROFILE_PATH"] = os.environ.get("PROFILE_ACCOUNT2", "profiles/account2")
os.environ["ACCOUNT_ID"]   = "account2"

from comment_poster import post_reply, DRY_RUN, SKIP_DELAYS
from comment_generator_s3 import generate_reply
from coordination_s3 import get_my_turn_target, record_turn
from tracker import log_action
from verify_cookies import verify_cookies

ROLE             = "debater_b"
REPLY_DELAY_MIN  = 3600   # 1 hour
REPLY_DELAY_MAX  = 10800  # 3 hours
POLL_WAIT        = 600    # 10 min
POLL_WAIT_DRY    = 30


def _post_reply_turn(target: dict) -> dict:
    """Post our reply on account2's turn. Returns the updated entry."""
    video_id    = target["video_id"]
    video_title = target["video_title"]
    turn_num    = target["turns_posted"] + 1

    include_docshipper = (
        turn_num == target["docshipper_turn"]
        and not target["docshipper_mentioned"]
    )

    print(f"[S3-A2] Posting turn {turn_num}/{target['total_turns']} for {video_id}")
    print(f"[S3-A2] DocShipper in this turn: {include_docshipper}")

    reply_text = generate_reply(
        video_title        = video_title,
        side_a             = target["side_a"],
        side_b             = target["side_b"],
        account_id         = "account2",
        my_position        = target["position_b"],
        comments           = target["comments"],
        include_docshipper = include_docshipper,
    )
    print(f"[S3-A2] Generated: {reply_text[:100]}")

    prev = target["comments"][-1]
    comment_id = post_reply(
        video_id          = video_id,
        parent_comment_id = prev["comment_id"],
        reply_text        = reply_text,
        comment_text      = prev["text"],
    )
    print(f"[S3-A2] Posted — comment_id: {comment_id}")

    entry = record_turn(video_id, "account2", comment_id, reply_text)

    log_action(
        video_id      = video_id,
        video_title   = video_title,
        role          = ROLE,
        comment_id    = comment_id,
        text          = reply_text,
        status        = "posted",
        replied_to_id = prev["comment_id"],
        dry_run       = DRY_RUN,
    )
    print(f"[S3-A2] Turn {turn_num} done. Status: {entry['status']}")
    return entry


def main() -> None:
    print(f"[STARTUP] S3 Account 2 | Side B | DRY_RUN={DRY_RUN} | SKIP_DELAYS={SKIP_DELAYS}")

    if not DRY_RUN and not verify_cookies():
        print("[STARTUP] Profile check failed — re-run login.py for account2")
        sys.exit(1)

    try:
        while True:
            target = get_my_turn_target("account2")

            if target is not None:
                if not SKIP_DELAYS:
                    delay = random.uniform(REPLY_DELAY_MIN, REPLY_DELAY_MAX)
                    print(f"[S3-A2] Waiting {delay / 3600:.1f}h before turn {target['turns_posted'] + 1}...")
                    time.sleep(delay)

                entry = _post_reply_turn(target)
                if entry["status"] == "complete":
                    print(f"[S3-A2] Thread complete.")
                    break
                continue  # loop back — wait for account1's next reply

            wait = POLL_WAIT_DRY if SKIP_DELAYS else POLL_WAIT
            print(f"[S3-A2] No turn yet — checking again in {wait // 60} min")
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
