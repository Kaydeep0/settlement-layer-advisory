"""
scan_personal_sources.py — Kiran's personal macro/finance feed scanner.

Scans a curated set of RSS feeds for macro, monetary policy, and structural
finance content. Scores by author, topic, and recency. Flags Lyn Alden,
Howard Marks, Veritasium, IMF, and Fed speeches published in the last 48h.

Usage:
    python3 scan_personal_sources.py

Output: content_engine/personal/sources/personal_YYYYMMDD.json
"""

import feedparser
import json
import os
import re
import sys
import time as _time
from datetime import datetime, timezone, timedelta
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ENV_PATH   = "/Users/kiran/GENIUSFLOW_OS/workspace/geniusflow/.env"
OUTPUT_DIR = "/Users/kiran/SETTLEMENT_LAYER_ADVISORY/content_engine/personal/sources"

# ---------------------------------------------------------------------------
# Personal RSS feeds
# ---------------------------------------------------------------------------
PERSONAL_FEEDS = [
    ("Veritasium",      "https://www.youtube.com/feeds/videos.xml?channel_id=UCHnyfMqiRRG1u-2MsSQLbXA"),
    ("Bloomberg Markets","https://feeds.bloomberg.com/markets/news.rss"),
    ("IMF",             "https://www.imf.org/en/News/rss?language=eng"),
    ("Lyn Alden",       "https://www.lynalden.com/feed/"),
    ("Patrick Boyle",   "https://www.youtube.com/feeds/videos.xml?channel_id=UCYY5GWf7MHFJ6DZeHreoXgw"),
    ("MacroVoices",     "https://www.macrovoices.com/feed"),
    ("ZeroHedge",       "https://feeds.feedburner.com/zerohedge/feed"),
    ("Goldman Sachs",   "https://www.goldmansachs.com/rss/insights.xml"),
    ("JP Morgan",       "https://www.jpmorgan.com/insights/rss"),
    ("BIS",             "https://www.bis.org/rss/cbspeeches.rss"),
    ("Federal Reserve", "https://www.federalreserve.gov/feeds/speeches.xml"),
    ("World Bank",      "https://feeds.worldbank.org/worldbank/news"),
    ("FT",              "https://www.ft.com/rss/home"),
]

# ---------------------------------------------------------------------------
# Filter keywords — article must contain at least one to be kept
# ---------------------------------------------------------------------------
KEYWORDS = [
    "macro", "economy", "inflation", "debt", "rates", "monetary", "fiscal",
    "capital", "market", "finance", "investment", "wealth", "banking", "credit",
    "growth", "recession", "yield", "bond", "equity", "fund", "asset",
    "portfolio", "policy", "central bank", "imf", "fed", "bis", "goldman",
    "jpmorgan", "structural", "cycle", "liquidity", "leverage", "systemic",
]

# Watch-list names for presence checks
WATCH_NAMES = ["lyn alden", "howard marks"]

# ---------------------------------------------------------------------------
# Helpers
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


def has_keyword(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in KEYWORDS)


def parse_entry_time(entry) -> Optional[datetime]:
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                ts = _time.mktime(val)
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except Exception:
                pass
    return None


def hours_ago(pub_dt: Optional[datetime], now: datetime) -> Optional[float]:
    if pub_dt is None:
        return None
    return round((now - pub_dt).total_seconds() / 3600, 2)


def score_article(
    source_name: str,
    title: str,
    summary: str,
    pub_dt: Optional[datetime],
    now: datetime,
) -> int:
    """
    Personal scoring rubric for macro/finance content quality.
    Returns integer score; higher = more relevant to Kiran.
    """
    combined = (title + " " + summary).lower()
    score = 0

    # --- High-value authors (+3 each) ---
    if source_name in ("Lyn Alden", "Howard Marks"):
        score += 3
    if any(n in combined for n in WATCH_NAMES):
        score += 3

    if source_name in ("Veritasium", "Patrick Boyle"):
        score += 3

    if source_name in ("IMF", "World Bank") and re.search(r"policy|framework", combined):
        score += 3

    if re.search(r"central bank|monetary policy|rate decision", combined):
        score += 3

    # --- Institutional sources (+2) ---
    if source_name in ("Goldman Sachs", "JP Morgan", "BIS"):
        score += 2

    if re.search(r"\bdebt\b|inflation|interest rate|capital flows", combined):
        score += 2

    if re.search(r"structural shift|paradigm|capital cycle", combined):
        score += 2

    # --- Freshness (+1 each) ---
    if pub_dt:
        age_h = (now - pub_dt).total_seconds() / 3600
        if age_h <= 6:
            score += 1

    # --- Counterintuitive framing (+1) ---
    if re.search(r"contrary|surprising|against consensus|most people miss", combined):
        score += 1

    # --- Specific data (+1) ---
    if re.search(r"\d+(?:\.\d+)?\s*(?:%|percent|bp|bps)", combined):
        score += 1

    return score


def is_fresh(pub_dt: Optional[datetime], now: datetime, max_hours: float = 48.0) -> bool:
    """Return True if article was published within max_hours."""
    if pub_dt is None:
        return False
    return (now - pub_dt).total_seconds() / 3600 <= max_hours


# ---------------------------------------------------------------------------
# Feed scanning
# ---------------------------------------------------------------------------

