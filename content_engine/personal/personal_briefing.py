#!/usr/bin/env python3
"""Kiran Kaur Personal LinkedIn — Daily Content Briefing Orchestrator"""

import subprocess
import sys
import os
import json
import datetime
import glob

BASE = os.path.dirname(os.path.abspath(__file__))
TODAY = datetime.date.today().strftime("%Y%m%d")
DATE_DISPLAY = datetime.date.today().strftime("%B %d, %Y")

SOURCES_DIR = os.path.join(BASE, "sources")
POSTS_DIR   = os.path.join(BASE, "posts")
VISUALS_DIR = os.path.join(BASE, "visuals")

# Watch-list authors — flagged if they appear in sources
WATCH_LIST = [
    "Howard Marks",
    "Lyn Alden",
    "Veritasium",
    "IMF",
    "Federal Reserve speeches",
]


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

def run_step(label, script):
    """Run a pipeline step, print output, return success bool."""
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    result = subprocess.run(
        [sys.executable, script],
        cwd=BASE,
        capture_output=False  # let output flow through
    )
    if result.returncode != 0:
        print(f"[ERROR] {label} exited with code {result.returncode}")
        return False
    return True


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def load_sources():
    """Load today's personal sources JSON. Returns (data, error_str)."""
    path = os.path.join(SOURCES_DIR, f"personal_{TODAY}.json")
    if not os.path.exists(path):
        matches = glob.glob(os.path.join(SOURCES_DIR, f"*{TODAY}*.json"))
        if matches:
            path = sorted(matches)[-1]
        else:
            return None, f"personal sources file not found: {path}"
    try:
        with open(path) as f:
            return json.load(f), None
    except Exception as e:
        return None, f"personal sources parse error: {e}"


def load_posts():
    """Load today's personal posts JSON. Returns (data, error_str)."""
    path = os.path.join(POSTS_DIR, f"personal_posts_{TODAY}.json")
    if not os.path.exists(path):
        matches = glob.glob(os.path.join(POSTS_DIR, f"*{TODAY}*.json"))
        if matches:
            path = sorted(matches)[-1]
        else:
            return None, f"personal posts file not found: {path}"
    try:
        with open(path) as f:
            return json.load(f), None
    except Exception as e:
        return None, f"personal posts parse error: {e}"


# ---------------------------------------------------------------------------
# Briefing sections
# ---------------------------------------------------------------------------

def section_top_sources(sources_data, errors):
    """Render the ranked source table."""
    lines = ["## Top Sources Today", ""]

    if sources_data is None:
        lines.append(f"> Could not load sources: {errors}")
        return "\n".join(lines)

    articles = sources_data if isinstance(sources_data, list) else sources_data.get("articles", [])

    def sort_key(a):
        return (-float(a.get("score", 0)), float(a.get("hours_ago", 999)))

    top = sorted(articles, key=sort_key)[:10]

    if not top:
        lines.append("> No articles found for today.")
        return "\n".join(lines)

    lines += [
        "| Rank | Score | Source | Title | Age |",
        "|------|-------|--------|-------|-----|",
    ]

    for i, a in enumerate(top, 1):
        title     = a.get("title", "Untitled")
        # Truncate long titles for table readability
        if len(title) > 60:
            title = title[:57] + "..."
        score     = a.get("score", "?")
        source    = a.get("source", "?")
        hours_ago = float(a.get("hours_ago", 0))
        lines.append(f"| {i} | {score} | {source} | {title} | {hours_ago:.1f}h |")

    return "\n".join(lines)


def section_watch_list(sources_data):
    """Render the Watch List section."""
    lines = ["## Watch List", ""]

    if sources_data is None:
        for name in WATCH_LIST:
            lines.append(f"- {name}: (sources unavailable)")
        return "\n".join(lines)

    articles = sources_data if isinstance(sources_data, list) else sources_data.get("articles", [])

    # Map of watch-list name to articles found
    hits = {name: [] for name in WATCH_LIST}

    # Match keywords against source name or title
    keyword_map = {
        "Howard Marks":              ["Howard Marks", "Oaktree"],
        "Lyn Alden":                 ["Lyn Alden", "lynalden"],
        "Veritasium":                ["Veritasium"],
        "IMF":                       ["IMF", "International Monetary Fund"],
        "Federal Reserve speeches":  ["Federal Reserve", "Fed Chair", "FOMC", "Powell"],
    }

    for a in articles:
        title  = a.get("title", "")
        source = a.get("source", "")
        for name, kws in keyword_map.items():
            for kw in kws:
                if kw.lower() in title.lower() or kw.lower() in source.lower():
                    hits[name].append(a)
                    break

    for name in WATCH_LIST:
        found = hits[name]
        if found:
            titles = "; ".join(h.get("title", "untitled")[:70] for h in found[:2])
            lines.append(f"- {name}: new content found — {titles}")
        else:
            lines.append(f"- {name}: nothing new today")

    return "\n".join(lines)


