"""
entity_readings_updater.py — Settlement Layer Advisory entity Phi_S tracker.

Reads today's daily_YYYYMMDD.json from sources/, counts entity mentions,
updates Phi_S values, and saves to entity_readings.json.

Usage:
    python3 entity_readings_updater.py
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SOURCES_DIR = "/Users/kiran/SETTLEMENT_LAYER_ADVISORY/content_engine/sources"
READINGS_PATH = "/Users/kiran/SETTLEMENT_LAYER_ADVISORY/content_engine/entity_readings.json"

# ---------------------------------------------------------------------------
# Entity search terms (case-insensitive)
# ---------------------------------------------------------------------------
ENTITY_TERMS = {
    "Federal Reserve": ["federal reserve", "fed ", "fomc", "powell", "fed rate"],
    "SEC":             ["sec ", "securities and exchange", "gensler", "atkins"],
    "CFTC":            ["cftc", "commodity futures", "selig"],
    "OCC":             ["occ ", "office of the comptroller", "hsu"],
    "Circle":          ["circle", "usdc", "jeremy allaire"],
    "Coinbase":        ["coinbase", "brian armstrong", "base chain"],
    "ONDO":            ["ondo", "ousg", "ondo finance"],
    "BlackRock":       ["blackrock", "buidl", "larry fink"],
    "Fireblocks":      ["fireblocks", "mpc custody"],
    "Ripple":          ["ripple", "xrp", "ripplenet"],
}

# ---------------------------------------------------------------------------
# Defaults (used if entity_readings.json does not exist)
# ---------------------------------------------------------------------------
DEFAULTS = {
    "Federal Reserve": 2.41,
    "SEC":             1.19,
    "CFTC":            0.83,
    "OCC":             1.74,
    "Circle":          2.03,
    "Coinbase":        1.55,
    "ONDO":            0.94,
    "BlackRock":       1.88,
    "Fireblocks":      0.71,
    "Ripple":          3.12,
}

PHI_MAX = 10.0
PHI_FLOOR = 0.3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def phi_status(phi_s: float) -> str:
    if phi_s < 1.0:
        return "STABLE"
    elif phi_s < 2.0:
        return "ELEVATED"
    elif phi_s < 4.0:
        return "HIGH"
    else:
        return "EXTRACTION"


def compute_delta(mention_count: int) -> float:
    """Return the raw delta to apply based on mention count."""
    if mention_count == 0:
        return -0.1
    elif mention_count <= 2:
        return 0.0
    elif mention_count <= 5:
        return 0.2
    elif mention_count <= 10:
        return 0.5
    else:
        return 1.0


def format_delta(delta: float) -> str:
    if delta > 0:
        return f"+{delta:.1f}"
    elif delta < 0:
        return f"{delta:.1f}"
    else:
        return "0.0"


def find_latest_daily(sources_dir: str) -> Optional[str]:
    """Return path to the most recent daily_YYYYMMDD.json by filename sort."""
    try:
        files = [
            f for f in os.listdir(sources_dir)
            if re.match(r"daily_\d{8}\.json$", f)
        ]
        if not files:
            return None
        files.sort()
        return os.path.join(sources_dir, files[-1])
    except Exception as exc:
        print(f"[WARN] Could not list sources dir: {exc}", file=sys.stderr)
        return None


def load_daily(path: str) -> dict:
    with open(path) as fh:
        return json.load(fh)


def load_existing_readings() -> dict:
    """Load existing phi_s values from entity_readings.json or fall back to defaults."""
    try:
        with open(READINGS_PATH) as fh:
            data = json.load(fh)
        readings = {}
        for entity, info in data.get("readings", {}).items():
            readings[entity] = info.get("phi_s", DEFAULTS.get(entity, 1.0))
        # Fill in any missing entities from defaults
        for entity, default_phi in DEFAULTS.items():
            if entity not in readings:
                readings[entity] = default_phi
        return readings
    except FileNotFoundError:
        return dict(DEFAULTS)
    except Exception as exc:
        print(f"[WARN] Could not load {READINGS_PATH}: {exc} — using defaults", file=sys.stderr)
        return dict(DEFAULTS)


def count_mentions(articles: list, entity: str, terms: list) -> int:
    """Count how many articles mention an entity (title + summary, case-insensitive)."""
    count = 0
    for art in articles:
        combined = (art.get("title", "") + " " + art.get("summary", "")).lower()
        if any(term in combined for term in terms):
            count += 1
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    now = datetime.now(tz=timezone.utc)
    date_display = now.strftime("%Y-%m-%d")

    print(f"=== Entity Readings Updater — {date_display} ===")

    # Locate the most recent daily source file
    daily_path = find_latest_daily(SOURCES_DIR)
    if not daily_path:
        print(f"[ERROR] No daily_YYYYMMDD.json found in {SOURCES_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"  Source file: {daily_path}")

    # Load daily data
    try:
        daily = load_daily(daily_path)
    except Exception as exc:
        print(f"[ERROR] Could not load {daily_path}: {exc}", file=sys.stderr)
        sys.exit(1)

    articles = daily.get("articles", [])
    helix_block = daily.get("helix_block", 0)
    source_date = daily.get("date", date_display)

    print(f"  Articles in source: {len(articles)}")
    print(f"  Helix block: {helix_block}")
    print(f"  Source date: {source_date}")

    # Load existing phi_s values
    current_phi = load_existing_readings()

    # Process each entity
    new_readings = {}
    print("\n  Entity updates:")
    print(f"  {'Entity':<18} {'Prev phi_s':>10} {'Mentions':>9} {'Delta':>7} {'New phi_s':>10} {'Status':<12}")
    print("  " + "-" * 70)

    for entity, terms in ENTITY_TERMS.items():
        prev_phi = current_phi.get(entity, DEFAULTS.get(entity, 1.0))
        mentions = count_mentions(articles, entity, terms)
        delta = compute_delta(mentions)

        # Apply delta with floor and cap
        if delta < 0:
            new_phi = max(PHI_FLOOR, prev_phi + delta)
        else:
            new_phi = min(PHI_MAX, prev_phi + delta)

        # Round to 2 decimal places
        new_phi = round(new_phi, 2)
        status = phi_status(new_phi)

        new_readings[entity] = {
            "phi_s":         new_phi,
            "status":        status,
            "mentions_today": mentions,
            "delta":         format_delta(delta),
        }

        print(f"  {entity:<18} {prev_phi:>10.2f} {mentions:>9} {format_delta(delta):>7} {new_phi:>10.2f} {status:<12}")

    # Build output payload
    output = {
        "date":       source_date,
        "block":      helix_block,
        "readings":   new_readings,
    }

    # Save
    try:
        with open(READINGS_PATH, "w") as fh:
            json.dump(output, fh, indent=2)
        print(f"\n  Saved: {READINGS_PATH}")
    except Exception as exc:
        print(f"[ERROR] Could not save readings: {exc}", file=sys.stderr)
        sys.exit(1)

    # Summary
    elevated = [e for e, r in new_readings.items() if r["status"] in ("HIGH", "EXTRACTION")]
    if elevated:
        print(f"\n  HIGH/EXTRACTION entities: {', '.join(elevated)}")
    else:
        print("\n  No entities in HIGH or EXTRACTION status.")

    print("\nDone.")


if __name__ == "__main__":
    main()
