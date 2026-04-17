"""
scan_sources.py — Settlement Layer Advisory daily content scanner.

Scans RSS feeds and engine data for relevant regulatory / RWA news.
Output: content_engine/sources/daily_YYYYMMDD.json

Usage:
    python3 scan_sources.py
"""

import feedparser
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ENV_PATH              = "/Users/kiran/GENIUSFLOW_OS/workspace/geniusflow/.env"
VAULT_PATH            = "/Users/kiran/GENIUSFLOW_OS/workspace/geniusflow/data/vault.json"
ENGINE_OUTPUT_PATH    = "/Users/kiran/GENIUSFLOW_OS/workspace/geniusflow/data/engine_output_latest.txt"
OUTPUT_DIR            = "/Users/kiran/SETTLEMENT_LAYER_ADVISORY/content_engine/sources"
ENTITY_READINGS_PATH  = "/Users/kiran/SETTLEMENT_LAYER_ADVISORY/content_engine/entity_readings.json"

SCRAPE_TIMEOUT = 12
SCRAPE_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SLAContentBot/1.0)"}

# ---------------------------------------------------------------------------
# RSS feeds
# ---------------------------------------------------------------------------
FEEDS = [
    ("SEC EDGAR", "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&dateb=&owner=include&count=10&search_text=&output=atom"),
    ("CFTC", "https://www.cftc.gov/rss/pressreleases.xml"),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("The Block", "https://www.theblock.co/rss.xml"),
    ("Tokenized Securities", "https://rss.app/feeds/tokenized-securities.xml"),
]

# ---------------------------------------------------------------------------
# Keywords — at least one must appear for an article to be kept
# ---------------------------------------------------------------------------
KEYWORDS = [
    "tokenized", "rwa", "real world asset", "sec", "cftc", "regulation",
    "compliance", "settlement", "accredited investor", "reg d", "reg s",
    "rule 506", "stablecoin", "genius act", "digital asset",
    "blockchain securities", "tokenized fund", "tokenized securities",
    "investor onboarding", "kyc", "aml",
]

# ---------------------------------------------------------------------------
# Entity readings — loaded dynamically from entity_readings.json
# ---------------------------------------------------------------------------
_ENTITY_DEFAULTS = {
    "Federal Reserve": {"phi_s": 2.41, "status": "ELEVATED"},
    "SEC":             {"phi_s": 1.19, "status": "ELEVATED"},
    "CFTC":            {"phi_s": 0.83, "status": "STABLE"},
    "OCC":             {"phi_s": 1.74, "status": "ELEVATED"},
    "Circle":          {"phi_s": 2.03, "status": "ELEVATED"},
    "Coinbase":        {"phi_s": 1.55, "status": "ELEVATED"},
    "ONDO":            {"phi_s": 0.94, "status": "STABLE"},
    "BlackRock":       {"phi_s": 1.88, "status": "ELEVATED"},
    "Fireblocks":      {"phi_s": 0.71, "status": "STABLE"},
    "Ripple":          {"phi_s": 3.12, "status": "HIGH"},
}

def load_entity_readings() -> dict:
    """Load dynamic Phi_S from entity_readings.json; fall back to defaults."""
    try:
        with open(ENTITY_READINGS_PATH) as f:
            data = json.load(f)
        readings = {}
        for entity, info in data.get("readings", {}).items():
            readings[entity] = {"phi_s": info["phi_s"], "status": info["status"]}
        if readings:
            return readings
    except Exception:
        pass
    return _ENTITY_DEFAULTS


# ---------------------------------------------------------------------------
# Scrapers — replacements for broken RSS feeds
# ---------------------------------------------------------------------------

def _safe_get(url: str) -> Optional[requests.Response]:
    try:
        r = requests.get(url, headers=SCRAPE_HEADERS, timeout=SCRAPE_TIMEOUT)
        r.raise_for_status()
        return r
    except Exception:
        return None