def section_posts(posts_data, errors):
    """Render the Posts Ready to Publish section."""
    lines = ["## Posts Ready to Publish", ""]

    if posts_data is None:
        lines.append(f"> Could not load posts: {errors}")
        return "\n".join(lines)

    posts = posts_data if isinstance(posts_data, list) else posts_data.get("posts", [])

    if not posts:
        lines.append("> No posts generated for today.")
        return "\n".join(lines)

    default_times = ["08:30 AM", "11:00 AM", "01:30 PM", "04:00 PM", "06:30 PM"]

    for i, post in enumerate(posts, 1):
        post_time = post.get("publish_time", default_times[(i - 1) % len(default_times)])
        post_type = post.get("type", post.get("post_type", "Macro data observation"))
        template  = post.get("template", "A")
        source    = post.get("source", "")
        hashtags  = post.get("hashtags", "#MacroFinance #CapitalMarkets #DigitalAssets")
        text      = post.get("text", post.get("content", ""))
        chars     = len(text)
        visual    = f"personal/visuals/personal_visual_{TODAY}_{i}.png"

        lines += [
            f"### Post {i}  [{post_time}]",
            f"**Type:** {post_type}",
            f"**Template:** {template}",
            f"**Source:** {source}",
            f"**Visual:** {visual}",
            f"**Hashtags:** {hashtags}",
            f"**Characters:** {chars}",
            "",
            text,
            "",
            "---",
            "",
        ]

    return "\n".join(lines)


def section_conversations(posts_data, sources_data):
    """Render the Conversations to Join section."""
    lines = [
        "## Conversations to Join Today",
        "",
    ]

    # Try to pull topics from posts metadata; fall back to sensible defaults
    suggestions = []
    if posts_data is not None:
        posts = posts_data if isinstance(posts_data, list) else posts_data.get("posts", [])
        for p in posts:
            for conv in p.get("conversations", []):
                suggestions.append(conv)

    if not suggestions:
        suggestions = [
            ("#MacroFinance",    "Ask what the latest rates move signals for private credit duration."),
            ("#MonetaryPolicy",  "Note the lag between Fed language and credit spread reaction."),
            ("#CapitalMarkets",  "Highlight the disconnect between equity vol and credit vol."),
            ("#DigitalAssets",   "Add institutional context: who actually holds T-bill-backed stablecoins."),
            ("#StructuredFinance", "Point out that CLO tranche spreads are compressing faster than underlying."),
        ]

    for item in suggestions[:5]:
        if isinstance(item, dict):
            tag     = item.get("hashtag", item.get("tag", "#Topic"))
            comment = item.get("comment", item.get("angle", ""))
            lines.append(f'1. {tag} — Suggested comment: "{comment}"')
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            lines.append(f'1. {item[0]} — Suggested comment: "{item[1]}"')
        else:
            lines.append(f"1. {item}")

    return "\n".join(lines)


