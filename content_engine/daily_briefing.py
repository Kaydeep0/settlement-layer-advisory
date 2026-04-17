#!/usr/bin/env python3
"""Settlement Layer Advisory — Daily Content Briefing Orchestrator"""

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

GENIUSFLOW_BASE = "/Users/kiran/GENIUSFLOW_OS/workspace/geniusflow"
HOST_STATE_PATH = os.path.join(GENIUSFLOW_BASE, "HOST", "state.json")
ENGINE_OUTPUT_PATH = os.path.join(GENIUSFLOW_BASE, "data", "engine_output_latest.txt")


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
    """Load today's sources JSON. Returns (data, error_str)."""
    path = os.path.join(SOURCES_DIR, f"daily_{TODAY}.json")
    if not os.path.exists(path):
        # Try any file matching today's date pattern
        matches = glob.glob(os.path.join(SOURCES_DIR, f"*{TODAY}*.json"))
        if matches:
            path = sorted(matches)[-1]
        else:
            return None, f"sources file not found: {path}"
    try:
        with open(path) as f:
            return json.load(f), None
    except Exception as e:
        return None, f"sources parse error: {e}"


def load_posts():
    """Load today's posts JSON. Returns (data, error_str)."""
    path = os.path.join(POSTS_DIR, f"posts_{TODAY}.json")
    if not os.path.exists(path):
        matches = glob.glob(os.path.join(POSTS_DIR, f"*{TODAY}*.json"))
        if matches:
            path = sorted(matches)[-1]
        else:
            return None, f"posts file not found: {path}"
    try:
        with open(path) as f:
            return json.load(f), None
    except Exception as e:
        return None, f"posts parse error: {e}"