def scrape_sec() -> list:
    r = _safe_get(
        "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent"
        "&type=&dateb=&owner=include&count=20&search_text="
    )
    if not r:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for row in soup.select("table tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        link_tag = row.find("a", href=True)
        if not link_tag:
            continue
        title = f"SEC EDGAR: {' '.join(c.get_text(strip=True) for c in cells[:3])}"
        href = link_tag["href"]
        url = href if href.startswith("http") else "https://www.sec.gov" + href
        results.append({"title": title, "summary": "SEC EDGAR filing", "published": "", "source": "SEC EDGAR", "url": url})
    return results[:20]


def scrape_cftc() -> list:
    r = _safe_get("https://www.cftc.gov/PressRoom/PressReleases")
    if not r:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for a in soup.select("a[href*='/PressRoom/PressReleases/']"):
        title = a.get_text(strip=True)
        if not title or len(title) < 10:
            continue
        href = a["href"]
        url = href if href.startswith("http") else "https://www.cftc.gov" + href
        # Get date from nearest sibling text
        parent_text = a.parent.get_text(separator=" ", strip=True) if a.parent else ""
        results.append({"title": title, "summary": parent_text[:200], "published": "", "source": "CFTC", "url": url})
    return results[:20]


def scrape_bis() -> list:
    results = []
    for path in ["/list/speeches/index.htm", "/list/papers/index.htm"]:
        r = _safe_get(f"https://www.bis.org{path}")
        if not r:
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for item in soup.select("div.item, li.item, tr"):
            a = item.find("a", href=True)
            if not a:
                continue
            title = a.get_text(strip=True)
            if not title or len(title) < 10:
                continue
            href = a["href"]
            url = href if href.startswith("http") else "https://www.bis.org" + href
            date_el = item.find(class_=re.compile(r"date|time", re.I))
            pub = date_el.get_text(strip=True) if date_el else ""
            results.append({"title": title, "summary": pub, "published": "", "source": "BIS", "url": url})
    return results[:20]


def scrape_imf() -> list:
    r = _safe_get("https://www.imf.org/en/Publications/Search?when=Last30days&series=WP")
    if not r:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for item in soup.select("div.result-item, article, div.card"):
        a = item.find("a", href=True)
        if not a:
            continue
        title = a.get_text(strip=True)
        if not title or len(title) < 10:
            continue
        href = a["href"]
        url = href if href.startswith("http") else "https://www.imf.org" + href
        summary_el = item.find(class_=re.compile(r"summary|desc|abstract", re.I))
        summary = summary_el.get_text(strip=True)[:300] if summary_el else ""
        results.append({"title": title, "summary": summary, "published": "", "source": "IMF", "url": url})
    return results[:15]


def scrape_goldman() -> list:
    r = _safe_get("https://www.goldmansachs.com/insights/")
    if not r:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for tag in soup.find_all(["h2", "h3", "h4"]):
        a = tag.find("a", href=True) or (tag.parent.find("a", href=True) if tag.parent else None)
        if not a:
            continue
        title = tag.get_text(strip=True)
        if not title or len(title) < 10:
            continue
        href = a["href"]
        url = href if href.startswith("http") else "https://www.goldmansachs.com" + href
        results.append({"title": title, "summary": "", "published": "", "source": "Goldman Sachs", "url": url})
    return results[:15]


def scrape_jpmorgan() -> list:
    r = _safe_get("https://www.jpmorgan.com/insights/research")
    if not r:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for tag in soup.find_all(["h2", "h3", "h4"]):
        a = tag.find("a", href=True) or (tag.parent.find("a", href=True) if tag.parent else None)
        if not a:
            continue
        title = tag.get_text(strip=True)
        if not title or len(title) < 10:
            continue
        href = a["href"]
        url = href if href.startswith("http") else "https://www.jpmorgan.com" + href
        results.append({"title": title, "summary": "", "published": "", "source": "JP Morgan", "url": url})
    return results[:15]


def scrape_worldbank() -> list:
    # Try RSS first
    feed = feedparser.parse("https://blogs.worldbank.org/en/rss.xml")
    if not feed.bozo and feed.entries:
        results = []
        for entry in feed.entries:
            title = getattr(entry, "title", "")
            summary = re.sub(r"<[^>]+>", " ", getattr(entry, "summary", "") or "").strip()
            results.append({"title": title, "summary": summary[:300], "published": "", "source": "World Bank", "url": getattr(entry, "link", "")})
        return results[:15]
    # Fallback: scrape
    r = _safe_get("https://blogs.worldbank.org/en/allblog")
    if not r:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for a in soup.select("h2 a, h3 a, .blog-title a"):
        title = a.get_text(strip=True)
        if not title or len(title) < 10:
            continue
        href = a.get("href", "")
        url = href if href.startswith("http") else "https://blogs.worldbank.org" + href
        results.append({"title": title, "summary": "", "published": "", "source": "World Bank", "url": url})
    return results[:15]


def scrape_coindesk() -> list:
    r = _safe_get("https://www.coindesk.com/")
    if not r:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not re.match(r"/(markets|policy|tech|business)/", href):
            continue
        title = a.get_text(strip=True)
        if not title or len(title) < 15 or href in seen:
            continue
        seen.add(href)
        url = "https://www.coindesk.com" + href if not href.startswith("http") else href
        results.append({"title": title, "summary": "", "published": "", "source": "CoinDesk", "url": url})
    return results[:20]


SCRAPERS = [
    ("SEC EDGAR",     scrape_sec),
    ("CFTC",          scrape_cftc),
    ("BIS",           scrape_bis),
    ("IMF",           scrape_imf),
    ("Goldman Sachs", scrape_goldman),
    ("JP Morgan",     scrape_jpmorgan),
    ("World Bank",    scrape_worldbank),
    ("CoinDesk",      scrape_coindesk),
]

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


def entry_has_keyword(text: str) -> bool:
    """Return True if text contains at least one tracked keyword (case-insensitive)."""
    lower = text.lower()
    return any(kw in lower for kw in KEYWORDS)


def parse_entry_time(entry) -> Optional[datetime]:
    """Try to extract a timezone-aware datetime from a feedparser entry."""
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                import time as _time
                ts = _time.mktime(val)
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except Exception:
                pass
    return None


def score_article(title: str, summary: str, pub_dt: Optional[datetime], now: datetime) -> int:
    """Return relevance score for an article."""
    combined = (title + " " + summary).lower()
    score = 0

    if "sec" in combined or "cftc" in combined:
        score += 3
    if "regulation" in combined or "compliance" in combined:
        score += 3
    if "rwa" in combined or "tokenized" in combined:
        score += 2
    if re.search(r"rule\s*506|reg\s*d\b|reg\s*s\b", combined):
        score += 2

    if pub_dt:
        age_hours = (now - pub_dt).total_seconds() / 3600
        if age_hours <= 24:
            score += 1
        if age_hours <= 6:
            score += 1

    return score


def hours_ago(pub_dt: Optional[datetime], now: datetime) -> Optional[float]:
    if pub_dt is None:
        return None
    return round((now - pub_dt).total_seconds() / 3600, 2)


# ---------------------------------------------------------------------------
# Feed scanning
# ---------------------------------------------------------------------------

def scan_feeds(now: datetime) -> tuple[list[dict], list[str]]:
    """Fetch and filter articles from all feeds + scrapers. Returns (articles, failed_feeds)."""
    articles = []
    failed = []

    # RSS feeds (feedparser)
    for source_name, url in FEEDS:
        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                raise ValueError(f"feedparser bozo error: {feed.bozo_exception}")

            count_before = len(articles)
            for entry in feed.entries:
                title = getattr(entry, "title", "") or ""
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
                summary_clean = re.sub(r"<[^>]+>", " ", summary).strip()
                summary_clean = re.sub(r"\s+", " ", summary_clean)
                combined_text = title + " " + summary_clean
                if not entry_has_keyword(combined_text):
                    continue
                pub_dt = parse_entry_time(entry)
                link = getattr(entry, "link", "") or ""
                articles.append({
                    "title": title.strip(),
                    "summary": summary_clean[:500],
                    "published": pub_dt.isoformat() if pub_dt else "",
                    "source": source_name,
                    "url": link,
                    "_pub_dt": pub_dt,
                    "_score": score_article(title, summary_clean, pub_dt, now),
                })

            fetched = len(articles) - count_before
            print(f"  [{source_name}] {fetched} relevant article(s) found.", file=sys.stderr)

        except Exception as exc:
            print(f"  [WARN] Feed failed — {source_name} ({url}): {exc}", file=sys.stderr)
            failed.append(source_name)

    # HTTP scrapers (replace broken RSS)
    for source_name, scraper_fn in SCRAPERS:
        try:
            raw = scraper_fn()
            count = 0
            for item in raw:
                title   = item.get("title", "").strip()
                summary = item.get("summary", "").strip()
                url     = item.get("url", "")
                if not title or not url:
                    continue
                combined = title + " " + summary
                if not entry_has_keyword(combined):
                    continue
                articles.append({
                    "title":     title,
                    "summary":   summary[:500],
                    "published": item.get("published", ""),
                    "source":    source_name,
                    "url":       url,
                    "_pub_dt":   None,
                    "_score":    score_article(title, summary, None, now),
                })
                count += 1
            print(f"  [{source_name}] {count} relevant article(s) scraped.", file=sys.stderr)
        except Exception as exc:
            print(f"  [WARN] Scraper failed — {source_name}: {exc}", file=sys.stderr)
            failed.append(source_name)

    return articles, failed


# ---------------------------------------------------------------------------
# Engine readings
# ---------------------------------------------------------------------------

def load_parkash(vault_path: str) -> dict:
    """Find the latest PARKASH_SESSION record and return PT/kappa/coverage."""
    defaults = {"PT": 0.213, "kappa": 0.386, "coverage": 0.0}
    try:
        with open(vault_path) as fh:
            records = json.load(fh)
        if not isinstance(records, list):
            return defaults
        sessions = [r for r in records if r.get("entity") == "PARKASH_SESSION"]
        if not sessions:
            return defaults
        latest = sessions[-1]
        return {
            "PT":       latest.get("PT", defaults["PT"]),
            "kappa":    latest.get("kappa", defaults["kappa"]),
            "coverage": latest.get("coverage", defaults["coverage"]),
        }
    except Exception as exc:
        print(f"[WARN] Could not load vault: {exc}", file=sys.stderr)
        return defaults


def load_helix_block(engine_output_path: str, default: int = 44882914) -> int:
    """Try to extract a block number from engine_output_latest.txt."""
    try:
        with open(engine_output_path) as fh:
            content = fh.read()
        # Look for patterns like "block 44882914", "block=44882914", or bare 8-digit numbers
        match = re.search(r"block[:\s=#]*([0-9]{7,})", content, re.IGNORECASE)
        if match:
            return int(match.group(1))
        # Fallback: any 8+ digit standalone number
        match = re.search(r"\b([0-9]{8,})\b", content)
        if match:
            return int(match.group(1))
    except Exception as exc:
        print(f"[WARN] Could not read engine output: {exc}", file=sys.stderr)
    return default


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    now = datetime.now(tz=timezone.utc)
    date_str = now.strftime("%Y%m%d")
    date_display = now.strftime("%Y-%m-%d")
    generated_at = now.strftime("%Y-%m-%dT%H:%M:%S")

    print(f"=== Settlement Layer Advisory — Source Scan {date_display} ===")

    # Load env (sets ANTHROPIC_API_KEY in environment for downstream use)
    env = load_env(ENV_PATH)
    if "ANTHROPIC_API_KEY" in env:
        os.environ.setdefault("ANTHROPIC_API_KEY", env["ANTHROPIC_API_KEY"])
        print(f"  ANTHROPIC_API_KEY loaded from .env.")
    else:
        print("[WARN] ANTHROPIC_API_KEY not found in .env", file=sys.stderr)

    # Scan feeds
    print("\nScanning feeds...")
    raw_articles, failed_feeds = scan_feeds(now)
    print(f"\n  Total relevant articles before dedup: {len(raw_articles)}")

    # Deduplicate by URL, keep highest score
    seen_urls: dict[str, dict] = {}
    for art in raw_articles:
        url = art["url"]
        if url not in seen_urls or art["_score"] > seen_urls[url]["_score"]:
            seen_urls[url] = art

    deduped = list(seen_urls.values())

    # Sort by score descending, then by recency
    deduped.sort(key=lambda a: (a["_score"], a["_pub_dt"] or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)

    # Keep top 10
    top10 = deduped[:10]

    # Build clean article list
    output_articles = []
    for rank, art in enumerate(top10, start=1):
        output_articles.append({
            "rank":      rank,
            "score":     art["_score"],
            "title":     art["title"],
            "summary":   art["summary"],
            "published": art["published"],
            "source":    art["source"],
            "url":       art["url"],
            "hours_ago": hours_ago(art["_pub_dt"], now),
        })

    # Engine readings (dynamic from entity_readings.json)
    parkash = load_parkash(VAULT_PATH)
    helix_block = load_helix_block(ENGINE_OUTPUT_PATH)
    entity_readings = load_entity_readings()

    # Build output payload
    payload = {
        "date":            date_display,
        "generated_at":    generated_at,
        "articles":        output_articles,
        "engine_readings": entity_readings,
        "parkash":         parkash,
        "helix_block":     helix_block,
        "helix_tx":        "eigenstate_obs",
        "total_scanned":   len(raw_articles),
    }

    # Write output
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"daily_{date_str}.json")
    with open(output_path, "w") as fh:
        json.dump(payload, fh, indent=2)
    print(f"\n  Output written: {output_path}")

    # Summary to stdout
    total_scanned = len(raw_articles)
    print(f"\n--- Summary ---")
    print(f"  Articles scanned (pre-dedup): {total_scanned}")
    print(f"  Articles after dedup:          {len(deduped)}")
    print(f"  Kept (top 10):                 {len(output_articles)}")
    if failed_feeds:
        print(f"  Failed feeds:                  {', '.join(failed_feeds)}")
    else:
        print(f"  Failed feeds:                  none")
    print(f"  Parkash PT={parkash['PT']:.4f}  kappa={parkash['kappa']:.4f}  coverage={parkash['coverage']:.4f}")
    print(f"  Helix block:                   {helix_block}")

    print(f"\n  Top 3 articles by score:")
    for art in output_articles[:3]:
        age = f"{art['hours_ago']}h ago" if art["hours_ago"] is not None else "unknown age"
        print(f"    [{art['score']}] {art['title'][:80]}  ({art['source']}, {age})")

    print("\nDone.")


if __name__ == "__main__":
    main()
