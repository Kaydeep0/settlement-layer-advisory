"""
generate_posts.py — Settlement Layer Advisory daily LinkedIn post generator.

Reads the daily sources JSON produced by scan_sources.py and calls the
Anthropic API to generate LinkedIn posts for the brand page.

Usage:
    python3 generate_posts.py

Output: content_engine/posts/posts_YYYYMMDD.json
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
ENV_PATH = "/Users/kiran/GENIUSFLOW_OS/workspace/geniusflow/.env"
SOURCES_DIR = "/Users/kiran/SETTLEMENT_LAYER_ADVISORY/content_engine/sources"
POSTS_DIR = "/Users/kiran/SETTLEMENT_LAYER_ADVISORY/content_engine/posts"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODEL = "claude-sonnet-4-6"
MAX_CHARS = 1300

SYSTEM_PROMPT = (
    "You are a LinkedIn content writer for Settlement Layer Advisory, a licensed RWA compliance firm. "
    "You write sharp, specific, data-driven posts about regulatory developments in the tokenized asset "
    "and RWA space. You never pitch. You never use em dashes. You cite sources. You write in a "
    "professional but direct tone. Every post demonstrates expertise without claiming it. "
    "Maximum 1300 characters per post. Max 3 hashtags. No emojis except one warning symbol if "
    "genuinely urgent. Never mention Series 7 or Series 66 by name — use \"licensed professionals\" "
    "instead. One sentence maximum about Settlement Layer Advisory per post."
)

# ---------------------------------------------------------------------------
# Template text embedded in prompts
# ---------------------------------------------------------------------------
TEMPLATE_A_FORMAT = """\
[SHARP ONE LINE HEADLINE WITH NUMBER OR FACT]
[2-3 lines of context from article]
[One line: what this means for RWA protocols]
[Optional: one line connecting to Settlement Layer Advisory]
Source: [Source name]"""

TEMPLATE_B_FORMAT = """\
[STRIKING NUMBER OR STAT]
[What it means in 2-3 lines]
[One line: settlement layer implication]
Source: [Source name]"""

TEMPLATE_D_FORMAT = """\
Under [specific rule], [specific requirement].
Most RWA protocols [specific gap].
[What happens if this gap exists].
Settlement Layer Advisory closes this gap. [Specific service]."""

TEMPLATE_E_FORMAT = """\
[Pattern observed across sources]
[Data point 1]
[Data point 2]
[Data point 3]
[What this pattern means for the tokenized settlement layer]
Source: [Multiple sources listed]"""

VISUAL_MAP = {
    "A": "regulatory_card",
    "B": "stat_card",
    "C": "signal_chart",
    "D": "quote_card",
    "E": "trend_card",
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
    """Load daily_YYYYMMDD.json from sources directory."""
    path = os.path.join(SOURCES_DIR, f"daily_{date_str}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Sources file not found: {path}\n"
            f"Run scan_sources.py first to generate it."
        )
    with open(path) as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Template C formatter (no API call)
# ---------------------------------------------------------------------------

def format_template_c(
    engine_readings: dict,
    helix_block: int,
    date_display: str,
    wfp_score: float = None,
    observer_city: str = "Walnut Creek CA",
    entity_city: str = "Washington DC",
) -> str:
    """
    Format the engine signal post directly from structured data.
    Avoids API cost since the data is already structured.

    wfp_score: WFP v2.1 verification confidence (0-1). If provided, appended
               as a verification line so readers can assess observation quality.
    """
    lines = [f"Eigenstate Research field readings, {date_display}."]
    lines.append("")

    # Find the longest entity name for alignment
    max_len = max(len(e) for e in engine_readings) if engine_readings else 10

    # Find highest reading to reference in closing line
    highest_entity = None
    highest_phi = -1.0
    for entity, data in engine_readings.items():
        phi = float(data.get("phi_s", 0))
        status = data.get("status", "STABLE")
        padding = " " * (max_len - len(entity))
        lines.append(f"{entity}{padding}  Phi_S = {phi:.2f}  {status}")
        if phi > highest_phi:
            highest_phi = phi
            highest_entity = entity

    lines.append("")
    lines.append(
        f"Every observation committed to Base mainnet before publication. Block {helix_block}."
    )

    # WFP verification confidence line
    if wfp_score is not None:
        lines.append(
            f"Verification confidence (WFP): {wfp_score:.0%}"
        )
        lines.append(
            f"Anchor: {observer_city} observing {entity_city} jurisdiction"
        )

    # Closing sentence about the highest reading
    if highest_entity:
        lines.append("")
        if highest_phi >= 2.5:
            lines.append(
                f"{highest_entity} at Phi_S {highest_phi:.2f} signals elevated settlement risk "
                f"for protocols building in this topology. Monitor before deployment."
            )
        elif highest_phi >= 1.5:
            lines.append(
                f"{highest_entity} at Phi_S {highest_phi:.2f}: protocols operating in this topology "
                f"should review their compliance posture before the next settlement cycle."
            )
        else:
            lines.append(
                f"Field readings remain stable. Settlement protocols can proceed with standard "
                f"compliance review cadence."
            )

    lines.append("")
    lines.append("Source: Eigenstate Research")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# API call helpers
# ---------------------------------------------------------------------------

def build_engine_readings_block(engine_readings: dict) -> str:
    """Format engine readings as a compact block for embedding in prompts."""
    max_len = max(len(e) for e in engine_readings) if engine_readings else 10
    rows = []
    for entity, data in engine_readings.items():
        phi = float(data.get("phi_s", 0))
        status = data.get("status", "STABLE")
        padding = " " * (max_len - len(entity))
        rows.append(f"{entity}{padding}  Phi_S = {phi:.2f}  {status}")
    return "\n".join(rows)


def build_user_prompt(
    template: str,
    article: dict,
    engine_readings: dict,
    helix_block: int,
    date_display: str,
    template_format: str,
    extra_articles: list = None,
) -> str:
    """Build the user prompt for a single post."""
    title = article.get("title", "")
    summary = article.get("summary", "")
    source = article.get("source", "")
    url = article.get("url", "")

    readings_block = build_engine_readings_block(engine_readings)

    # For Template E, include multiple source titles if available
    if template == "E" and extra_articles:
        source_material_lines = ["Multiple sources:\n"]
        for art in [article] + extra_articles[:2]:
            source_material_lines.append(
                f"  TITLE: {art.get('title', '')}\n"
                f"  SUMMARY: {art.get('summary', '')}\n"
                f"  SOURCE: {art.get('source', '')}\n"
                f"  URL: {art.get('url', '')}"
            )
        source_material = "\n".join(source_material_lines)
    else:
        source_material = (
            f"TITLE: {title}\n"
            f"SUMMARY: {summary}\n"
            f"SOURCE: {source}\n"
            f"URL: {url}"
        )

    prompt = f"""Write a LinkedIn post using TEMPLATE {template} about this source material:

{source_material}

Engine readings today:
{readings_block}

Helix block: {helix_block}

TEMPLATE {template} format:
{template_format}

POST RULES:
- Maximum 1300 characters
- No em dashes
- Max 3 hashtags: always #RWA #TokenizedAssets and one topic-specific
- No emojis unless genuinely urgent
- End with: Source: {source if template != "E" else "[Multiple sources listed]"}
- Engine signal posts include block number
- Never pitch directly. One sentence max about Settlement Layer Advisory."""

    return prompt


def call_api(client: anthropic.Anthropic, user_prompt: str) -> str:
    """Call the Anthropic API and return the text response."""
    message = client.messages.create(
        model=MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": user_prompt}],
        system=SYSTEM_PROMPT,
    )
    return message.content[0].text.strip()


def fallback_post(template: str, article: dict) -> str:
    """Generate a minimal fallback post when the API fails."""
    title = article.get("title", "Untitled")
    summary = article.get("summary", "")
    source = article.get("source", "")
    url = article.get("url", "")

    if template == "A":
        return (
            f"{title}\n\n"
            f"{summary[:300]}\n\n"
            f"This development has direct implications for RWA protocol compliance teams.\n\n"
            f"#RWA #TokenizedAssets #Compliance\n\n"
            f"Source: {source}"
        )
    elif template == "B":
        return (
            f"{title}\n\n"
            f"{summary[:300]}\n\n"
            f"Settlement layer teams should review exposure.\n\n"
            f"#RWA #TokenizedAssets #Compliance\n\n"
            f"Source: {source}"
        )
    elif template == "D":
        return (
            f"Compliance reminder: review your current regulatory posture.\n\n"
            f"{summary[:300]}\n\n"
            f"Settlement Layer Advisory works with licensed professionals to close these gaps.\n\n"
            f"#RWA #TokenizedAssets #Compliance\n\n"
            f"Source: {source}"
        )
    elif template == "E":
        return (
            f"A pattern is emerging across regulatory channels.\n\n"
            f"{summary[:300]}\n\n"
            f"The tokenized settlement layer is adapting.\n\n"
            f"#RWA #TokenizedAssets #Compliance\n\n"
            f"Source: {source}"
        )
    else:
        return (
            f"{title}\n\n{summary[:300]}\n\nSource: {source}"
        )


# ---------------------------------------------------------------------------
# Post plan builder
# ---------------------------------------------------------------------------

def is_regulatory_source(article: dict) -> bool:
    source = article.get("source", "").lower()
    title = article.get("title", "").lower()
    summary = article.get("summary", "").lower()
    return (
        "sec" in source or "cftc" in source
        or "sec" in title or "cftc" in title
        or "sec" in summary or "cftc" in summary
    )


def build_post_plan(articles: list, date_display: str) -> list:
    """
    Determine which template and article to use for each post slot.
    Returns list of dicts: {slot, template, article_idx, best_time, type}
    """
    # Parse weekday from date_display (YYYY-MM-DD)
    try:
        dt = datetime.strptime(date_display, "%Y-%m-%d")
        is_tuesday = dt.weekday() == 1  # Monday=0, Tuesday=1
    except Exception:
        is_tuesday = False

    # Pad articles list if fewer than 5
    while len(articles) < 5:
        articles.append({
            "title": "RWA Market Update",
            "summary": "Ongoing developments in the tokenized asset and real world asset space.",
            "source": "Eigenstate Research",
            "url": "",
        })

    plan = []

    # Post 1: Template C — engine signal (always, no article needed)
    plan.append({
        "slot": 1,
        "template": "C",
        "article_idx": None,
        "best_time": "08:00",
        "type": "engine_signal",
    })

    # Post 2: Template A (if regulatory) or Template E
    template_2 = "A" if is_regulatory_source(articles[0]) else "E"
    plan.append({
        "slot": 2,
        "template": template_2,
        "article_idx": 0,
        "best_time": "11:00",
        "type": "regulatory" if template_2 == "A" else "trend",
    })

    # Post 3: Template B or A
    template_3 = "B" if not is_regulatory_source(articles[1]) else "A"
    plan.append({
        "slot": 3,
        "template": template_3,
        "article_idx": 1,
        "best_time": "13:00",
        "type": "market_data" if template_3 == "B" else "regulatory",
    })

    # Post 4: Template D on Tuesday, else Template A
    template_4 = "D" if is_tuesday else "A"
    plan.append({
        "slot": 4,
        "template": template_4,
        "article_idx": 2,
        "best_time": "16:00",
        "type": "compliance_reminder" if template_4 == "D" else "regulatory",
    })

    # Post 5: Template E or B
    template_5 = "E" if len(articles) >= 3 else "B"
    plan.append({
        "slot": 5,
        "template": template_5,
        "article_idx": 3,
        "best_time": "19:00",
        "type": "trend" if template_5 == "E" else "market_data",
    })

    return plan


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    now = datetime.now(tz=timezone.utc)
    date_str = now.strftime("%Y%m%d")
    date_display = now.strftime("%Y-%m-%d")
    generated_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"=== Settlement Layer Advisory — Post Generator {date_display} ===")

    # Load env
    env = load_env(ENV_PATH)
    api_key = env.get("ANTHROPIC_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key
        print("  ANTHROPIC_API_KEY loaded.")
    else:
        print("[WARN] ANTHROPIC_API_KEY not found. API calls will fail.", file=sys.stderr)

    # Load today's sources
    print(f"\nLoading sources for {date_str}...")
    try:
        sources = load_sources(date_str)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    articles = sources.get("articles", [])
    engine_readings = sources.get("engine_readings", {})
    helix_block = sources.get("helix_block", 44882914)

    # Load WFP score from entity_readings.json if available
    _wfp_score = None
    try:
        import json as _json
        _er_path = os.path.join(os.path.dirname(__file__), "entity_readings.json")
        if os.path.isfile(_er_path):
            _er = _json.loads(open(_er_path).read())
            _wfp_score = _er.get("wfp_score")
    except Exception:
        pass

    print(f"  Articles loaded: {len(articles)}")
    print(f"  Engine entities: {len(engine_readings)}")
    print(f"  Helix block: {helix_block}")
    if _wfp_score is not None:
        print(f"  WFP score: {_wfp_score:.1%}")

    # Build post plan
    plan = build_post_plan(list(articles), date_display)

    # Initialise API client
    client = anthropic.Anthropic(api_key=api_key) if api_key else None

    # Generate posts
    os.makedirs(POSTS_DIR, exist_ok=True)
    posts = []

    for slot_info in plan:
        slot = slot_info["slot"]
        template = slot_info["template"]
        article_idx = slot_info["article_idx"]
        best_time = slot_info["best_time"]
        post_type = slot_info["type"]

        article = articles[article_idx] if article_idx is not None and article_idx < len(articles) else {}
        source_name = article.get("source", "Eigenstate Research")

        print(f"\n[Post {slot}] Template {template} — {post_type} — {best_time}")

        # Template C: format directly, no API call
        if template == "C":
            print("  Formatting engine signal post (no API call)...")
            post_text = format_template_c(
                engine_readings, helix_block, date_display,
                wfp_score=_wfp_score,
            )
            hashtags = ["#RWA", "#TokenizedAssets", "#Compliance"]
            source_label = "Eigenstate Research"

        else:
            # Determine template format string
            template_formats = {
                "A": TEMPLATE_A_FORMAT,
                "B": TEMPLATE_B_FORMAT,
                "D": TEMPLATE_D_FORMAT,
                "E": TEMPLATE_E_FORMAT,
            }
            template_format = template_formats.get(template, TEMPLATE_A_FORMAT)

            # For Template E, pass extra articles for multi-source context
            extra_articles = []
            if template == "E" and len(articles) > article_idx + 1:
                extra_articles = articles[article_idx + 1: article_idx + 3]

            user_prompt = build_user_prompt(
                template=template,
                article=article,
                engine_readings=engine_readings,
                helix_block=helix_block,
                date_display=date_display,
                template_format=template_format,
                extra_articles=extra_articles if template == "E" else None,
            )

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

            # Extract hashtags from post text (pull any #word tokens)
            found_tags = re.findall(r"#\w+", post_text)
            # Ensure required tags are present, cap at 3
            required = ["#RWA", "#TokenizedAssets"]
            tag_set = []
            for tag in required:
                if tag not in tag_set:
                    tag_set.append(tag)
            for tag in found_tags:
                if tag not in tag_set and len(tag_set) < 3:
                    tag_set.append(tag)
            hashtags = tag_set[:3]

            source_label = source_name

        # Enforce character limit — truncate gracefully if needed
        if len(post_text) > MAX_CHARS:
            post_text = post_text[:MAX_CHARS - 3].rsplit("\n", 1)[0] + "..."
            print(f"  [INFO] Post truncated to {MAX_CHARS} chars.")

        char_count = len(post_text)
        print(f"  Character count: {char_count}")

        posts.append({
            "id": slot,
            "template": template,
            "type": post_type,
            "post_text": post_text,
            "hashtags": hashtags,
            "source": source_label,
            "visual": VISUAL_MAP.get(template, "regulatory_card"),
            "best_time": best_time,
            "character_count": char_count,
        })

    # Build output payload
    output = {
        "date": date_display,
        "generated_at": generated_at,
        "model": MODEL,
        "posts": posts,
    }

    # Write output
    output_path = os.path.join(POSTS_DIR, f"posts_{date_str}.json")
    with open(output_path, "w") as fh:
        json.dump(output, fh, indent=2)

    print(f"\n=== Done ===")
    print(f"  Posts written: {len(posts)}")
    print(f"  Output: {output_path}")
    print()
    for post in posts:
        print(f"  [{post['best_time']}] Post {post['id']} (Template {post['template']}) — {post['character_count']} chars — {post['type']}")


if __name__ == "__main__":
    main()