def section_bloomberg(sources_data):
    """Render Bloomberg Terminal Coverage section."""
    lines = [
        "## Bloomberg Terminal Coverage",
        "",
        "Top macro stories relevant to rates, credit, capital markets, and digital assets:",
        "(Sourced from available Bloomberg/GS/JPM feeds)",
        "",
    ]

    bloomberg_sources = {"Bloomberg Markets", "Goldman Sachs", "JP Morgan", "FT"}

    if sources_data is None:
        lines.append("(Sources unavailable)")
        return "\n".join(lines)

    articles = sources_data if isinstance(sources_data, list) else sources_data.get("articles", [])

    bloomberg_hits = [
        a for a in articles
        if a.get("source", "") in bloomberg_sources
        or any(s.lower() in a.get("source", "").lower() for s in ["bloomberg", "goldman", "jpmorgan", "jp morgan", "ft.com", "financial times"])
    ]

    def sort_key(a):
        return (-float(a.get("score", 0)), float(a.get("hours_ago", 999)))

    bloomberg_hits = sorted(bloomberg_hits, key=sort_key)[:7]

    if not bloomberg_hits:
        lines.append("(No Bloomberg/GS/JPM articles found in today's feed scan)")
        return "\n".join(lines)

    for i, a in enumerate(bloomberg_hits, 1):
        title     = a.get("title", "Untitled")
        source    = a.get("source", "?")
        url       = a.get("url", a.get("link", "#"))
        hours_ago = float(a.get("hours_ago", 0))
        lines.append(f"{i}. [{title}]({url}) ({source}, {hours_ago:.1f}h ago)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Summary counters
# ---------------------------------------------------------------------------

def compute_summary(sources_data, posts_data, visuals_dir):
    articles_scanned = 0
    posts_generated  = 0
    visuals_created  = 0
    failed_feeds     = []
    failed_feed_note = ""

    if sources_data is not None:
        articles = sources_data if isinstance(sources_data, list) else sources_data.get("articles", [])
        articles_scanned = len(articles)
        if isinstance(sources_data, dict):
            failed_feeds = sources_data.get("failed_feeds", [])

    if posts_data is not None:
        posts = posts_data if isinstance(posts_data, list) else posts_data.get("posts", [])
        posts_generated = len(posts)

    if os.path.isdir(visuals_dir):
        visuals_created = len(glob.glob(os.path.join(visuals_dir, f"personal_visual_{TODAY}_*.png")))

    if failed_feeds:
        feed_list = ", ".join(
            f"{f}" if isinstance(f, str) else f"{f.get('name', '?')} — {f.get('reason', 'error')}"
            for f in failed_feeds
        )
        failed_feed_note = f"  Failed feeds: {len(failed_feeds)} ({feed_list})"

    return articles_scanned, posts_generated, visuals_created, failed_feed_note


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"\nKiran Kaur Personal LinkedIn — Daily Content Briefing")
    print(f"Date: {DATE_DISPLAY}")
    print(f"Run directory: {BASE}")

    steps_ok = True

    # Step 1: Scan personal sources
    ok = run_step("STEP 1 — Scan Personal Sources", os.path.join(BASE, "scan_personal_sources.py"))
    if not ok:
        steps_ok = False

    # Step 2: Generate personal posts
    personal_posts_script = os.path.join(BASE, "generate_personal_posts.py")
    if os.path.exists(personal_posts_script):
        ok = run_step("STEP 2 — Generate Personal Posts", personal_posts_script)
        if not ok:
            steps_ok = False
    else:
        print(f"\n[SKIP] generate_personal_posts.py not found at {personal_posts_script}")
        print("       Create it to enable personal post generation.")

    # Step 3: Generate personal visuals
    ok = run_step("STEP 3 — Generate Personal Visuals", os.path.join(BASE, "generate_personal_visuals.py"))
    if not ok:
        steps_ok = False

    # Step 4: Build briefing
    print(f"\n{'='*60}")
    print(f"  STEP 4 — Build Personal Briefing")
    print(f"{'='*60}")

    sources_data, sources_err = load_sources()
    posts_data, posts_err     = load_posts()

    briefing_path = os.path.join(BASE, f"briefing_{TODAY}.md")

    briefing_lines = [
        "# Kiran Kaur Personal LinkedIn",
        "# Daily Content Briefing",
        f"# {DATE_DISPLAY}",
        "",
        "---",
        "",
        section_top_sources(sources_data, sources_err),
        "",
        "---",
        "",
        section_watch_list(sources_data),
        "",
        "---",
        "",
        section_posts(posts_data, posts_err),
        section_conversations(posts_data, sources_data),
        "",
        "---",
        "",
        section_bloomberg(sources_data),
        "",
        "---",
        "",
        "*Generated by Kiran Kaur personal content engine*",
        "*Eigenstate Research | Kiran Kaur*",
        "",
    ]

    briefing_text = "\n".join(briefing_lines)

    try:
        with open(briefing_path, "w") as f:
            f.write(briefing_text)
        print(f"[OK] Personal briefing written: {briefing_path}")
    except Exception as e:
        print(f"[ERROR] Could not write briefing: {e}")
        steps_ok = False

    # Summary
    articles_scanned, posts_generated, visuals_created, failed_feed_note = compute_summary(
        sources_data, posts_data, VISUALS_DIR
    )

    print(f"\n{'='*60}")
    print(f"  PERSONAL BRIEFING COMPLETE")
    print(f"{'='*60}")
    print(f"  Articles scanned:  {articles_scanned}")
    print(f"  Posts generated:   {posts_generated}")
    print(f"  Visuals created:   {visuals_created}")
    print(f"  Briefing:          briefing_{TODAY}.md")
    if failed_feed_note:
        print(failed_feed_note)
    if not steps_ok:
        print("  [WARNING] One or more pipeline steps reported errors. Review output above.")
    print()

    return 0 if steps_ok else 1


if __name__ == "__main__":
    sys.exit(main())
