import json
import os
from datetime import datetime

import gspread
from dotenv import load_dotenv

load_dotenv()

GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SERVICE_ACCOUNT_PATH = os.getenv("SERVICE_ACCOUNT_PATH", "service_account.json")
TARGETS_FILE = os.getenv("TARGETS_FILE", "targets.json")

# Sheet columns (1-indexed for gspread, 0-indexed here for reference):
# timestamp | video_id | video_link | video_title | account | role | comment_id | replied_to_id | text | status | flagged
HEADER = [
    "timestamp", "video_id", "video_link", "video_title", "account", "role",
    "comment_id", "replied_to_id", "text", "status", "flagged",
]


def _get_sheet():
    client = gspread.service_account(filename=SERVICE_ACCOUNT_PATH)
    return client.open_by_key(GOOGLE_SHEET_ID).sheet1


def _ensure_header(sheet):
    """Write header row if the sheet is empty."""
    existing = sheet.row_values(1)
    if not existing or existing[0] != "timestamp":
        sheet.insert_row(HEADER, index=1)


def log_action(
    video_id: str,
    video_title: str,
    role: str,
    comment_id: str,
    text: str,
    status: str,
    replied_to_id: str = "",
    dry_run: bool = False,
) -> None:
    """
    Append one row to the tracking sheet.

    Parameters
    ----------
    video_id       : YouTube video ID
    video_title    : Human-readable video title
    role           : "initiator", "challenger", or "synthesizer"
    comment_id     : ID returned after posting (or "dry_run_id")
    text           : The comment or reply text that was posted
    status         : "posted" or "error"
    replied_to_id  : comment_id this is replying to; empty string for Account 1
    dry_run        : If True, print the row instead of writing to the sheet
    """
    timestamp  = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    account    = os.getenv("ACCOUNT_ID", "account1")
    video_link = f"https://www.youtube.com/watch?v={video_id}"

    row = [
        timestamp,
        video_id,
        video_link,
        video_title,
        account,
        role,
        comment_id,
        replied_to_id,
        text,
        status,
        "no",           # flagged — always starts as "no"
    ]

    if dry_run:
        print("[DRY RUN] Would log row:")
        for col, val in zip(HEADER, row):
            print(f"  {col:<15}: {val}")
        return

    sheet = _get_sheet()
    _ensure_header(sheet)
    sheet.append_row(row, value_input_option="USER_ENTERED")


def get_used_video_ids() -> set:
    """
    Return the set of video IDs for conversations that have reached
    status 'complete' in targets.json. Used to avoid reusing videos.
    """
    try:
        with open(TARGETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        used = {
            t["video_id"]
            for t in data.get("targets", [])
            if t.get("status") == "complete" and t.get("video_id")
        }
        print(f"[TRACKER] {len(used)} completed video(s) found in {TARGETS_FILE}")
        return used
    except FileNotFoundError:
        print(f"[TRACKER] {TARGETS_FILE} not found — no completed videos to exclude")
        return set()
    except Exception as e:
        print(f"[TRACKER] ERROR reading {TARGETS_FILE}: {e}")
        return set()


if __name__ == "__main__":
    print("--- get_used_video_ids (targets.json is empty) ---")
    ids = get_used_video_ids()
    print(f"Used IDs: {ids}")

    print("\n--- log_action dry run ---")
    log_action(
        video_id="dQw4w9WgXcQ",
        video_title="Test Video Title",
        role="initiator",
        comment_id="dry_run_id_001",
        text="Just cleared my first LCL shipment and the duty rate was higher than quoted.",
        status="posted",
        replied_to_id="",
        dry_run=True,
    )

    print("\n--- log_action dry run (reply) ---")
    log_action(
        video_id="dQw4w9WgXcQ",
        video_title="Test Video Title",
        role="challenger",
        comment_id="dry_run_id_002",
        text="That depends heavily on the HS code classification used.",
        status="posted",
        replied_to_id="dry_run_id_001",
        dry_run=True,
    )

    print("\n✓ Tracker dry run passed")
