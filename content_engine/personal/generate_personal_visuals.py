"""
generate_personal_visuals.py — Personal LinkedIn visual generator for Kiran Kaur.

Generates 1200x628px PNG visuals for Kiran's personal LinkedIn posts.
White/light theme. Clean minimal style.

Reads:
    content_engine/personal/posts/personal_posts_YYYYMMDD.json

Writes:
    content_engine/personal/visuals/personal_visual_YYYYMMDD_[id].png

Usage:
    python3 generate_personal_visuals.py
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
    import matplotlib.lines as mlines
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("[ERROR] matplotlib is not installed. Run: pip3 install matplotlib", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
POSTS_DIR   = "/Users/kiran/SETTLEMENT_LAYER_ADVISORY/content_engine/personal/posts"
VISUALS_DIR = "/Users/kiran/SETTLEMENT_LAYER_ADVISORY/content_engine/personal/visuals"

# ---------------------------------------------------------------------------
# Personal color palette (white/light theme)
# ---------------------------------------------------------------------------
BG         = "#ffffff"
NAVY       = "#1a1a2e"
AMBER      = "#e8930a"
MUTED      = "#6b7280"
LIGHT_GRAY = "#f8f9fa"
BORDER     = "#e5e7eb"

WATERMARK  = "Kiran Kaur | Eigenstate Research"
BRAND      = "Kiran Kaur"

FIG_W_PX = 1200
FIG_H_PX = 628
DPI      = 100
FIG_W_IN = FIG_W_PX / DPI   # 12.0
FIG_H_IN = FIG_H_PX / DPI   # 6.28

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_fig(bg_color: str = BG):
    """Create a blank figure with white background."""
    fig, ax = plt.subplots(figsize=(FIG_W_IN, FIG_H_IN), dpi=DPI)
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    return fig, ax


def _save(fig, path: str, bg_color: str = BG):
    """Save figure to path and close."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=bg_color)
    plt.close(fig)
    print(f"  Saved: {path}")


def _wrap(text: str, width: int) -> list[str]:
    return textwrap.wrap(text, width=width)


def _amber_left_bar(ax, bar_width: float = 0.006):
    """Draw a narrow amber rectangle on the left edge of the axes."""
    rect = patches.Rectangle(
        (0, 0), bar_width, 1.0,
        transform=ax.transAxes,
        color=AMBER,
        zorder=5,
        clip_on=False,
    )
    ax.add_patch(rect)


def _hline(ax, y: float, x0: float = 0.04, x1: float = 0.96,
           color: str = AMBER, lw: float = 1.2):
    """Draw a horizontal line across the axes at axes-fraction coordinates."""
    line = mlines.Line2D([x0, x1], [y, y],
                         transform=ax.transAxes,
                         color=color, linewidth=lw)
    ax.add_artist(line)


# ---------------------------------------------------------------------------
# Visual 1: line_chart
# ---------------------------------------------------------------------------

