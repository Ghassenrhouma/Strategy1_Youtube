import json
import os
import subprocess
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

BRAVE_EXE = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
BRAVE_USER_DATA = os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "BraveSoftware", "Brave-Browser", "User Data")


def kill_brave():
    """Kill any running Brave processes so Playwright can use the profile."""
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq brave.exe", "/NH"],
        capture_output=True, text=True
    )
    if "brave.exe" in result.stdout:
        print("Closing existing Brave windows to allow Playwright access...")
        subprocess.run(["taskkill", "/F", "/IM", "brave.exe"], capture_output=True)
        time.sleep(2)


def save_cookies():
    account = input("Which account? (1, 2 or 3): ").strip()
    if account not in ("1", "2", "3"):
        print("Invalid choice. Enter 1, 2 or 3.")
        return
    output_file = f"cookies_account{account}.json"

    kill_brave()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=BRAVE_USER_DATA,
            executable_path=BRAVE_EXE,
            headless=False,
        )

        page = context.new_page()
        page.goto("https://www.youtube.com")

        input(f"Switch to account {account}, then press Enter...")

        all_cookies = context.cookies()

        youtube_cookies = [
            c for c in all_cookies
            if any(d in c.get("domain", "") for d in [
                "youtube.com", "google.com", "accounts.google.com", "googlevideo.com"
            ])
        ]

        with open(output_file, "w") as f:
            json.dump(youtube_cookies, f, indent=2)

        print(f"[OK] Saved {len(youtube_cookies)} cookies to {output_file}")
        context.close()


if __name__ == "__main__":
    save_cookies()