def scan_feeds(now: datetime) -> tuple[list[dict], list[str], int]:
    """
    Fetch and filter articles from all personal feeds.
    Returns (articles, failed_feeds, total_scanned).
    """
    articles     = []
    failed       = []
    total_scanned = 0

    for source_name, url in PERSONAL_FEEDS:
        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                raise ValueError(f"feedparser bozo error: {feed.bozo_exception}")

            count_before = len(articles)
            for entry in feed.entries:
                total_scanned += 1
                title   = getattr(entry, "title", "") or ""
                summary = (
                    getattr(entry, "summary", "")
                    or getattr(entry, "description", "")
                    or ""
                )
                # Strip HTML
                summary_clean = re.sub(r"<[^>]+>", " ", summary).strip()
                summary_clean = re.sub(r"\s+", " ", summary_clean)

                combined_text = title + " " + summary_clean
                if not has_keyword(combined_text):
                    continue

                pub_dt = parse_entry_time(entry)
                link   = getattr(entry, "link", "") or ""

                articles.append({
                    "title":     title.strip(),
                    "summary":   summary_clean[:500],
                    "published": pub_dt.isoformat() if pub_dt else "",
                    "source":    source_name,
                    "url":       link,
                    "_pub_dt":   pub_dt,
                    "_score":    score_article(source_name, title, summary_clean, pub_dt, now),
                })

            fetched = len(articles) - count_before
            print(f"  [{source_name}] {fetched} article(s) matched.", file=sys.stderr)

        except Exception as exc:
            print(f"  [WARN] Feed failed — {source_name} ({url}): {exc}", file=sys.stderr)
            failed.append(source_name)

    return articles, failed, total_scanned


# ---------------------------------------------------------------------------
# Watch-list detection
# ---------------------------------------------------------------------------

def build_watch_list(articles: list[dict], now: datetime) -> dict:
    """
    Detect whether key authors/sources published within the last 48 hours.
    """
    watch = {
        "lyn_alden_new":    False,
        "howard_marks_new": False,
        "veritasium_new":   False,
        "imf_new":          False,
        "fed_speech_new":   False,
    }

    for art in articles:
        src    = art.get("source", "")
        combined = (art.get("title", "") + " " + art.get("summary", "")).lower()
        fresh  = is_fresh(art.get("_pub_dt"), now, 48)

        if not fresh:
            continue

        if src == "Lyn Alden" or "lyn alden" in combined:
            watch["lyn_alden_new"] = True
        if src == "Howard Marks" or "howard marks" in combined:
            watch["howard_marks_new"] = True
        if src == "Veritasium":
            watch["veritasium_new"] = True
        if src == "IMF":
            watch["imf_new"] = True
        if src == "Federal Reserve":
            watch["fed_speech_new"] = True

    return watch


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    now          = datetime.now(tz=timezone.utc)
    date_str     = now.strftime("%Y%m%d")
    date_display = now.strftime("%Y-%m-%d")
    generated_at = now.strftime("%Y-%m-%dT%H:%M:%S")

    print(f"=== Personal Source Scan — {date_display} ===")

    # Load env (for downstream consumers that need API keys)
    env = load_env(ENV_PATH)
    if "ANTHROPIC_API_KEY" in env:
        os.environ.setdefault("ANTHROPIC_API_KEY", env["ANTHROPIC_API_KEY"])
        print("  ANTHROPIC_API_KEY loaded.")
    else:
        print("[WARN] ANTHROPIC_API_KEY not found in .env", file=sys.stderr)

    # Scan feeds
    print("\nScanning personal feeds...")
    raw_articles, failed_feeds, total_scanned = scan_feeds(now)
    print(f"\n  Total scanned: {total_scanned}")
    print(f"  Matched keyword filter: {len(raw_articles)}")

    # Deduplicate by URL, keep highest score
    seen_urls: dict[str, dict] = {}
    for art in raw_articles:
        url = art["url"]
        if url not in seen_urls or art["_score"] > seen_urls[url]["_score"]:
            seen_urls[url] = art

    deduped = list(seen_urls.values())

    # Sort by score desc, then by recency
    deduped.sort(
        key=lambda a: (
            a["_score"],
            a["_pub_dt"] or datetime.min.replace(tzinfo=timezone.utc),
        ),
        reverse=True,
    )

    # Keep top 15
    top15 = deduped[:15]

    # Build clean output list
    output_articles = []
    for rank, art in enumerate(top15, start=1):
        output_articles.append({
            "rank":      rank,
            "score":     art["_score"],
            "title":     art["title"],
            "summary":   art["summary"],
            "published": art["published"],
            "source":    art["source"],
            "url":       art["url"],
            "hours_ago": hours_ago(art.get("_pub_dt"), now),
        })

    # Watch-list flags
    watch_list = build_watch_list(raw_articles, now)

    # Build output payload
    payload = {
        "date":          date_display,
        "generated_at":  generated_at,
        "articles":      output_articles,
        "watch_list":    watch_list,
        "failed_feeds":  failed_feeds,
        "total_scanned": total_scanned,
    }

    # Write output
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"personal_{date_str}.json")
    with open(output_path, "w") as fh:
        json.dump(payload, fh, indent=2)
    print(f"\n  Output written: {output_path}")

    # Summary
    print(f"\n--- Summary ---")
    print(f"  Total scanned:         {total_scanned}")
    print(f"  After keyword filter:  {len(raw_articles)}")
    print(f"  After dedup:           {len(deduped)}")
    print(f"  Kept (top 15):         {len(output_articles)}")
    if failed_feeds:
        print(f"  Failed feeds:          {', '.join(failed_feeds)}")
    else:
        print(f"  Failed feeds:          none")

    print(f"\n  Watch-list flags:")
    for key, val in watch_list.items():
        flag = "YES" if val else "no"
        print(f"    {key:<22} {flag}")

    if output_articles:
        print(f"\n  Top 3 articles by score:")
        for art in output_articles[:3]:
            age = f"{art['hours_ago']}h ago" if art["hours_ago"] is not None else "unknown age"
            print(f"    [{art['score']}] {art['title'][:80]}  ({art['source']}, {age})")

    print("\nDone.")


if __name__ == "__main__":
    main()
