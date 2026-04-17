"""
login.py — First-time login for each account.

Creates a persistent browser profile so all subsequent bot runs maintain
their session state automatically — no cookie files needed.

Usage:
    python login.py
"""

import os
import sys
from playwright.sync_api import sync_playwright

_HERE = os.path.dirname(os.path.abspath(__file__))


def login(account_num: str) -> None:
    profile_dir = os.path.join(_HERE, "profiles", f"account{account_num}")
    os.makedirs(profile_dir, exist_ok=True)

    print(f"\n[LOGIN] Opening browser for account {account_num}")
    print(f"[LOGIN] Profile will be saved to: {profile_dir}")
    print("[LOGIN] Log into YouTube/Google in the browser window.")
    print("[LOGIN] Once you see your avatar (top-right) come back here and press Enter.\n")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--window-size=1280,800",
            ],
        )
        page = context.new_page()
        page.goto("https://www.youtube.com")

        input("[LOGIN] Press Enter once you are fully logged in...")
        context.close()

    print(f"[LOGIN] Profile saved. Account {account_num} is ready.\n")


def main() -> None:
    print("=== YouTube Account Login ===")
    print("Creates a persistent browser profile for one account.\n")

    while True:
        choice = input("Which account? (1, 2, or 3): ").strip()
        if choice in ("1", "2", "3"):
            break
        print("Please enter 1, 2, or 3.")

    login(choice)
    print("Run login.py again for any other accounts you need to set up.")


if __name__ == "__main__":
    main()
