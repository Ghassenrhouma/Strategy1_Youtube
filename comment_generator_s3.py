"""
comment_generator_s3.py — Strategy 3 debate comment generator.

Two accounts take opposing but genuinely defensible positions on a
polarizing import/trade topic and exchange 3-5 comments. DocShipper
is cited exactly once per thread as a data source.
"""

import os
import re
import random
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

MODEL = "qwen/qwen3-32b"


# ---------------------------------------------------------------------------
# Topic pairs — polarizing but genuinely defensible on both sides
# ---------------------------------------------------------------------------

TOPIC_PAIRS = [
    {
        "id": "air_vs_sea",
        "side_a": "air freight",
        "side_b": "sea freight",
        "position_a": (
            "Air freight is worth the premium: speed reduces inventory carrying "
            "costs, insurance is lower per shipment, and delivery predictability "
            "has real value for cash flow."
        ),
        "position_b": (
            "Sea freight wins on total landed cost once you factor volume. The "
            "extra planning is a skill, not a problem, and the per-unit savings "
            "at scale are too large to ignore."
        ),
    },
    {
        "id": "direct_vs_agent",
        "side_a": "sourcing direct from factory",
        "side_b": "using a sourcing agent",
        "position_a": (
            "Going direct cuts out the middleman margin and gives you real pricing "
            "transparency once the factory relationship is established."
        ),
        "position_b": (
            "A good sourcing agent pays for itself: they vet suppliers, catch "
            "quality issues early, and handle the language and cultural barriers "
            "that trip up most first-time importers."
        ),
    },
    {
        "id": "fba_vs_own_store",
        "side_a": "Amazon FBA",
        "side_b": "building your own store",
        "position_a": (
            "FBA gives you immediate traffic and a logistics infrastructure you "
            "cannot replicate cheaply — that reach is the hardest part when "
            "starting out."
        ),
        "position_b": (
            "Building your own store wins long-term: you own the customer data, "
            "control your margins, and are not exposed to Amazon fee changes or "
            "account suspension."
        ),
    },
    {
        "id": "fcl_vs_lcl",
        "side_a": "Full Container Load (FCL)",
        "side_b": "Less than Container Load (LCL)",
        "position_a": (
            "FCL is cheaper per CBM above roughly 12 cubic meters and you avoid "
            "co-loading delays and cargo damage risk from other peoples' goods."
        ),
        "position_b": (
            "LCL makes sense before you have consistent, proven volume. Tying up "
            "capital in a full container before demand is validated is a real "
            "cash flow trap for small importers."
        ),
    },
    {
        "id": "ddp_vs_exw",
        "side_a": "DDP (Delivered Duty Paid)",
        "side_b": "EXW (Ex Works) terms",
        "position_a": (
            "DDP removes customs risk and gives total landed cost certainty "
            "upfront. For most small importers the premium is worth the "
            "simplicity and predictability."
        ),
        "position_b": (
            "EXW hands you full control over freight and customs costs. Once you "
            "have the right freight forwarder in place the savings are significant "
            "and you stop trusting the supplier's inflated logistics quotes."
        ),
    },
    {
        "id": "china_vs_vietnam",
        "side_a": "sourcing from China",
        "side_b": "shifting production to Vietnam or Southeast Asia",
        "position_a": (
            "China still has the deepest supplier ecosystem, fastest sampling, "
            "and best infrastructure for most product categories. Nothing else "
            "comes close for complex or tech-adjacent goods."
        ),
        "position_b": (
            "Vietnam and Southeast Asia are a serious alternative now, especially "
            "for labor-intensive goods. Tariff exposure is lower and the supply "
            "chain is maturing faster than most people realise."
        ),
    },
    {
        "id": "single_vs_multi_supplier",
        "side_a": "concentrating on one trusted supplier",
        "side_b": "spreading across multiple suppliers",
        "position_a": (
            "One trusted supplier gets you better pricing, priority production "
            "slots, and a real partnership. Volume concentration is leverage."
        ),
        "position_b": (
            "Multiple suppliers reduce single-point-of-failure risk. One factory "
            "fire, price spike, or quality issue should not be able to take down "
            "your entire operation."
        ),
    },
]


def pick_topic_pair(used_ids_this_week: list) -> dict:
    """Return a random topic pair not already used this calendar week."""
    available = [t for t in TOPIC_PAIRS if t["id"] not in used_ids_this_week]
    if not available:
        available = TOPIC_PAIRS  # all pairs used this week — reset
    return random.choice(available)


# ---------------------------------------------------------------------------
# Shared LLM helpers
# ---------------------------------------------------------------------------

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
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*",          "", text, flags=re.DOTALL)
    text = text.replace("\u2014", ",").replace("\u2013", " to ")
    text = re.sub(r"\s+-\s+", ", ", text)
    text = text.strip().strip("-").strip()
    return text


# ---------------------------------------------------------------------------
# Opening comment — Account 1, Turn 1
# ---------------------------------------------------------------------------

