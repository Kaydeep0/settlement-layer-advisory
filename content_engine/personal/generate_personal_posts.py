"""
generate_personal_posts.py — Kiran's personal LinkedIn post generator.

Reads the daily personal sources JSON produced by scan_personal_sources.py
and calls the Anthropic API to generate 5 LinkedIn posts from Kiran's
first-person, analytical, systems-thinker perspective.

Usage:
    python3 generate_personal_posts.py

Output: content_engine/personal/posts/personal_posts_YYYYMMDD.json
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

import anthropic

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ENV_PATH    = "/Users/kiran/GENIUSFLOW_OS/workspace/geniusflow/.env"
SOURCES_DIR = "/Users/kiran/SETTLEMENT_LAYER_ADVISORY/content_engine/personal/sources"
POSTS_DIR   = "/Users/kiran/SETTLEMENT_LAYER_ADVISORY/content_engine/personal/posts"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODEL     = "claude-sonnet-4-6"
MAX_CHARS = 1300

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are writing LinkedIn posts for Kiran Kaur, a CFA with expertise in private credit, "
    "capital markets, and field theory applied to regulatory topology. Kiran is a systems "
    "thinker who connects macro economic shifts to the settlement layer of financial "
    "infrastructure. Voice: first person, direct, analytical, curious. Never pitches "
    "Settlement Layer Advisory directly — only mentions it when genuinely relevant and "
    "naturally. No em dashes. Cite sources always. Max 3 hashtags. Professional but not "
    "corporate. Posts should make the reader think, not just inform. Occasionally end with "
    "a question to drive comments. Maximum 1300 characters."
)

# ---------------------------------------------------------------------------
# Template format strings embedded in each user prompt
# ---------------------------------------------------------------------------
TEMPLATE_A_FORMAT = """\
[STRIKING NUMBER OR FACT on one line]
[2-3 lines of what it means]
[One line: systems level implication]
Source: [Source]"""

TEMPLATE_B_FORMAT = """\
[Observation about market structure or capital cycle]
[Data supporting it]
[What most people miss about this]
[Question or implication]
Source: [Source]"""

TEMPLATE_C_FORMAT = """\
[Surprising or counterintuitive opening line]
[Brief explanation of the mechanism]
[Why this matters right now]
[Question to drive engagement]
Source: [Veritasium or reference]"""

TEMPLATE_D_FORMAT = """\
[What the institution just said or published]
[What it actually means in plain terms]
[Second order effect most analysts miss]
Source: [IMF / Fed / BIS / World Bank]"""

TEMPLATE_E_FORMAT = """\
[Observation about credit markets, private lending, or capital structure]
[Data point from Bloomberg or GS]
[How this connects to where capital is actually flowing]
[Implication for protocols or institutional investors]
Source: [Source]"""

# Visual field values by template
VISUAL_MAP = {
    "A": "stat_card",
    "B": "quote_card",
    "C": "quote_card",
    "D": "stat_card",
    "E": "bar_chart",
    "F": "weekly_wrap",
}

# Post type labels by template
TYPE_MAP = {
    "A": "macro_observation",
    "B": "deep_observation",
    "C": "counterintuitive",
    "D": "central_bank_signal",
    "E": "private_credit",
    "F": "weekly_wrap",
}

# ---------------------------------------------------------------------------
# Env loader
# ---------------------------------------------------------------------------

def load_env(path: str) -> dict:
    """Parse key=value .env file, ignore comments and blank lines."""
    env = {}
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, val = line.partition("=")
                    env[key.strip()] = val.strip()
    except Exception as exc:
        print(f"[WARN] Could not load .env from {path}: {exc}", file=sys.stderr)
    return env


# ---------------------------------------------------------------------------
# Sources loader
# ---------------------------------------------------------------------------

def load_sources(date_str: str) -> dict:
    """Load personal_YYYYMMDD.json from the personal sources directory."""
    path = os.path.join(SOURCES_DIR, f"personal_{date_str}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Sources file not found: {path}\n"
            f"Run scan_personal_sources.py first to generate it."
        )
    with open(path) as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_central_bank_source(article: dict) -> bool:
    """Return True if the article is from IMF, Fed, BIS, or World Bank."""
    source = article.get("source", "").lower()
    title  = article.get("title", "").lower()
    return any(
        kw in source or kw in title
        for kw in ("imf", "federal reserve", "bis", "world bank", "fed ")
    )


def has_veritasium_in_top15(articles: list) -> bool:
    """Return True if Veritasium appears in the top 15 articles list."""
    for art in articles[:15]:
        if art.get("source", "").lower() == "veritasium":
            return True
    return False


def has_central_bank_in_top5(articles: list) -> bool:
    """Return True if an IMF/Fed/BIS/World Bank article is in the top 5."""
    for art in articles[:5]:
        if is_central_bank_source(art):
            return True
    return False


def find_first_central_bank_article(articles: list) -> dict:
    """Return the first central bank article from the top 5, or top article."""
    for art in articles[:5]:
        if is_central_bank_source(art):
            return art
    return articles[0]


def extract_hashtags(text: str, required: list, max_tags: int = 3) -> list:
    """
    Pull hashtags from post text. Ensure required tags are present.
    Cap total at max_tags.
    """
    found = re.findall(r"#\w+", text)
    tag_set = []
    for tag in required:
        if tag not in tag_set:
            tag_set.append(tag)
    for tag in found:
        if tag not in tag_set and len(tag_set) < max_tags:
            tag_set.append(tag)
    return tag_set[:max_tags]


def truncate_post(text: str, limit: int = MAX_CHARS) -> tuple[str, bool]:
    """Truncate post text to limit. Returns (text, was_truncated)."""
    if len(text) <= limit:
        return text, False
    truncated = text[: limit - 3].rsplit("\n", 1)[0] + "..."
    return truncated, True


# ---------------------------------------------------------------------------
# Template F builder (no API call)
# ---------------------------------------------------------------------------

def build_template_f(articles: list, date_display: str) -> str:
    """
    Build the Friday weekly wrap post directly from the top 5 articles.
    No API call. Identifies the most pressing macro/regulatory signal for
    the forward-looking observation.
    """
    top5 = articles[:5]

    lines = ["Five things that moved the field this week."]
    lines.append("")

    for i, art in enumerate(top5, start=1):
        title  = art.get("title", "Untitled").strip()
        source = art.get("source", "Unknown")
        lines.append(f"{i:02d}. {title} ({source})")

    lines.append("")

    # Forward-looking observation: prefer central bank or IMF article
    forward_art = None
    for art in top5:
        if is_central_bank_source(art):
            forward_art = art
            break
    if forward_art is None:
        forward_art = top5[0] if top5 else {}

    fwd_title  = forward_art.get("title", "")
    fwd_source = forward_art.get("source", "")

    # Build a concise forward-looking line from the article title
    fwd_line = (
        f"What I am watching next week: whether {fwd_source} follows through on the "
        f"signals embedded in this week's data. The structural read points toward "
        f"tighter conditions before any easing. Positioning matters."
    )
    # Keep it under the character budget
    if fwd_title:
        fwd_line = (
            f"What I am watching next week: follow-through on the dynamics flagged by "
            f"{fwd_source}. The headline is the surface. The settlement layer beneath "
            f"it is what I am tracking."
        )

    lines.append(fwd_line)
    lines.append("")
    lines.append("#Macro #CapitalMarkets #PrivateCredit")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Fallback post builder (used when API call fails)
# ---------------------------------------------------------------------------

def fallback_post(template: str, article: dict) -> str:
    """Generate a minimal hand-formatted post when the API is unavailable."""
    title   = article.get("title", "Untitled").strip()
    summary = article.get("summary", "").strip()
    source  = article.get("source", "")

    snippet = summary[:280].rstrip()
    if snippet and not snippet.endswith("."):
        snippet += "."

    if template == "A":
        return (
            f"{title}\n\n"
            f"{snippet}\n\n"
            f"The systems-level implication: capital formation and settlement infrastructure "
            f"are being repriced at the same time. That combination is rare.\n\n"
            f"#Macro #CapitalMarkets #FixedIncome\n\n"
            f"Source: {source}"
        )
    elif template == "B":
        return (
            f"What most analysts miss about this shift: the data point on the surface "
            f"is not the signal. The structural change underneath it is.\n\n"
            f"{snippet}\n\n"
            f"The question worth asking: what does this mean for where capital actually "
            f"settles, not just where it trades?\n\n"
            f"#CapitalMarkets #PrivateCredit #Macro\n\n"
            f"Source: {source}"
        )
    elif template == "C":
        return (
            f"The counterintuitive read on this:\n\n"
            f"{snippet}\n\n"
            f"Most frameworks explain the effect. Very few explain the mechanism. "
            f"That gap is where the structural risk lives.\n\n"
            f"Does the second-order effect here get priced in before the next cycle?\n\n"
            f"#SystemsThinking #Macro #CapitalMarkets\n\n"
            f"Source: {source}"
        )
    elif template == "D":
        return (
            f"What this institution just published matters beyond the headline.\n\n"
            f"{snippet}\n\n"
            f"The second-order effect most analysts miss: policy signals of this kind "
            f"move capital allocation frameworks before they move prices.\n\n"
            f"#CentralBank #Macro #FixedIncome\n\n"
            f"Source: {source}"
        )
    elif template == "E":
        return (
            f"A structural shift is visible in the private credit data.\n\n"
            f"{snippet}\n\n"
            f"Capital is not flowing where the headlines suggest. The actual "
            f"re-allocation is slower, more deliberate, and concentrated in a narrower "
            f"band of structures than most models assume.\n\n"
            f"#PrivateCredit #CapitalStructure #Macro\n\n"
            f"Source: {source}"
        )
    else:
        return (
            f"{title}\n\n"
            f"{snippet}\n\n"
            f"Source: {source}"
        )


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------

def call_api(client: anthropic.Anthropic, user_prompt: str) -> str:
    """Call the Anthropic API and return the generated post text."""
    message = client.messages.create(
        model=MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": user_prompt}],
        system=SYSTEM_PROMPT,
    )
    return message.content[0].text.strip()


# ---------------------------------------------------------------------------
# User prompt builders
# ---------------------------------------------------------------------------

def build_prompt_a(article: dict) -> str:
    title   = article.get("title", "")
    summary = article.get("summary", "")
    source  = article.get("source", "")
    url     = article.get("url", "")

    return f"""Write a LinkedIn post using TEMPLATE A for Kiran Kaur's personal profile.

