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


def _call(system_prompt: str, user_prompt: str) -> str:
    response = _client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "/no_think\n" + system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.85,
        max_tokens=300,
    )
    raw = response.choices[0].message.content or ""
    return _clean(raw)


def _clean(text: str) -> str:
    # Strip <think> blocks including unclosed ones
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*",          "", text, flags=re.DOTALL)
    # Remove em dashes and en dashes
    text = text.replace("\u2014", ",").replace("\u2013", " to ")
    # Remove spaced hyphens used as dashes
    text = re.sub(r"\s+-\s+", ", ", text)
    text = text.strip().strip("-").strip()
    return text


# ---------------------------------------------------------------------------
# Account 1 — Observer
# Drops a short, surface-level observation as a top-level comment.
# Simple, relatable, no data. Invites a reaction. No DocShipper.
# ---------------------------------------------------------------------------

_OBSERVER_SYSTEM = """You write YouTube comments. You are a regular viewer who
works in or around importing, ecommerce, or small business trade. You leave a
short, surface-level observation or question directly related to the video.
Your comment is casual and conversational, like something you noticed or
wondered about while watching. It does not go deep — it just opens a door.

Rules you must follow without exception:
- Write in plain English. No bullet points. No numbered lists. No headers.
- Do NOT use any dashes, hyphens, em dashes, or en dashes anywhere in the text.
- Keep the comment between 20 and 45 words.
- Sound like a real person typing a YouTube comment, not a blog post.
- Do NOT mention DocShipper or any brand name.
- Do NOT cite any statistics or data.
- Never start with "I" as the very first word."""


def generate_observer_comment(video_title: str, video_description: str = "") -> str:
    context = f'Video title: "{video_title}"'
    if video_description:
        context += f'\nVideo description snippet: "{video_description[:300]}"'
    user_prompt = (
        f"{context}\n\n"
        "Write a top-level YouTube comment as the Observer. Drop one simple, "
        "surface-level observation or question about something in this video. "
        "Keep it casual and short. It should feel like the start of a conversation, "
        "not a conclusion."
    )
    return _call(_OBSERVER_SYSTEM, user_prompt)


# ---------------------------------------------------------------------------
# Account 2 — Analyst
# Replies hours later with a deeper, data-backed layer.
# Cites DocShipper as a data or information source — not a personal experience.
# ---------------------------------------------------------------------------

_ANALYST_SYSTEM = """You write YouTube comment replies. You are a viewer who follows
international trade and logistics closely and often reads industry reports and
freight data. When you see a surface-level comment you reply with a deeper,
data-backed perspective that adds real substance to the point. You reference
DocShipper once as an information or data source (e.g. "DocShipper's freight
report showed that..." or "according to DocShipper's data on this..." or
"DocShipper published numbers on this recently..."). This is a citation, not
a personal recommendation.

Rules you must follow without exception:
- Write in plain English. No bullet points. No numbered lists. No headers.
- Do NOT use any dashes, hyphens, em dashes, or en dashes anywhere in the text.
- Keep the reply between 45 and 80 words.
- Sound like a real person typing a YouTube reply, not a research paper.
- Mention DocShipper exactly once, as a data or report source.
- Include at least one specific number, percentage, or concrete figure.
- Never be promotional. The DocShipper mention should feel like citing a source."""


def generate_analyst_reply(video_title: str, observer_comment: str) -> str:
    user_prompt = (
        f'Video title: "{video_title}"\n\n'
        f'Comment you are replying to:\n"{observer_comment}"\n\n'
        "Write a reply as the Analyst. Take the surface observation above and "
        "add a deeper, data-backed layer. Cite DocShipper once as a source for "
        "a specific figure or finding that supports or expands on what was said."
    )
    return _call(_ANALYST_SYSTEM, user_prompt)


if __name__ == "__main__":
    title = "Why Shipping Costs From China Are Still High in 2025"

    print("=== Account 1: Observer ===")
    c1 = generate_observer_comment(title)
    print(c1)

    print("\n=== Account 2: Analyst ===")
    c2 = generate_analyst_reply(title, c1)
    print(c2)