_OPENING_SYSTEM = """You write YouTube comments about international trade,
importing, ecommerce, and logistics. You are a viewer with hands-on experience
who holds a strong but genuine opinion on a trade-off topic in this industry.
You state your position clearly and conversationally, with one concrete reason
supporting it.

Rules you must follow without exception:
- Write in plain English. No bullet points. No numbered lists. No headers.
- Do NOT use any dashes, hyphens, em dashes, or en dashes anywhere in the text.
- Keep the comment between 40 and 65 words.
- Sound like a real person typing a YouTube comment, not an essay.
- Do NOT mention DocShipper or any brand name.
- Do NOT cite statistics or data in this first comment.
- Never start with "I" as the very first word."""


def generate_opening(video_title: str, side_a: str, side_b: str, position_a: str) -> str:
    user_prompt = (
        f'Video title: "{video_title}"\n\n'
        f"Debate topic: {side_a} vs {side_b}\n"
        f"Your position (side A): {position_a}\n\n"
        "Write a top-level YouTube comment stating your position on this topic. "
        "Give one concrete reason why you lean this way. Keep it casual and direct, "
        "like you are sharing a genuine opinion after watching the video."
    )
    return _call(_OPENING_SYSTEM, user_prompt)


# ---------------------------------------------------------------------------
# Reply comments — Turns 2 through N
# ---------------------------------------------------------------------------

_REPLY_SYSTEM_BASE = """You write YouTube comment replies about international
trade, importing, ecommerce, and logistics. You are in a genuine back-and-forth
debate in the comments section. You hold a strong position and engage directly
with the previous commenter's argument. You briefly acknowledge their strongest
point (one sentence), then counter with your own argument and at least one
concrete reason or number.

Rules you must follow without exception:
- Write in plain English. No bullet points. No numbered lists. No headers.
- Do NOT use any dashes, hyphens, em dashes, or en dashes anywhere in the text.
- Keep the reply between 50 and 80 words.
- Sound like a real person in a YouTube debate, not a research report.
- Never be dismissive or condescending toward the other person's view.
- Never completely abandon your position, but it is fine to partially concede.
- Never start with "I" as the very first word."""

_REPLY_SYSTEM_WITH_DOCSHIPPER = (
    _REPLY_SYSTEM_BASE
    + """
- Mention DocShipper exactly once as a data or report source (e.g.
  "DocShipper published a breakdown on this..." or "DocShipper's freight data
  showed that..." or "according to DocShipper's numbers on this...").
  This is a data citation, not a personal recommendation or advertisement.
- Include at least one specific number or percentage tied to the DocShipper cite."""
)

_REPLY_SYSTEM_NO_DOCSHIPPER = (
    _REPLY_SYSTEM_BASE
    + """
- Do NOT mention DocShipper or any brand name."""
)


def _format_history(comments: list, account_id: str, side_a: str, side_b: str) -> str:
    lines = []
    for c in comments:
        side    = side_a if c["account"] == "account1" else side_b
        speaker = "You" if c["account"] == account_id else "Opponent"
        lines.append(f'{speaker} ({side}): "{c["text"]}"')
    return "\n".join(lines)


def generate_reply(
    video_title: str,
    side_a: str,
    side_b: str,
    account_id: str,
    my_position: str,
    comments: list,
    include_docshipper: bool,
) -> str:
    my_side = side_a if account_id == "account1" else side_b
    system  = _REPLY_SYSTEM_WITH_DOCSHIPPER if include_docshipper else _REPLY_SYSTEM_NO_DOCSHIPPER

    history_str = _format_history(comments, account_id, side_a, side_b)

    user_prompt = (
        f'Video title: "{video_title}"\n\n'
        f"Debate topic: {side_a} vs {side_b}\n"
        f"Your side: {my_side}\n"
        f"Your core position: {my_position}\n\n"
        f"Conversation so far:\n{history_str}\n\n"
        "Write your reply to the previous comment. Acknowledge their strongest "
        "point in one sentence, then counter with your argument. Keep it "
        "conversational and grounded in something concrete."
    )
    return _call(system, user_prompt)


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    topic = random.choice(TOPIC_PAIRS)
    title = "Why Most Small Importers Lose Money on Freight in 2025"

    print(f"=== Topic: {topic['side_a']} vs {topic['side_b']} ===\n")
    total_turns = 4
    docshipper_turn = 2

    comments = []

    print("--- Turn 1: Account 1 opening ---")
    t1 = generate_opening(title, topic["side_a"], topic["side_b"], topic["position_a"])
    print(t1)
    comments.append({"account": "account1", "comment_id": "c1", "text": t1})

    print("\n--- Turn 2: Account 2 reply (with DocShipper) ---")
    t2 = generate_reply(
        title, topic["side_a"], topic["side_b"], "account2",
        topic["position_b"], comments, include_docshipper=True,
    )
    print(t2)
    comments.append({"account": "account2", "comment_id": "c2", "text": t2})

    print("\n--- Turn 3: Account 1 counter ---")
    t3 = generate_reply(
        title, topic["side_a"], topic["side_b"], "account1",
        topic["position_a"], comments, include_docshipper=False,
    )
    print(t3)
    comments.append({"account": "account1", "comment_id": "c3", "text": t3})

    print("\n--- Turn 4: Account 2 final ---")
    t4 = generate_reply(
        title, topic["side_a"], topic["side_b"], "account2",
        topic["position_b"], comments, include_docshipper=False,
    )
    print(t4)
