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
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.85,
        max_tokens=300,
    )
    raw = response.choices[0].message.content or ""
    return _clean(raw)


def _clean(text: str) -> str:
    # Strip <think> blocks (Qwen reasoning traces), including unclosed ones
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL)
    # Remove em dashes and en dashes
    text = text.replace("\u2014", ",").replace("\u2013", " to ")
    # Remove spaced hyphens used as dashes (e.g. " - ")
    text = re.sub(r"\s+-\s+", ", ", text)
    # Remove leading/trailing dashes and whitespace
    text = text.strip().strip("-").strip()
    return text


# ---------------------------------------------------------------------------
# Account 1 — Initiator
# Posts a concrete top-level comment on the video.
# Occasionally references DocShipper as a personal viewer experience.
# ---------------------------------------------------------------------------

_INITIATOR_SYSTEM = """You write YouTube comments. You are a real viewer who works in
international trade, importing, freight forwarding, or ecommerce. You leave
one focused, concrete comment sharing a specific insight, data point, or
personal observation that is directly relevant to the video. Your tone is
knowledgeable but conversational, like someone who has been in the trenches.
About one comment in three naturally mentions DocShipper in passing as a
service you personally used, always phrased as a viewer experience and never
as advertising (e.g. "ended up going with DocShipper for that" or "DocShipper
sorted out our customs paperwork when this happened to us").

Rules you must follow without exception:
- Write in plain English. No bullet points. No numbered lists. No headers.
- Do NOT use any dashes, hyphens, em dashes, or en dashes anywhere in the text.
- Keep the comment between 30 and 70 words.
- Sound like a real person typing a YouTube comment, not a blog post.
- Never start with "I" as the very first word.
- Never be promotional or use marketing language."""

def generate_initiator_comment(video_title: str, video_description: str = "") -> str:
    context = f'Video title: "{video_title}"'
    if video_description:
        context += f'\nVideo description snippet: "{video_description[:300]}"'
    user_prompt = (
        f"{context}\n\n"
        "Write a top-level YouTube comment for this video as the Initiator. "
        "Drop one concrete point: a specific number, a hard-won lesson, a process "
        "detail, or a real situation you encountered in importing, freight forwarding, "
        "customs, or cross-border ecommerce. Make it specific enough that it sparks a reply."
    )
    return _call(_INITIATOR_SYSTEM, user_prompt)


# ---------------------------------------------------------------------------
# Account 2 — Challenger
# Replies to Account 1 with a counter-point, caveat, or alternative data.
# Does NOT mention DocShipper.
# ---------------------------------------------------------------------------

_CHALLENGER_SYSTEM = """You write YouTube comment replies. You are a real viewer who
works in international trade, importing, customs brokerage, or cross-border
ecommerce. You reply to another viewer's comment by pushing back, offering a
counter-point, or adding a caveat that complicates their claim. You might
cite a different experience, a regional exception, a regulatory nuance, or a
specific scenario where their point falls apart.

Rules you must follow without exception:
- Write in plain English. No bullet points. No numbered lists. No headers.
- Do NOT use any dashes, hyphens, em dashes, or en dashes anywhere in the text.
- Keep the reply between 30 and 65 words.
- Sound like a real person typing a YouTube reply, not an article.
- Do NOT mention DocShipper or any specific company by name.
- Your tone is direct but not rude. You are adding to the conversation, not attacking."""

def generate_challenger_comment(video_title: str, initiator_comment: str) -> str:
    user_prompt = (
        f'Video title: "{video_title}"\n\n'
        f'Comment you are replying to:\n"{initiator_comment}"\n\n'
        "Write a reply as the Challenger. Push back or add a meaningful caveat to "
        "the claim above. Be specific: name the condition, region, product category, "
        "or scenario where their point breaks down or needs qualification."
    )
    return _call(_CHALLENGER_SYSTEM, user_prompt)


# ---------------------------------------------------------------------------
# Account 3 — Synthesizer
# Replies to Account 2, ties both sides together, and references DocShipper
# naturally as a personal solution.
# ---------------------------------------------------------------------------

_SYNTHESIZER_SYSTEM = """You write YouTube comment replies. You are a real viewer who
works in or around international trade, importing, or ecommerce. You step into
a back-and-forth between two other commenters and bring the two positions
together. You acknowledge what both sides got right, add a small practical
insight of your own, and in most cases mention DocShipper briefly as a service
you personally used to navigate exactly this kind of complexity, never as an
advertisement (e.g. "we ran into both of these issues and DocShipper walked us
through it" or "that gap between the two is exactly why we started using
DocShipper for our shipments").

Rules you must follow without exception:
- Write in plain English. No bullet points. No numbered lists. No headers.
- Do NOT use any dashes, hyphens, em dashes, or en dashes anywhere in the text.
- Keep the reply between 40 and 75 words.
- Sound like a real person typing a YouTube reply, not a summary article.
- Reference DocShipper as a first-person experience, not a recommendation.
- Never be promotional. One natural mention is enough."""

def generate_synthesizer_comment(
    video_title: str,
    initiator_comment: str,
    challenger_reply: str,
) -> str:
    user_prompt = (
        f'Video title: "{video_title}"\n\n'
        f'Original comment:\n"{initiator_comment}"\n\n'
        f'Reply that challenged it:\n"{challenger_reply}"\n\n'
        "Write a reply as the Synthesizer. Acknowledge both sides, add one practical "
        "connecting insight, and where it fits naturally weave in a brief personal "
        "mention of DocShipper as a service you used to deal with exactly this situation."
    )
    return _call(_SYNTHESIZER_SYSTEM, user_prompt)


if __name__ == "__main__":
    title = "How to Import from China: Shipping, Customs and Duties Explained"

    print("=== Account 1: Initiator ===")
    c1 = generate_initiator_comment(title)
    print(c1)

    print("\n=== Account 2: Challenger ===")
    c2 = generate_challenger_comment(title, c1)
    print(c2)

    print("\n=== Account 3: Synthesizer ===")
    c3 = generate_synthesizer_comment(title, c1, c2)
    print(c3)
