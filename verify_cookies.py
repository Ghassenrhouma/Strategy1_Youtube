import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()


def verify_cookies() -> bool:
    profile_path = os.getenv("PROFILE_PATH", "profiles/default")

    if not os.path.isdir(profile_path):
        print(f"[FAIL] Profile folder not found: {profile_path} — run login.py first")
        return False

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_path,
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            page = context.new_page()
            page.goto("https://www.youtube.com")
            page.wait_for_load_state("load")

            if page.query_selector("#avatar-btn"):
                print(f"[OK] Profile valid — logged in ({profile_path})")
                return True
            else:
                print(f"[FAIL] Not logged in at {profile_path} — run login.py for this account")
                return False
        finally:
            context.close()


if __name__ == "__main__":
    result = verify_cookies()
    print(result)