def load_host_state():
    """Load HOST/state.json for PT, kappa, hourglass. Returns dict (empty on failure)."""
    if not os.path.exists(HOST_STATE_PATH):
        return {}
    try:
        with open(HOST_STATE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Briefing sections
# ---------------------------------------------------------------------------

def section_engine_readings(state):
    """Render the Engine Readings section."""
    pt       = state.get("PT", "N/A")
    kappa    = state.get("kappa", state.get("k", "N/A"))
    coverage = state.get("coverage", "N/A")
    block    = state.get("helix_block", state.get("block", "N/A"))

    # Try to pull entity phi_s table from engine output if available
    entity_rows = ""
    try:
        if os.path.exists(ENGINE_OUTPUT_PATH):
            with open(ENGINE_OUTPUT_PATH) as f:
                raw = f.read()
            # Parse lines like "Federal Reserve  phi_s=2.41  ELEVATED"
            import re
            for m in re.finditer(
                r"([A-Za-z ]{4,30})\s+phi_s\s*[=:]\s*([0-9.]+)\s+([A-Z_]+)", raw
            ):
                entity_rows += f"| {m.group(1).strip()} | {m.group(2)} | {m.group(3)} |\n"
    except Exception:
        pass

    if not entity_rows:
        entity_rows = (
            "| Federal Reserve | -- | -- |\n"
            "| SEC | -- | -- |\n"
            "| Tokenized Treasury Pool | -- | -- |\n"
        )

    lines = [
        "## Engine Readings Today",
        "",
        "| Entity | Phi_S | Status |",
        "|--------|-------|--------|",
        entity_rows.rstrip(),
        "",
        f"PT: {pt} | kappa: {kappa} | Coverage: {coverage}%",
        f"Helix Block: {block}",
    ]
    return "\n".join(lines)


def section_top_sources(sources_data, errors):
    """Render the Top Sources section."""
    lines = ["## Top Sources Scanned", ""]

    if sources_data is None:
        lines.append(f"> Could not load sources: {errors}")
        return "\n".join(lines)

    articles = sources_data if isinstance(sources_data, list) else sources_data.get("articles", [])
    failed   = sources_data.get("failed_feeds", []) if isinstance(sources_data, dict) else []

    # Sort by score descending, then age ascending
    def sort_key(a):
        return (-float(a.get("score", 0)), float(a.get("hours_ago", 999)))

    top = sorted(articles, key=sort_key)[:10]

    if not top:
        lines.append("> No articles found for today.")
        return "\n".join(lines)

    for i, a in enumerate(top, 1):
        title     = a.get("title", "Untitled")
        url       = a.get("url", a.get("link", "#"))
        score     = a.get("score", "?")
        source    = a.get("source", "?")
        hours_ago = float(a.get("hours_ago", 0))
        lines.append(f"{i}. [{title}]({url}) — Score: {score} | {source} | {hours_ago:.1f}h ago")

    if failed:
        lines.append("")
        lines.append("**Failed feeds:** " + ", ".join(failed))

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

    # Default publish times (cycle through if more than 5)
    default_times = ["08:00 AM", "11:00 AM", "01:00 PM", "03:30 PM", "06:00 PM"]

    for i, post in enumerate(posts, 1):
        post_time = post.get("publish_time", default_times[(i - 1) % len(default_times)])
        template  = post.get("template", "C")
        source    = post.get("source", "Eigenstate Research")
        hashtags  = post.get("hashtags", "#RWA #TokenizedAssets #Compliance")
        text      = post.get("text", post.get("content", ""))
        chars     = len(text)
        visual    = f"visuals/visual_{TODAY}_{i}.png"

        lines += [
            f"### Post {i}  [Best time: {post_time}]",
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


TRENDING_CONVERSATIONS = """\
## Trending Conversations to Join

This section lists 5 relevant LinkedIn hashtags and conversation angles in RWA and compliance today:

1. #RWA — Tokenized fund AUM hitting new highs; question institutional infrastructure readiness
2. #GENIUSAct — Senate timeline pressure; stablecoin issuers mapping reserve attestation
3. #TokenizedAssets — SEC jurisdictional clarity; secondary market transfer restrictions
4. #DigitalAssets — SAB 122 downstream effects on custodian compliance structures
5. #Compliance — Accredited investor verification gap; 506(c) reasonable steps standard"""


# ---------------------------------------------------------------------------
# Summary counters
# ---------------------------------------------------------------------------

def compute_summary(sources_data, posts_data, visuals_dir, steps_failed):
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
        visuals_created = len(glob.glob(os.path.join(visuals_dir, f"visual_{TODAY}_*.png")))

    if failed_feeds:
        # Build a short note
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
    print(f"\nSettlement Layer Advisory — Daily Content Briefing")
    print(f"Date: {DATE_DISPLAY}")
    print(f"Run directory: {BASE}")

    steps_ok = True

    # Step 1: Scan sources
    ok = run_step("STEP 1 — Scan Sources", os.path.join(BASE, "scan_sources.py"))
    if not ok:
        steps_ok = False

    # Step 2: Generate posts
    ok = run_step("STEP 2 — Generate Posts", os.path.join(BASE, "generate_posts.py"))
    if not ok:
        steps_ok = False

    # Step 3: Generate visuals
    ok = run_step("STEP 3 — Generate Visuals", os.path.join(BASE, "generate_visuals.py"))
    if not ok:
        steps_ok = False

    # Step 4: Build briefing
    print(f"\n{'='*60}")
    print(f"  STEP 4 — Build Briefing")
    print(f"{'='*60}")

    sources_data, sources_err = load_sources()
    posts_data, posts_err     = load_posts()
    state                     = load_host_state()

    briefing_path = os.path.join(BASE, f"briefing_{TODAY}.md")

    briefing_lines = [
        "# Settlement Layer Advisory",
        "# Daily Content Briefing",
        f"# {DATE_DISPLAY}",
        "",
        "---",
        "",
        section_engine_readings(state),
        "",
        "---",
        "",
        section_top_sources(sources_data, sources_err),
        "",
        "---",
        "",
        section_posts(posts_data, posts_err),
        TRENDING_CONVERSATIONS,
        "",
        "---",
        "",
        "*Generated by Settlement Layer Advisory content engine*",
        "*Powered by Eigenstate Research | Base mainnet timestamped*",
        "",
    ]

    briefing_text = "\n".join(briefing_lines)

    try:
        with open(briefing_path, "w") as f:
            f.write(briefing_text)
        print(f"[OK] Briefing written: {briefing_path}")
    except Exception as e:
        print(f"[ERROR] Could not write briefing: {e}")
        steps_ok = False

    # Summary
    articles_scanned, posts_generated, visuals_created, failed_feed_note = compute_summary(
        sources_data, posts_data, VISUALS_DIR, not steps_ok
    )

    print(f"\n{'='*60}")
    print(f"  BRIEFING COMPLETE")
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