def make_line_chart(post: dict, out_path: str):
    """
    White background line chart.
    Reads data from post["chart_data"] if present; else renders a placeholder.
    Expected format:
        chart_data: {
            "labels": [...],
            "series": [
                {"label": "Primary", "values": [...]},
                {"label": "Compare", "values": [...]},   # optional
            ]
        }
    """
    chart_data = post.get("chart_data", {})
    labels = chart_data.get("labels", [])
    series = chart_data.get("series", [])
    title  = post.get("post_title") or post.get("post_text", "")[:80]
    source = post.get("source", "")

    fig, ax = _base_fig()
    ax.set_facecolor(BG)
    ax.patch.set_alpha(1)

    if series:
        primary = series[0]
        values  = primary.get("values", [])
        x       = list(range(len(values)))
        x_ticks = labels if labels else x

        # Primary line in amber
        ax.plot(x, values, color=AMBER, linewidth=2.2, zorder=3,
                label=primary.get("label", "Primary"))

        # Comparison lines in muted gray
        for comp in series[1:]:
            comp_vals = comp.get("values", [])
            ax.plot(list(range(len(comp_vals))), comp_vals,
                    color=MUTED, linewidth=1.4, linestyle="--", zorder=2,
                    label=comp.get("label", ""))

        ax.set_xticks(x[:len(x_ticks)])
        ax.set_xticklabels(x_ticks, rotation=0, fontsize=8, color=MUTED)

    else:
        # Placeholder: flat amber line
        ax.plot([0, 1], [0.5, 0.5], color=AMBER, linewidth=2,
                transform=ax.transAxes)
        ax.text(0.5, 0.5, "No chart data provided",
                transform=ax.transAxes, ha="center", va="center",
                color=MUTED, fontsize=12)

    # Minimal clean axes
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(BORDER)
    ax.spines["left"].set_color(BORDER)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.yaxis.grid(True, color=LIGHT_GRAY, linewidth=0.6)
    ax.set_facecolor(BG)

    # Title top left
    if title:
        title_lines = _wrap(title, 70)
        for i, tl in enumerate(title_lines[:2]):
            ax.text(0.01, 1.04 - i * 0.06, tl,
                    transform=ax.transAxes,
                    color=NAVY, fontsize=13, fontweight="bold",
                    ha="left", va="bottom")

    # Legend (if multiple series)
    if series and len(series) > 1:
        ax.legend(fontsize=8, frameon=False,
                  labelcolor=MUTED, loc="upper right")

    # Watermark bottom right
    ax.text(0.99, -0.07, WATERMARK,
            transform=ax.transAxes,
            color=MUTED, fontsize=8, ha="right", va="top")

    if source:
        ax.text(0.99, -0.12, f"Source: {source}",
                transform=ax.transAxes,
                color=MUTED, fontsize=7, ha="right", va="top")

    fig.tight_layout()
    _save(fig, out_path)


# ---------------------------------------------------------------------------
# Visual 2: bar_chart
# ---------------------------------------------------------------------------

