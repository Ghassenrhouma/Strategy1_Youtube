"""
test_comment_selectors.py — Live browser test for comment loading & posting.

Skips all watch-time / video behaviour so it runs fast.
Uses real cookies and a real video but does NOT post anything (DRY_RUN=True).

Usage:
    python test_comment_selectors.py
"""

import os
import sys
import time
import random
from dotenv import load_dotenv

_HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_HERE, ".env"))

os.environ["DRY_RUN"]     = "True"
os.environ["SKIP_DELAYS"] = "True"
os.environ["HEADLESS"]    = os.environ.get("HEADLESS", "False")   # visible by default
os.environ["COOKIES_PATH"] = os.environ.get("COOKIES_ACCOUNT2", "cookies_account2.json")

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from browser_helper import get_browser_context, patch_page, human_scroll

# ── target video ──────────────────────────────────────────────────────────────
import json
with open(os.path.join(_HERE, "targets.json")) as _f:
    _targets = json.load(_f)["targets"]
VIDEO_ID = _targets[0]["video_id"] if _targets else "PSWiWOoOF_Q"

# ── helpers ───────────────────────────────────────────────────────────────────
_PASS = 0
_FAIL = 0

def _check(condition: bool, label: str) -> None:
    global _PASS, _FAIL
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}")
    if condition:
        _PASS += 1
    else:
        _FAIL += 1


def _wait_for_load(page, timeout=10000):
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
    except PlaywrightTimeoutError:
        pass


# ── test ──────────────────────────────────────────────────────────────────────
def run():
    print(f"\n=== Comment selector test | video: {VIDEO_ID} ===\n")

    with sync_playwright() as p:
        context = get_browser_context(p)
        page = context.new_page()
        patch_page(page)

        # Navigate directly — no watch time
        print(f"[NAV] Going to https://www.youtube.com/watch?v={VIDEO_ID}")
        page.goto(f"https://www.youtube.com/watch?v={VIDEO_ID}")
        _wait_for_load(page)
        time.sleep(random.uniform(2, 4))

        # Scroll to trigger comment section
        human_scroll(page)

        # Step 1 — comments section container
        print("\n[TEST] Step 1 — wait for comments section container")
        try:
            page.wait_for_selector("#comments ytd-item-section-renderer", timeout=30000)
            _check(True, "#comments ytd-item-section-renderer found")
        except PlaywrightTimeoutError:
            _check(False, "#comments ytd-item-section-renderer NOT found within 30s")
            context.close()
            return

        # Step 2 — switch to Newest first so fresh comments are visible
        print("\n[TEST] Step 2 — switch sort order to Newest first")
        try:
            sort_btn = None
            for sel in [
                "yt-sort-filter-sub-menu-renderer #label",
                "yt-sort-filter-sub-menu-renderer button",
                "#sort-menu",
            ]:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    sort_btn = el
                    break

            if sort_btn:
                sort_btn.click()
                time.sleep(random.uniform(0.8, 1.5))

                # Dump all visible dropdown options for diagnosis
                print("  [INFO] Dropdown options found:")
                for sel in ["tp-yt-paper-item", "yt-menu-service-item-renderer", "ytd-menu-service-item-renderer"]:
                    items = page.query_selector_all(sel)
                    if items:
                        for i, item in enumerate(items):
                            try:
                                txt = (item.inner_text() or "").strip()
                                visible = item.is_visible()
                                print(f"         [{sel}][{i}] visible={visible} text='{txt}'")
                            except Exception:
                                pass

                clicked = False
                for sel in ["tp-yt-paper-item", "yt-menu-service-item-renderer", "ytd-menu-service-item-renderer"]:
                    items = [i for i in page.query_selector_all(sel) if i.is_visible()]
                    for item in items:
                        txt = (item.inner_text() or "").lower()
                        if "newest" in txt or "recent" in txt:
                            item.click()
                            clicked = True
                            break
                    if not clicked and len(items) >= 2:
                        # Fallback: second option is always "Newest first"
                        print(f"  [INFO] Falling back to clicking second option in {sel}")
                        items[1].click()
                        clicked = True
                    if clicked:
                        break

                time.sleep(random.uniform(1.5, 2.5))
                _check(clicked, "Switched to Newest first")
            else:
                _check(False, "Sort button not found")
        except Exception as e:
            _check(False, f"Sort failed: {e}")

        # Step 3 — scroll comments section into view to trigger item rendering
        print("\n[TEST] Step 3 — scroll comments into view and wait for items")
        section = page.query_selector("#comments ytd-item-section-renderer")
        if section:
            section.scroll_into_view_if_needed()
            time.sleep(random.uniform(1.0, 2.0))

        COMMENT_SELECTORS = [
            "ytd-comment-thread-renderer",
            "ytd-comment-view-model",
            "ytd-comment-renderer",
            "#contents ytd-comment-thread-renderer",
        ]

        threads = []
        matched_selector = None
        for attempt in range(20):
            for sel in COMMENT_SELECTORS:
                els = page.query_selector_all(sel)
                if els:
                    threads = els
                    matched_selector = sel
                    break
            if threads:
                break
            page.evaluate("window.scrollBy(0, 300)")
            time.sleep(random.uniform(0.8, 1.5))

        # Report all selector counts for diagnosis
        print("  [INFO] Selector counts after scrolling:")
        for sel in COMMENT_SELECTORS:
            n = len(page.query_selector_all(sel))
            print(f"         {sel}: {n}")

        _check(len(threads) > 0, f"Comment elements found via '{matched_selector}' ({len(threads)} items)")

        # Step 4 — comment text readable
        print("\n[TEST] Step 4 — comment text readable")
        texts = []
        for thread in threads[:3]:
            el = thread.query_selector("#content-text")
            if el:
                texts.append((el.inner_text() or "").strip()[:80])
        _check(len(texts) > 0, f"Read text from {len(texts)} item(s)")
        for t in texts:
            print(f"    » {t}")

        # Step 5 — comment box present (not clicking / not posting)
        print("\n[TEST] Step 5 — comment input box present")
        box = page.query_selector("#simplebox-placeholder")
        _check(box is not None, "#simplebox-placeholder found")

        context.close()

    print(f"\n{'='*45}")
    print(f"  Results: {_PASS} passed, {_FAIL} failed")
    print(f"{'='*45}\n")
    sys.exit(0 if _FAIL == 0 else 1)


if __name__ == "__main__":
    run()
