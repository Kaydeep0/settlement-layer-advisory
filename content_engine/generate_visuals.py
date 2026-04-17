"""
generate_visuals.py — Settlement Layer Advisory LinkedIn visual generator.

Generates 1200x628px PNG visuals for each LinkedIn post using matplotlib + PIL.

Reads:
    content_engine/posts/posts_YYYYMMDD.json
    content_engine/sources/daily_YYYYMMDD.json

Writes:
    content_engine/visuals/visual_YYYYMMDD_[id].png

Usage:
    python3 generate_visuals.py
"""

import json
import os
import re
import sys
import textwrap
from datetime import datetime, timezone

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("[ERROR] matplotlib is not installed. Run: pip3 install matplotlib", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
POSTS_DIR   = "/Users/kiran/SETTLEMENT_LAYER_ADVISORY/content_engine/posts"
SOURCES_DIR = "/Users/kiran/SETTLEMENT_LAYER_ADVISORY/content_engine/sources"
VISUALS_DIR = "/Users/kiran/SETTLEMENT_LAYER_ADVISORY/content_engine/visuals"

# ---------------------------------------------------------------------------
# SLA Color palette
# ---------------------------------------------------------------------------
BG_DARK          = "#0a0a0f"
AMBER            = "#e8930a"
CYAN             = "#4fc3c3"
NAVY             = "#1a1a2e"
WHITE            = "#f8f8f8"
MUTED            = "#6b7280"
ELEVATED_COLOR   = AMBER
HIGH_COLOR       = "#ff6b35"
STABLE_COLOR     = CYAN
EXTRACTION_COLOR = "#ff2244"

STATUS_COLORS = {
    "STABLE":     STABLE_COLOR,
    "ELEVATED":   ELEVATED_COLOR,
    "HIGH":       HIGH_COLOR,
    "EXTRACTION": EXTRACTION_COLOR,
}

FIG_W_PX = 1200
FIG_H_PX = 628
DPI      = 100
FIG_W_IN = FIG_W_PX / DPI   # 12.0
FIG_H_IN = FIG_H_PX / DPI   # 6.28

FOOTER_TEXT   = "settlementlayeradvisory.com"
BRAND_SHORT   = "Settlement Layer Advisory"
EIGENSTATE    = "EIGENSTATE RESEARCH"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_fig():
    """Create a blank figure with BG_DARK background and a single axes."""
    fig, ax = plt.subplots(figsize=(FIG_W_IN, FIG_H_IN), dpi=DPI)
    fig.patch.set_facecolor(BG_DARK)
    ax.set_facecolor(BG_DARK)
    return fig, ax


def _save(fig, path: str):
    """Save figure to path and close it."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=BG_DARK)
    plt.close(fig)
    print(f"  Saved: {path}")


def _wrap(text: str, width: int) -> list[str]:
    """Wrap text to width, return list of lines."""
    return textwrap.wrap(text, width=width)


def _amber_top_rule(fig):
    """Draw full-width amber accent line at very top of figure (figure coords)."""
    line = matplotlib.lines.Line2D(
        [0, 1], [1, 1],
        transform=fig.transFigure,
        color=AMBER,
        linewidth=2,
        solid_capstyle="butt",
    )
    fig.add_artist(line)


# ---------------------------------------------------------------------------
# Visual 1: signal_chart — horizontal bar chart of Phi_S readings
# ---------------------------------------------------------------------------

def make_signal_chart(post: dict, sources: dict, date_str: str, out_path: str):
    engine_readings = sources.get("engine_readings", {})
    helix_block     = sources.get("helix_block", 0)
    date_display    = sources.get("date", date_str)

    if not engine_readings:
        print("  [WARN] No engine_readings in sources — skipping signal_chart.", file=sys.stderr)
        return

    entities  = list(engine_readings.keys())
    phi_vals  = [float(engine_readings[e].get("phi_s", 0)) for e in entities]
    statuses  = [engine_readings[e].get("status", "STABLE") for e in entities]
    bar_colors = [STATUS_COLORS.get(s, CYAN) for s in statuses]

    fig, ax = plt.subplots(figsize=(FIG_W_IN, FIG_H_IN), dpi=DPI)
    fig.patch.set_facecolor(BG_DARK)
    ax.set_facecolor(BG_DARK)

    # --- Amber top rule ---
    _amber_top_rule(fig)

    # --- Horizontal bars ---
    y_positions = range(len(entities))
    bars = ax.barh(
        list(y_positions),
        phi_vals,
        color=bar_colors,
        height=0.55,
        left=0,
        zorder=3,
    )

    # Entity labels left of bars
    for i, entity in enumerate(entities):
        ax.text(
            -0.05, i,
            entity,
            ha="right",
            va="center",
            color=WHITE,
            fontsize=10,
            fontfamily="monospace",
        )

    # Phi_S values at end of each bar
    for i, (phi, bar) in enumerate(zip(phi_vals, bars)):
        ax.text(
            phi + 0.03, i,
            f"{phi:.2f}",
            ha="left",
            va="center",
            color=WHITE,
            fontsize=9,
            fontfamily="monospace",
        )

    # Grid lines (x only, subtle)
    ax.xaxis.grid(True, color="#1e1e2e", linewidth=0.7, linestyle="--", zorder=0)
    ax.yaxis.grid(False)

    # Hide y ticks and labels (we use custom entity labels)
    ax.set_yticks([])
    ax.set_yticklabels([])
    ax.tick_params(axis="x", colors=MUTED, labelsize=8)

    # Remove spines except bottom
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#1e1e2e")

    # X axis range: leave headroom for labels
    max_phi = max(phi_vals) if phi_vals else 1
    ax.set_xlim(-0.15 * max_phi - 0.5, max_phi * 1.25)
    ax.set_ylim(-0.7, len(entities) - 0.3)

    # --- Title block (top left, inside axes using figure text) ---
    fig.text(0.07, 0.93, EIGENSTATE,
             color=AMBER, fontsize=16, fontweight="bold",
             ha="left", va="top")

    subtitle = f"Field Readings  |  {date_display}  |  Base mainnet block {helix_block}"
    fig.text(0.07, 0.86, subtitle,
             color=MUTED, fontsize=9, ha="left", va="top")

    # --- Footer ---
    fig.text(0.97, 0.03, FOOTER_TEXT,
             color=MUTED, fontsize=8, ha="right", va="bottom")

    fig.tight_layout(rect=[0.12, 0.06, 0.98, 0.84])
    _save(fig, out_path)


# ---------------------------------------------------------------------------
# Visual 2: stat_card
# ---------------------------------------------------------------------------

def make_stat_card(post: dict, sources: dict, date_str: str, out_path: str):
    post_text = post.get("post_text", "")
    source    = post.get("source", "")
    lines     = [l.strip() for l in post_text.strip().splitlines() if l.strip()]

    # Extract first line as stat/headline; rest as context
    stat_line    = lines[0] if lines else "—"
    context_text = " ".join(lines[1:4]) if len(lines) > 1 else ""

    # Try to isolate a big number from stat_line
    number_match = re.search(r"[\$€£]?[\d,\.]+\s*(?:%|B|M|T|K|trillion|billion|million|percent)?", stat_line)
    big_number = number_match.group(0).strip() if number_match else stat_line[:30]
    context_label = stat_line.replace(big_number, "").strip(" ,:—-") if number_match else context_text[:100]
    if not context_label:
        context_label = context_text[:100]

    fig, ax = _base_fig()
    ax.axis("off")

    # Top right brand label
    ax.text(0.97, 0.95, BRAND_SHORT,
            transform=ax.transAxes,
            color=AMBER, fontsize=9, ha="right", va="top")

    # Large number — centered
    ax.text(0.5, 0.60, big_number,
            transform=ax.transAxes,
            color=AMBER, fontsize=52, fontweight="bold",
            ha="center", va="center")

    # Amber horizontal rule below number
    rule_y = 0.46
    rule = matplotlib.lines.Line2D([0.15, 0.85], [rule_y, rule_y],
                                   transform=ax.transAxes,
                                   color=AMBER, linewidth=1.5)
    ax.add_artist(rule)

    # Context text below rule (wrapped at 60 chars)
    wrapped_context = _wrap(context_label, 60)
    for i, wline in enumerate(wrapped_context[:4]):
        ax.text(0.5, rule_y - 0.08 - i * 0.07, wline,
                transform=ax.transAxes,
                color=WHITE, fontsize=14, ha="center", va="top")

    # Source attribution bottom right
    if source:
        ax.text(0.97, 0.04, f"Source: {source}",
                transform=ax.transAxes,
                color=MUTED, fontsize=9, ha="right", va="bottom")

    _amber_top_rule(fig)
    _save(fig, out_path)


# ---------------------------------------------------------------------------
# Visual 3: regulatory_card
# ---------------------------------------------------------------------------

def make_regulatory_card(post: dict, sources: dict, date_str: str, out_path: str):
    post_text    = post.get("post_text", "")
    source       = post.get("source", "")
    date_display = sources.get("date", date_str)
    lines        = [l.strip() for l in post_text.strip().splitlines() if l.strip()]

    headline  = lines[0] if lines else "Regulatory Signal"
    body_text = " ".join(lines[1:6]) if len(lines) > 1 else ""

    fig, ax = _base_fig()
    ax.axis("off")

    # Amber vertical accent bar, left edge
    bar_rect = patches.Rectangle(
        (0, 0), 0.012, 1.0,
        transform=ax.transAxes,
        color=AMBER, zorder=4,
    )
    ax.add_patch(bar_rect)

    # "REGULATORY SIGNAL" label top left
    ax.text(0.04, 0.93, "R E G U L A T O R Y   S I G N A L",
            transform=ax.transAxes,
            color=AMBER, fontsize=11, fontweight="bold",
            ha="left", va="top")

    # Date top right
    ax.text(0.97, 0.93, date_display,
            transform=ax.transAxes,
            color=MUTED, fontsize=9, ha="right", va="top")

    # Headline — white, bold, wrapped
    headline_wrapped = _wrap(headline, 55)
    for i, wline in enumerate(headline_wrapped[:3]):
        ax.text(0.04, 0.80 - i * 0.10, wline,
                transform=ax.transAxes,
                color=WHITE, fontsize=18, fontweight="bold",
                ha="left", va="top")

    # Body text — muted, wrapped
    body_wrapped = _wrap(body_text, 75)
    body_start_y = 0.80 - len(headline_wrapped[:3]) * 0.10 - 0.08
    for i, wline in enumerate(body_wrapped[:6]):
        ax.text(0.04, body_start_y - i * 0.08, wline,
                transform=ax.transAxes,
                color=MUTED, fontsize=11, ha="left", va="top")

    # Source bottom right
    if source:
        ax.text(0.97, 0.06, f"Source: {source}",
                transform=ax.transAxes,
                color=AMBER, fontsize=9, ha="right", va="bottom")

    _amber_top_rule(fig)
    _save(fig, out_path)


# ---------------------------------------------------------------------------
# Visual 4: quote_card
# ---------------------------------------------------------------------------

def make_quote_card(post: dict, sources: dict, date_str: str, out_path: str):
    post_text = post.get("post_text", "")
    lines = [l.strip() for l in post_text.strip().splitlines() if l.strip()]
    # Use full post or best paragraph
    quote_text = " ".join(lines[:5]) if lines else "Settlement clarity is a competitive advantage."

    fig, ax = _base_fig()
    ax.axis("off")

    # Large amber quotation mark top left (partially transparent)
    ax.text(0.04, 0.97, "\u201c",
            transform=ax.transAxes,
            color=AMBER, fontsize=72, alpha=0.35,
            ha="left", va="top")

    # Rule text centered and wrapped
    quote_wrapped = _wrap(quote_text, 60)
    n_lines = len(quote_wrapped[:7])
    y_start = 0.55 + (n_lines * 0.065) / 2  # vertically center block
    for i, wline in enumerate(quote_wrapped[:7]):
        ax.text(0.5, y_start - i * 0.09, wline,
                transform=ax.transAxes,
                color=WHITE, fontsize=14, ha="center", va="top")

    # Brand bottom right
    ax.text(0.97, 0.06, BRAND_SHORT,
            transform=ax.transAxes,
            color=AMBER, fontsize=10, ha="right", va="bottom")

    _amber_top_rule(fig)
    _save(fig, out_path)


# ---------------------------------------------------------------------------
# Visual 5: trend_card
# ---------------------------------------------------------------------------

def make_trend_card(post: dict, sources: dict, date_str: str, out_path: str):
    post_text = post.get("post_text", "")
    lines = [l.strip() for l in post_text.strip().splitlines() if l.strip()]

    # "TREND SIGNAL" label
    # Bullet lines: any line starting with a digit, dash, bullet, or data signal
    bullet_lines = []
    for line in lines[1:]:
        stripped = line.lstrip("*-•\u2022 ")
        if stripped:
            bullet_lines.append(stripped)

    if not bullet_lines:
        bullet_lines = lines[1:6]

    fig, ax = _base_fig()
    ax.axis("off")

    # "TREND SIGNAL" top left
    ax.text(0.04, 0.93, "TREND SIGNAL",
            transform=ax.transAxes,
            color=AMBER, fontsize=13, fontweight="bold",
            ha="left", va="top")

    # Headline (first line)
    headline = lines[0] if lines else ""
    if headline:
        hl_wrapped = _wrap(headline, 65)
        for i, wline in enumerate(hl_wrapped[:2]):
            ax.text(0.04, 0.82 - i * 0.08, wline,
                    transform=ax.transAxes,
                    color=WHITE, fontsize=13, fontweight="bold",
                    ha="left", va="top")

    # Bullet points
    bullet_y_start = 0.62
    for i, bline in enumerate(bullet_lines[:6]):
        wrapped_b = _wrap(bline, 72)
        for j, wline in enumerate(wrapped_b[:2]):
            prefix = "  " if j > 0 else "  \u25aa "
            ax.text(0.04, bullet_y_start - i * 0.10 - j * 0.06, prefix + wline,
                    transform=ax.transAxes,
                    color=WHITE, fontsize=12, ha="left", va="top")

    # Bottom amber rule + footer
    rule_y = 0.10
    rule = matplotlib.lines.Line2D([0.04, 0.96], [rule_y, rule_y],
                                   transform=ax.transAxes,
                                   color=AMBER, linewidth=1.2)
    ax.add_artist(rule)

    ax.text(0.97, 0.05, FOOTER_TEXT,
            transform=ax.transAxes,
            color=MUTED, fontsize=8, ha="right", va="bottom")

    _amber_top_rule(fig)
    _save(fig, out_path)


# ---------------------------------------------------------------------------
# Visual dispatcher
# ---------------------------------------------------------------------------

VISUAL_MAKERS = {
    "signal_chart":    make_signal_chart,
    "stat_card":       make_stat_card,
    "regulatory_card": make_regulatory_card,
    "quote_card":      make_quote_card,
    "trend_card":      make_trend_card,
}


def make_visual(post: dict, sources: dict, date_str: str):
    visual_type = post.get("visual", "regulatory_card")
    post_id     = post.get("id", 0)

    out_path = os.path.join(
        VISUALS_DIR,
        f"visual_{date_str}_{post_id}.png",
    )

    maker = VISUAL_MAKERS.get(visual_type)
    if maker is None:
        print(f"  [WARN] Unknown visual type '{visual_type}' for post {post_id} — defaulting to regulatory_card.",
              file=sys.stderr)
        maker = make_regulatory_card

    print(f"\n[Post {post_id}] visual={visual_type}")
    maker(post, sources, date_str, out_path)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_posts(date_str: str) -> dict:
    path = os.path.join(POSTS_DIR, f"posts_{date_str}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Posts file not found: {path}")
    with open(path) as fh:
        return json.load(fh)


def load_sources(date_str: str) -> dict:
    path = os.path.join(SOURCES_DIR, f"daily_{date_str}.json")
    if not os.path.exists(path):
        print(f"[WARN] Sources file not found: {path}. Engine readings will be empty.", file=sys.stderr)
        return {}
    with open(path) as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    now      = datetime.now(tz=timezone.utc)
    date_str = now.strftime("%Y%m%d")

    print(f"=== Settlement Layer Advisory — Visual Generator {now.strftime('%Y-%m-%d')} ===")

    # Load posts
    try:
        posts_payload = load_posts(date_str)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    posts = posts_payload.get("posts", [])
    if not posts:
        print("[ERROR] No posts found in payload.", file=sys.stderr)
        sys.exit(1)

    # Load sources (for engine_readings / helix_block)
    sources = load_sources(date_str)

    os.makedirs(VISUALS_DIR, exist_ok=True)

    print(f"\nGenerating {len(posts)} visual(s)...")
    for post in posts:
        try:
            make_visual(post, sources, date_str)
        except Exception as exc:
            print(f"  [ERROR] Failed to generate visual for post {post.get('id')}: {exc}", file=sys.stderr)

    print(f"\nDone. Visuals saved to: {VISUALS_DIR}")


if __name__ == "__main__":
    main()
