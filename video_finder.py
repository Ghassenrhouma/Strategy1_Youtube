import os
import re
import random
import time
from urllib.parse import quote_plus

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from browser_helper import get_browser_context, patch_page, human_scroll

load_dotenv()

SEARCH_QUERIES = [
    # Import / freight intent
    "import from China",
    "freight forwarder",
    "customs clearance",
    "shipping from China to Europe",
    "import duties explained",
    "sourcing from Alibaba",

    # Pain points (high engagement)
    "import problems",
    "customs delay",
    "shipping costs too high",
    "supplier scam China",
    "how to find suppliers China",

    # SME / e-commerce angle
    "dropshipping from China",
    "Amazon FBA sourcing",
    "e-commerce logistics",
    "product sourcing tips",

    # French market
    "importer depuis la Chine",
    "transitaire international",
    "dédouanement France",
    "sourcing Asie",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_english_title(title: str) -> bool:
    if re.search(r"[\u0600-\u06FF]", title):  # Arabic script
        return False
    if re.search(r"[\u4e00-\u9fff]", title):  # Chinese script
        return False
    # Catch Arabic transliteration: digits mixed into uppercase letter runs
    if len(re.findall(r"\b[A-Z]*\d[A-Z]+\b|\b[A-Z]+\d[A-Z]*\b", title)) >= 2:
        return False
    return True


def _is_within_30_days(upload_time: str) -> bool:
    """
    Return True only if the upload time string suggests the video was
    published within approximately the last 30 days.

    YouTube time string examples:
      "3 hours ago", "2 days ago", "1 week ago", "4 weeks ago",
      "1 month ago", "3 months ago", "1 year ago"
    """
    if not upload_time:
        return True  # unknown — give benefit of the doubt

    t = upload_time.lower().strip()

    # Years → definitely not recent
    if re.search(r"\d+\s*(year|years|ans?\b)", t):
        return False

    # Months → not within 30 days (1 month ≈ 30-31 days, YouTube rounds up)
    if re.search(r"\d+\s*(month|months|mois)", t):
        return False

    # Weeks → recent only if <= 4
    week_match = re.search(r"(\d+)\s*(week|weeks|semaine)", t)
    if week_match:
        return int(week_match.group(1)) <= 4

    # Hours, minutes, days → always within 30 days
    return True


def _human_search(page, query: str) -> None:
    """Type query into YouTube search bar with human-like cadence."""
    page.goto("https://www.youtube.com/?hl=en&gl=US")
    page.wait_for_load_state("load")
    time.sleep(random.uniform(2, 5))

    search_selector = None
    for sel in [
        "input#search",
        "input[name='search_query']",
        "#search-input input",
        "ytd-searchbox input",
    ]:
        try:
            page.wait_for_selector(sel, timeout=5000)
            search_selector = sel
            break
        except Exception:
            continue

    if not search_selector:
        page.goto(
            f"https://www.youtube.com/results?search_query={quote_plus(query)}&hl=en&gl=US"
        )
        page.wait_for_load_state("load")
        time.sleep(random.uniform(2, 4))
        return

    page.click(search_selector)
    time.sleep(random.uniform(0.8, 2.0))

    for char in query:
        page.keyboard.type(char)
        time.sleep(random.uniform(0.05, 0.18))
        if random.random() < 0.05:
            time.sleep(random.uniform(0.5, 1.5))

    time.sleep(random.uniform(0.5, 1.5))
    page.keyboard.press("Enter")
    page.wait_for_load_state("load")
    time.sleep(random.uniform(2, 4))


def _scrape_search_results(page, max_results: int = 20) -> list:
    """
    Pull candidate videos from the current YouTube search results page.
    Returns a list of dicts with video_id, title, description, upload_time.
    """
    human_scroll(page)
    candidates = []

    for renderer in page.query_selector_all("ytd-video-renderer"):
        if len(candidates) >= max_results:
            break

        title_el = renderer.query_selector("#video-title")
        if not title_el:
            continue

        href = title_el.get_attribute("href") or ""
        match = re.search(r"v=([a-zA-Z0-9_-]+)", href)
        if not match:
            continue

        video_id = match.group(1)
        title = (title_el.inner_text() or "").strip()

        desc_el = renderer.query_selector("#description-text")
        description = (desc_el.inner_text() if desc_el else "").strip()

        meta_spans = renderer.query_selector_all("#metadata-line span")
        upload_time = meta_spans[1].inner_text().strip() if len(meta_spans) > 1 else ""

        candidates.append({
            "video_id": video_id,
            "title": title,
            "description": description,
            "upload_time": upload_time,
        })

    return candidates



# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_target_video(seen_video_ids: set, page=None) -> dict:
    """
    Search YouTube and return one viable video dict:
        {"video_id": str, "title": str, "description": str}

    Selection criteria:
      - Not in seen_video_ids
      - English title
      - Uploaded within the last 30 days
      - Comments enabled and at least 2 threads visible

    Tries up to 4 randomly-chosen queries before raising RuntimeError.

    Parameters
    ----------
    seen_video_ids : set of video_id strings already used by this bot
    page           : existing Playwright page (optional); if None a new
                     browser session is opened using COOKIES_ACCOUNT1
    """
    def _find(pg):
        tried_queries = set()
        query_pool = SEARCH_QUERIES.copy()
        random.shuffle(query_pool)

        for query in query_pool[:4]:
            if query in tried_queries:
                continue
            tried_queries.add(query)

            print(f"[FINDER] Searching: '{query}'")
            _human_search(pg, query)

            raw_candidates = _scrape_search_results(pg, max_results=20)
            print(f"[FINDER] {len(raw_candidates)} raw results scraped")

            # Pre-filter without loading any video pages
            filtered = [
                c for c in raw_candidates
                if c["video_id"] not in seen_video_ids
                and _is_english_title(c["title"])
                and _is_within_30_days(c["upload_time"])
            ]
            print(f"[FINDER] {len(filtered)} candidates after pre-filter")

            if filtered:
                candidate = filtered[0]
                print(f"[FINDER] Found: {candidate['video_id']} | {candidate['title'][:55]}")
                return {
                    "video_id":    candidate["video_id"],
                    "title":       candidate["title"],
                    "description": candidate["description"],
                }

        raise RuntimeError(
            "No suitable video found after trying 4 queries. "
            "All candidates were either already used or too old."
        )

    if page is not None:
        return _find(page)

    with sync_playwright() as p:
        # Use Account 1 cookies for browsing — read-only, no posting here
        os.environ["COOKIES_PATH"] = os.getenv("COOKIES_ACCOUNT1", "cookies_account1.json")
        context = get_browser_context(p)
        try:
            pg = context.new_page()
            patch_page(pg)
            return _find(pg)
        finally:
            context.close()