def make_bar_chart(post: dict, out_path: str):
    """
    White background vertical bar chart with amber bars.
    Reads post["chart_data"] if present.
    """
    chart_data = post.get("chart_data", {})
    labels = chart_data.get("labels", [])
    series = chart_data.get("series", [])
    title  = post.get("post_title") or post.get("post_text", "")[:80]
    source = post.get("source", "")

    fig, ax = _base_fig()

    if series:
        primary = series[0]
        values  = primary.get("values", [])
        x_labels = labels if labels else [str(i) for i in range(len(values))]
        x = list(range(len(values)))

        ax.bar(x, values, color=AMBER, width=0.55, zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels(x_labels, rotation=30, ha="right",
                           fontsize=9, color=NAVY)

        # Value labels on top of bars
        for xi, v in zip(x, values):
            ax.text(xi, v, f"{v:g}", ha="center", va="bottom",
                    color=NAVY, fontsize=8, fontweight="bold")
    else:
        ax.text(0.5, 0.5, "No chart data provided",
                transform=ax.transAxes, ha="center", va="center",
                color=MUTED, fontsize=12)

    # Clean axes
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(BORDER)
    ax.spines["left"].set_color(BORDER)
    ax.tick_params(axis="y", colors=MUTED, labelsize=8)
    ax.yaxis.grid(True, color=LIGHT_GRAY, linewidth=0.6, zorder=0)
    ax.set_facecolor(BG)

    if title:
        title_lines = _wrap(title, 70)
        for i, tl in enumerate(title_lines[:2]):
            ax.text(0.01, 1.04 - i * 0.06, tl,
                    transform=ax.transAxes,
                    color=NAVY, fontsize=13, fontweight="bold",
                    ha="left", va="bottom")

    ax.text(0.99, -0.12, WATERMARK,
            transform=ax.transAxes,
            color=MUTED, fontsize=8, ha="right", va="top")

    if source:
        ax.text(0.99, -0.17, f"Source: {source}",
                transform=ax.transAxes,
                color=MUTED, fontsize=7, ha="right", va="top")

    fig.tight_layout()
    _save(fig, out_path)


# ---------------------------------------------------------------------------
# Visual 3: stat_card
# ---------------------------------------------------------------------------

def make_stat_card(post: dict, out_path: str):
    post_text = post.get("post_text", "")
    source    = post.get("source", "")
    lines     = [l.strip() for l in post_text.strip().splitlines() if l.strip()]

    stat_line    = lines[0] if lines else "—"
    context_text = " ".join(lines[1:4]) if len(lines) > 1 else ""

    # Extract big number
    number_match = re.search(
        r"[\$€£]?[\d,\.]+\s*(?:%|B|M|T|K|trillion|billion|million|percent)?",
        stat_line,
    )
    big_number = number_match.group(0).strip() if number_match else stat_line[:30]
    context_label = stat_line.replace(big_number, "").strip(" ,:—-") if number_match else ""
    if not context_label:
        context_label = context_text[:120]

    fig, ax = _base_fig()
    ax.axis("off")

    # Amber vertical accent line left edge (4px = ~0.003 axes units at this scale)
    _amber_left_bar(ax, bar_width=0.005)

    # "Kiran Kaur" top right in amber
    ax.text(0.97, 0.93, BRAND,
            transform=ax.transAxes,
            color=AMBER, fontsize=9, ha="right", va="top")

    # Large number centered, dark navy
    ax.text(0.5, 0.62, big_number,
            transform=ax.transAxes,
            color=NAVY, fontsize=52, fontweight="bold",
            ha="center", va="center")

    # Horizontal amber rule below number
    _hline(ax, y=0.46, x0=0.15, x1=0.85, color=AMBER, lw=1.5)

    # Context text below rule, muted gray, size 13
    wrapped = _wrap(context_label, 60)
    for i, wline in enumerate(wrapped[:4]):
        ax.text(0.5, 0.40 - i * 0.08, wline,
                transform=ax.transAxes,
                color=MUTED, fontsize=13, ha="center", va="top")

    # Source bottom right in muted
    if source:
        ax.text(0.97, 0.04, f"Source: {source}",
                transform=ax.transAxes,
                color=MUTED, fontsize=8, ha="right", va="bottom")

    _save(fig, out_path)


# ---------------------------------------------------------------------------
# Visual 4: quote_card
# ---------------------------------------------------------------------------

def make_quote_card(post: dict, out_path: str):
    post_text   = post.get("post_text", "")
    attribution = post.get("attribution") or post.get("source", "")
    lines       = [l.strip() for l in post_text.strip().splitlines() if l.strip()]
    quote_text  = " ".join(lines[:6]) if lines else "The structural shift is already underway."

    fig, ax = _base_fig()
    ax.axis("off")

    # Large amber quotation mark top left
    ax.text(0.04, 0.96, "\u201c",
            transform=ax.transAxes,
            color=AMBER, fontsize=64, alpha=0.40,
            ha="left", va="top")

    # Quote text centered, dark navy
    wrapped = _wrap(quote_text, 60)
    n = len(wrapped[:7])
    y_start = 0.55 + (n * 0.07) / 2
    for i, wline in enumerate(wrapped[:7]):
        ax.text(0.5, y_start - i * 0.09, wline,
                transform=ax.transAxes,
                color=NAVY, fontsize=13, ha="center", va="top")

    # Attribution below in muted
    if attribution:
        attr_y = y_start - n * 0.09 - 0.06
        ax.text(0.5, attr_y, f"-- {attribution}",
                transform=ax.transAxes,
                color=MUTED, fontsize=10, ha="center", va="top",
                fontstyle="italic")

    # Amber rule at bottom
    _hline(ax, y=0.10, x0=0.10, x1=0.90, color=AMBER, lw=1.0)

    _save(fig, out_path)


# ---------------------------------------------------------------------------
# Visual 5: weekly_wrap
# ---------------------------------------------------------------------------

def make_weekly_wrap(post: dict, out_path: str):
    post_text = post.get("post_text", "")
    lines     = [l.strip() for l in post_text.strip().splitlines() if l.strip()]

    # Separate header from list items
    items = []
    header = ""
    for line in lines:
        # Strip leading numbers/bullets
        cleaned = re.sub(r"^[\d]+[\.\)]\s*", "", line)
        cleaned = re.sub(r"^[-*\u2022]\s*", "", cleaned)
        if not header and cleaned:
            header = cleaned
        elif cleaned:
            items.append(cleaned)

    if not items:
        items = lines[1:6]

    fig, ax = _base_fig()
    ax.axis("off")

    # Amber accent bar left edge
    _amber_left_bar(ax, bar_width=0.006)

    # "FIVE THINGS" header in amber, bold
    ax.text(0.06, 0.93, "FIVE THINGS",
            transform=ax.transAxes,
            color=AMBER, fontsize=14, fontweight="bold",
            ha="left", va="top")

    # Header / subheadline in navy
    if header:
        hl_wrapped = _wrap(header, 65)
        for i, wline in enumerate(hl_wrapped[:2]):
            ax.text(0.06, 0.82 - i * 0.08, wline,
                    transform=ax.transAxes,
                    color=NAVY, fontsize=12, fontweight="bold",
                    ha="left", va="top")

    # Numbered list items in navy
    item_y_start = 0.65
    for i, item in enumerate(items[:5]):
        item_wrapped = _wrap(item, 72)
        for j, wline in enumerate(item_wrapped[:2]):
            prefix = f"  {i + 1}.  " if j == 0 else "       "
            ax.text(0.06, item_y_start - i * 0.115 - j * 0.06, prefix + wline,
                    transform=ax.transAxes,
                    color=NAVY, fontsize=11, ha="left", va="top")

    # Bottom horizontal amber rule
    _hline(ax, y=0.10, x0=0.04, x1=0.96, color=AMBER, lw=1.0)

    # Watermark bottom right
    ax.text(0.97, 0.05, WATERMARK,
            transform=ax.transAxes,
            color=MUTED, fontsize=8, ha="right", va="bottom")

    _save(fig, out_path)


# ---------------------------------------------------------------------------
# Visual dispatcher
# ---------------------------------------------------------------------------

VISUAL_MAKERS = {
    "line_chart":  make_line_chart,
    "bar_chart":   make_bar_chart,
    "stat_card":   make_stat_card,
    "quote_card":  make_quote_card,
    "weekly_wrap": make_weekly_wrap,
}

def make_visual(post: dict, date_str: str):
    visual_type = post.get("visual", "stat_card")
    post_id     = post.get("id", 0)

    out_path = os.path.join(
        VISUALS_DIR,
        f"personal_visual_{date_str}_{post_id}.png",
    )

    maker = VISUAL_MAKERS.get(visual_type)
    if maker is None:
        print(f"  [WARN] Unknown visual type '{visual_type}' for post {post_id} — defaulting to stat_card.",
              file=sys.stderr)
        maker = make_stat_card

    print(f"\n[Post {post_id}] visual={visual_type}")

    # line_chart and bar_chart take only (post, out_path)
    # stat_card, quote_card, weekly_wrap also take only (post, out_path)
    maker(post, out_path)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_posts(date_str: str) -> dict:
    path = os.path.join(POSTS_DIR, f"personal_posts_{date_str}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Personal posts file not found: {path}")
    with open(path) as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    now      = datetime.now(tz=timezone.utc)
    date_str = now.strftime("%Y%m%d")

    print(f"=== Personal Visual Generator — {now.strftime('%Y-%m-%d')} ===")

    try:
        posts_payload = load_posts(date_str)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    posts = posts_payload.get("posts", [])
    if not posts:
        print("[ERROR] No posts found in payload.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(VISUALS_DIR, exist_ok=True)

    print(f"\nGenerating {len(posts)} personal visual(s)...")
    for post in posts:
        try:
            make_visual(post, date_str)
        except Exception as exc:
            print(f"  [ERROR] Failed to generate visual for post {post.get('id')}: {exc}",
                  file=sys.stderr)

    print(f"\nDone. Visuals saved to: {VISUALS_DIR}")


if __name__ == "__main__":
    main()
