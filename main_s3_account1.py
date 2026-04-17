"""
Strategy 3 — Account 1 (Side A / Debater A)

Takes the "side A" position on a polarizing import/trade topic.
Posts the opening comment (turn 1), then returns for every odd-numbered
follow-up turn until the thread reaches its total_turns limit.
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

from comment_poster import post_comment, post_reply, DRY_RUN, SKIP_DELAYS
from comment_generator_s3 import generate_opening, generate_reply, pick_topic_pair
from coordination_s3 import (
    get_all_video_ids, get_used_topic_ids_this_week,
    get_active_target, get_target_by_video_id,
    get_my_turn_target, add_target, record_turn,
)
from tracker import log_action
from verify_cookies import verify_cookies
from video_finder import find_target_video

ROLE             = "debater_a"
REPLY_DELAY_MIN  = 3600   # 1 hour
REPLY_DELAY_MAX  = 10800  # 3 hours
POLL_WAIT        = 600    # 10 min
POLL_WAIT_DRY    = 30


def _start_new_thread() -> str:
    """Find a video, pick a topic pair, post the opening comment. Returns video_id."""
    seen_ids      = get_all_video_ids()
    used_topics   = get_used_topic_ids_this_week()
    print(f"[S3-A1] Searching for a new target ({len(seen_ids)} video(s) used)")
    print(f"[S3-A1] Topic IDs used this week: {used_topics}")

    video       = find_target_video(seen_ids)
    video_id    = video["video_id"]
    video_title = video["title"]

    topic        = pick_topic_pair(used_topics)
    total_turns  = random.randint(3, 5)
    # DocShipper appears in turn 2 or 3 — not the opener, not always the last word
    docshipper_turn = random.randint(2, min(3, total_turns))

    print(f"[S3-A1] Video : {video_id} | {video_title[:65]}")
    print(f"[S3-A1] Topic : {topic['side_a']} vs {topic['side_b']}")
    print(f"[S3-A1] Turns : {total_turns} | DocShipper on turn {docshipper_turn}")

    add_target(
        video_id        = video_id,
        video_title     = video_title,
        topic_id        = topic["id"],
        side_a          = topic["side_a"],
        side_b          = topic["side_b"],
        position_a      = topic["position_a"],
        position_b      = topic["position_b"],
        total_turns     = total_turns,
        docshipper_turn = docshipper_turn,
    )

    comment_text = generate_opening(video_title, topic["side_a"], topic["side_b"], topic["position_a"])
    print(f"[S3-A1] Turn 1 comment: {comment_text[:100]}")

    comment_id = post_comment(video_id, comment_text, video_title=video_title)
    print(f"[S3-A1] Posted — comment_id: {comment_id}")

    entry = record_turn(video_id, "account1", comment_id, comment_text)

    log_action(
        video_id      = video_id,
        video_title   = video_title,
        role          = ROLE,
        comment_id    = comment_id,
        text          = comment_text,
        status        = "posted",
        replied_to_id = "",
        dry_run       = DRY_RUN,
    )
    print(f"[S3-A1] Turn 1 done. Handed off to account2. Status: {entry['status']}")
    return video_id


def _post_reply_turn(target: dict) -> dict:
    """Post a follow-up reply on our turn. Returns the updated target entry."""
    video_id    = target["video_id"]
    video_title = target["video_title"]
    turn_num    = target["turns_posted"] + 1  # turn we are about to post

    include_docshipper = (
        turn_num == target["docshipper_turn"]
        and not target["docshipper_mentioned"]
    )

    print(f"[S3-A1] Posting turn {turn_num}/{target['total_turns']} for {video_id}")
    print(f"[S3-A1] DocShipper in this turn: {include_docshipper}")

    reply_text = generate_reply(
        video_title       = video_title,
        side_a            = target["side_a"],
        side_b            = target["side_b"],
        account_id        = "account1",
        my_position       = target["position_a"],
        comments          = target["comments"],
        include_docshipper= include_docshipper,
    )
    print(f"[S3-A1] Generated: {reply_text[:100]}")

    prev = target["comments"][-1]
    comment_id = post_reply(
        video_id          = video_id,
        parent_comment_id = prev["comment_id"],
        reply_text        = reply_text,
        comment_text      = prev["text"],
    )
    print(f"[S3-A1] Posted — comment_id: {comment_id}")

    entry = record_turn(video_id, "account1", comment_id, reply_text)

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
    print(f"[S3-A1] Turn {turn_num} done. Status: {entry['status']}")
    return entry


def main() -> None:
    print(f"[STARTUP] S3 Account 1 | Side A | DRY_RUN={DRY_RUN} | SKIP_DELAYS={SKIP_DELAYS}")

    if not DRY_RUN and not verify_cookies():
        print("[STARTUP] Profile check failed — re-run login.py for account1")
        sys.exit(1)

    # Track which thread we are responsible for so we know when to exit
    # even if account2 posts the final turn.
    video_id_in_progress = None

    try:
        while True:
            # --- Check if it's our turn to reply ---
            target = get_my_turn_target("account1")
            if target is not None:
                video_id_in_progress = target["video_id"]

                if not SKIP_DELAYS:
                    delay = random.uniform(REPLY_DELAY_MIN, REPLY_DELAY_MAX)
                    print(f"[S3-A1] Waiting {delay / 3600:.1f}h before turn {target['turns_posted'] + 1}...")
                    time.sleep(delay)

                entry = _post_reply_turn(target)
                if entry["status"] == "complete":
                    print(f"[S3-A1] Thread complete.")
                    break
                continue  # loop back — wait for account2's next reply

            # --- Not our turn ---
            if video_id_in_progress is None:
                # Haven't started anything yet
                active = get_active_target()
                if active is None:
                    # No thread at all — start one
                    video_id_in_progress = _start_new_thread()
                else:
                    # Resuming an interrupted run — pick up the existing thread
                    video_id_in_progress = active["video_id"]
                    print(f"[S3-A1] Resuming existing thread: {video_id_in_progress}")
                continue
            else:
                # We have a thread — check if account2 just posted the final turn
                entry = get_target_by_video_id(video_id_in_progress)
                if entry and entry["status"] == "complete":
                    print(f"[S3-A1] Thread complete (account2 posted last turn).")
                    break

            wait = POLL_WAIT_DRY if SKIP_DELAYS else POLL_WAIT
            print(f"[S3-A1] Waiting for account2 to reply — checking in {wait // 60} min")
            time.sleep(wait)

    except KeyboardInterrupt:
        print("\n[EXIT] Stopped by user")
        sys.exit(0)
    except Exception as exc:
        print(f"[ERROR] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