SOURCE MATERIAL:
TITLE: {title}
SUMMARY: {summary}
SOURCE: {source}
URL: {url}

TEMPLATE A format (Macro data, 150-800 chars):
{TEMPLATE_A_FORMAT}

POST RULES:
- First person voice ("I", "my", "we" sparingly)
- Maximum 1300 characters
- No em dashes
- Max 3 hashtags — choose from #Macro #FixedIncome #RWA #CapitalMarkets #PrivateCredit #MonetaryPolicy
- Cite the source at the end
- Do not pitch Settlement Layer Advisory unless directly relevant
- Lead with the striking number or fact on its own line"""


def build_prompt_b(article: dict) -> str:
    title   = article.get("title", "")
    summary = article.get("summary", "")
    source  = article.get("source", "")
    url     = article.get("url", "")

    return f"""Write a LinkedIn post using TEMPLATE B for Kiran Kaur's personal profile.

SOURCE MATERIAL:
TITLE: {title}
SUMMARY: {summary}
SOURCE: {source}
URL: {url}

TEMPLATE B format (Deep observation, 400-800 chars):
{TEMPLATE_B_FORMAT}

POST RULES:
- First person voice
- Maximum 1300 characters
- No em dashes
- Max 3 hashtags
- End with a question to drive engagement
- Cite the source at the end"""


def build_prompt_c(article: dict) -> str:
    title   = article.get("title", "")
    summary = article.get("summary", "")
    source  = article.get("source", "")
    url     = article.get("url", "")

    return f"""Write a LinkedIn post using TEMPLATE C for Kiran Kaur's personal profile.

