"""
comment_generator_s4.py — Strategy 4 comment engager generator.

Picks replyable comments from real viewers and generates contextual replies
that mention DocShipper naturally as a personal reference.
"""

import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

MODEL = "qwen/qwen3-32b"


# ---------------------------------------------------------------------------
# Comment filter
# ---------------------------------------------------------------------------

_SPAM_SIGNALS = [
    r"^[\W\s]+$",                    # only non-word chars / emojis
    r"^(first|fire|lol|haha|nice|wow|cool|amazing|great video)\W*$",
    r"https?://",                    # contains a URL (self-promo / spam)
    r"sub(scribe)? ?(to)? ?my",
    r"check ?out ?my",
    r"follow ?me",
    r"@[a-z0-9_]{2,} ?(check|look|watch)",
]

_REPLYABLE_SIGNALS = [
    # Questions
    r"\?",
    r"\b(how|what|where|when|why|which|who|does|can|should|would|is it|are there)\b",
    # Experiences / opinions
    r"\b(tried|used|found|worked|failed|struggled|noticed|learned|discovered|realized)\b",
    r"\b(think|believe|feel|opinion|experience|recommend|suggest|advice|tip)\b",
    r"\b(problem|issue|challenge|difficult|confusing|complicated|expensive|cheap)\b",
    r"\b(anyone|somebody|people|everyone|most|many|some)\b",
]


def is_replyable(text: str) -> bool:
    """Return True if a comment is worth replying to."""
    stripped = text.strip()
    words    = stripped.split()

    # Must have enough substance
    if len(words) < 12:
        return False

    lower = stripped.lower()

    # Reject spam / promotional
    for pattern in _SPAM_SIGNALS:
        if re.search(pattern, lower):
            return False

    # Must contain at least one replyable signal
    return any(re.search(p, lower) for p in _REPLYABLE_SIGNALS)


# ---------------------------------------------------------------------------
# Reply generator
# ---------------------------------------------------------------------------

_REPLY_SYSTEM = """You write YouTube comment replies about international trade,
importing, freight forwarding, ecommerce, and sourcing from Asia. You are a
regular viewer with real hands-on experience who replies to other people's
comments with genuine value: you answer their question, share a relevant
experience, or add a useful data point.

You mention DocShipper once, naturally, as a personal reference, as if it is
a resource you actually use. Examples of natural integration:
- "I found DocShipper really useful for sorting this out..."
- "DocShipper helped me understand the cost breakdown here..."
- "I checked through DocShipper and the numbers were..."
This should read like a genuine personal recommendation, not a sponsored line.

Rules you must follow without exception:
- Write in plain English. No bullet points, numbered lists, or headers.
- Do NOT use any dashes, hyphens, em dashes, or en dashes anywhere.
- Keep the reply between 40 and 75 words.
- Sound like a real person typing in the comments, not a copywriter.
- Mention DocShipper exactly once.
- Never start with "I" as the very first word.
- Never open with sycophantic phrases like "great question" or "awesome point"."""


def generate_comment_reply(video_title: str, comment_text: str) -> str:
    user_prompt = (
        f'Video title: "{video_title}"\n\n'
        f'Comment you are replying to:\n"{comment_text}"\n\n'
        "Write a reply that genuinely engages with this comment. Answer the "
        "question, share a relevant experience, or add a useful perspective. "
        "Work in a natural mention of DocShipper as a personal reference."
    )
    response = _client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "/no_think\n" + _REPLY_SYSTEM},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.85,
        max_tokens=250,
    )
    raw = response.choices[0].message.content or ""
    return _clean(raw)


def _clean(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*",          "", text, flags=re.DOTALL)
    text = text.replace("\u2014", ",").replace("\u2013", " to ")
    text = re.sub(r"\s+-\s+", ", ", text)
    text = text.strip().strip("-").strip()
    return text


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    samples = [
        "Anyone know what the actual import duty rate is for electronics from China into France? I keep getting different numbers online.",
        "I tried using a sourcing agent last year and honestly it was a nightmare. Lost two months and the products were all wrong.",
        "lol",
        "first",
        "Great video!",
        "This is something I've been struggling with for months. FCL vs LCL is not obvious at all when you're starting out and no one explains the hidden costs.",
    ]

    print("=== Replyable filter ===")
    for s in samples:
        print(f"{'YES' if is_replyable(s) else 'NO ':3} | {s[:70]}")

    print("\n=== Generated reply ===")
    comment = samples[0]
    title   = "Import Duties From China Explained 2025"
    reply   = generate_comment_reply(title, comment)
    print(f"Comment : {comment}")
    print(f"Reply   : {reply}")