SOURCE MATERIAL:
TITLE: {title}
SUMMARY: {summary}
SOURCE: {source}
URL: {url}

TEMPLATE C format (Counterintuitive/Veritasium style, 300-700 chars):
{TEMPLATE_C_FORMAT}

POST RULES:
- First person voice
- Open with a genuinely surprising or counterintuitive line
- Explain the mechanism, not just the effect
- Maximum 1300 characters
- No em dashes
- Max 3 hashtags — choose from #SystemsThinking #Macro #CapitalMarkets #Science
- End with a question to drive engagement
- Cite the source at the end"""


def build_prompt_d(article: dict) -> str:
    title   = article.get("title", "")
    summary = article.get("summary", "")
    source  = article.get("source", "")
    url     = article.get("url", "")

    return f"""Write a LinkedIn post using TEMPLATE D for Kiran Kaur's personal profile.

SOURCE MATERIAL:
TITLE: {title}
SUMMARY: {summary}
SOURCE: {source}
URL: {url}

TEMPLATE D format (Central bank signal, 300-800 chars):
{TEMPLATE_D_FORMAT}

POST RULES:
- First person voice
- Translate institutional language into plain terms
- Surface the second-order effect most analysts miss
- Maximum 1300 characters
- No em dashes
- Max 3 hashtags — choose from #CentralBank #MonetaryPolicy #Macro #FixedIncome
- Cite the source (IMF / Fed / BIS / World Bank) at the end"""


def build_prompt_e(article: dict) -> str:
    title   = article.get("title", "")
    summary = article.get("summary", "")
    source  = article.get("source", "")
    url     = article.get("url", "")

    return f"""Write a LinkedIn post using TEMPLATE E for Kiran Kaur's personal profile.

SOURCE MATERIAL:
TITLE: {title}
SUMMARY: {summary}
SOURCE: {source}
URL: {url}

TEMPLATE E format (Private credit/capital structure, 400-900 chars):
{TEMPLATE_E_FORMAT}

POST RULES:
- First person voice
- Root the post in a specific data point (Bloomberg, GS, JPMorgan if available in source)
- Connect to where capital is actually flowing, not where it is reported to flow
- Maximum 1300 characters
- No em dashes
- Max 3 hashtags — choose from #PrivateCredit #CapitalStructure #Macro #FixedIncome #AlternativeCredit
- Cite the source at the end"""


PROMPT_BUILDERS = {
    "A": build_prompt_a,
    "B": build_prompt_b,
    "C": build_prompt_c,
    "D": build_prompt_d,
    "E": build_prompt_e,
}


# ---------------------------------------------------------------------------
# Post plan builder
# ---------------------------------------------------------------------------

def build_post_plan(articles: list, watch_list: dict, is_friday: bool) -> list:
    """
    Determine template and article for each of the 5 daily post slots.

    Slot rules:
    - Post 1 (08:30): Template A — top article
    - Post 2 (12:00): Template B or D — D if central bank in top 5
    - Post 3 (15:00): Template C if Veritasium in top 15, else Template E
    - Post 4 (18:00): Template E — private credit/capital structure
    - Post 5 (21:00 Friday): Template F — weekly wrap (built in code, no API)
               (other days): Template A from 5th-best article
    """
    # Pad articles to at least 5
    placeholder = {
        "title":   "Macro Market Update",
        "summary": "Ongoing developments across capital markets, monetary policy, and credit.",
        "source":  "Bloomberg Markets",
        "url":     "",
    }
    padded = list(articles)
    while len(padded) < 5:
        padded.append(placeholder)

    plan = []

    # Post 1: Template A — top article
    plan.append({
        "slot":        1,
        "template":    "A",
        "article_idx": 0,
        "best_time":   "08:30",
    })

    # Post 2: Template D (central bank in top 5) else Template B
    if has_central_bank_in_top5(padded):
        cb_article = find_first_central_bank_article(padded)
        cb_idx     = next(
            (i for i, a in enumerate(padded) if a is cb_article),
            1,
        )
        plan.append({
            "slot":        2,
            "template":    "D",
            "article_idx": cb_idx,
            "best_time":   "12:00",
        })
    else:
        plan.append({
            "slot":        2,
            "template":    "B",
            "article_idx": 1,
            "best_time":   "12:00",
        })

    # Post 3: Template C if Veritasium in top 15 else Template E
    if has_veritasium_in_top15(padded):
        verit_idx = next(
            (i for i, a in enumerate(padded[:15]) if a.get("source", "") == "Veritasium"),
            2,
        )
        plan.append({
            "slot":        3,
            "template":    "C",
            "article_idx": verit_idx,
            "best_time":   "15:00",
        })
    else:
        plan.append({
            "slot":        3,
            "template":    "E",
            "article_idx": 2,
            "best_time":   "15:00",
        })

    # Post 4: Template E — private credit / capital structure angle
    plan.append({
        "slot":        4,
        "template":    "E",
        "article_idx": 3,
        "best_time":   "18:00",
    })

    # Post 5: Template F on Fridays, else Template A from 5th article
    if is_friday:
        plan.append({
            "slot":        5,
            "template":    "F",
            "article_idx": None,  # built in code from all top 5
            "best_time":   "21:00",
        })
    else:
        plan.append({
            "slot":        5,
            "template":    "A",
            "article_idx": 4,
            "best_time":   "08:30",
        })

    return plan


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    now          = datetime.now(tz=timezone.utc)
    date_str     = now.strftime("%Y%m%d")
    date_display = now.strftime("%Y-%m-%d")
    generated_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    is_friday    = now.weekday() == 4  # Monday=0

    print(f"=== Kiran Personal Post Generator — {date_display} ===")
    print(f"  Friday: {is_friday}")

    # Load env
    env     = load_env(ENV_PATH)
    api_key = env.get("ANTHROPIC_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key
        print("  ANTHROPIC_API_KEY loaded.")
    else:
        print("[WARN] ANTHROPIC_API_KEY not found. API calls will fall back.", file=sys.stderr)

    # Load today's personal sources
    print(f"\nLoading sources for {date_str}...")
    try:
        sources = load_sources(date_str)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    articles   = sources.get("articles", [])
    watch_list = sources.get("watch_list", {})

    print(f"  Articles loaded: {len(articles)}")
    print(f"  Watch-list flags: {watch_list}")

    if not articles:
        print("[ERROR] No articles found in sources file. Run scan_personal_sources.py.", file=sys.stderr)
        sys.exit(1)

    # Build post plan
    plan = build_post_plan(articles, watch_list, is_friday)

    # Initialise Anthropic client
    client = anthropic.Anthropic(api_key=api_key) if api_key else None

    # Ensure posts directory exists
    os.makedirs(POSTS_DIR, exist_ok=True)

    posts = []

    for slot_info in plan:
        slot        = slot_info["slot"]
        template    = slot_info["template"]
        article_idx = slot_info["article_idx"]
        best_time   = slot_info["best_time"]
        post_type   = TYPE_MAP.get(template, "post")

        article = (
            articles[article_idx]
            if article_idx is not None and article_idx < len(articles)
            else {}
        )
        source_name = article.get("source", "")

        print(f"\n[Post {slot}] Template {template} — {post_type} — {best_time}")

        # ----------------------------------------------------------------
        # Template F: build in code, no API call
        # ----------------------------------------------------------------
        if template == "F":
            print("  Building weekly wrap in code (no API call)...")
            post_text = build_template_f(articles, date_display)
            hashtags  = extract_hashtags(post_text, ["#Macro", "#CapitalMarkets"], 3)
            source_label = "Multiple sources"

        # ----------------------------------------------------------------
        # All other templates: call the API
        # ----------------------------------------------------------------
        else:
            prompt_builder = PROMPT_BUILDERS.get(template)
            if prompt_builder is None:
                print(f"  [WARN] No prompt builder for template {template}. Skipping.", file=sys.stderr)
                continue

            user_prompt = prompt_builder(article)

            if client:
                try:
                    print(f"  Calling API (model={MODEL})...")
                    post_text = call_api(client, user_prompt)
                    print(f"  API call successful. ({len(post_text)} chars)")
                except Exception as exc:
                    print(f"  [WARN] API call failed: {exc}. Using fallback.", file=sys.stderr)
                    post_text = fallback_post(template, article)
            else:
                print("  [WARN] No API client — using fallback template.", file=sys.stderr)
                post_text = fallback_post(template, article)

            required_tags = {
                "A": ["#Macro", "#FixedIncome"],
                "B": ["#CapitalMarkets", "#Macro"],
                "C": ["#SystemsThinking", "#Macro"],
                "D": ["#MonetaryPolicy", "#Macro"],
                "E": ["#PrivateCredit", "#CapitalMarkets"],
            }.get(template, ["#Macro"])

            hashtags     = extract_hashtags(post_text, required_tags, 3)
            source_label = source_name

        # Enforce character limit
        post_text, was_truncated = truncate_post(post_text, MAX_CHARS)
        if was_truncated:
            print(f"  [INFO] Post truncated to {MAX_CHARS} chars.")

        char_count = len(post_text)
        print(f"  Character count: {char_count}")

        posts.append({
            "id":              slot,
            "template":        template,
            "type":            post_type,
            "post_text":       post_text,
            "hashtags":        hashtags,
            "source":          source_label,
            "visual":          VISUAL_MAP.get(template, "stat_card"),
            "best_time":       best_time,
            "character_count": char_count,
        })

    # Build output payload
    output = {
        "date":         date_display,
        "generated_at": generated_at,
        "model":        MODEL,
        "posts":        posts,
    }

    # Write output
    output_path = os.path.join(POSTS_DIR, f"personal_posts_{date_str}.json")
    with open(output_path, "w") as fh:
        json.dump(output, fh, indent=2)

    print(f"\n=== Done ===")
    print(f"  Posts written: {len(posts)}")
    print(f"  Output: {output_path}")
    print()
    for post in posts:
        print(
            f"  [{post['best_time']}] Post {post['id']} "
            f"(Template {post['template']}) — {post['character_count']} chars — {post['type']}"
        )


if __name__ == "__main__":
    main()
