#!/usr/bin/env python3
"""
Settlement Layer Advisory + Kiran Kaur Personal
Combined Master Content Briefing Orchestrator

Runs both pipelines and merges output into a single master briefing.
"""

import subprocess
import sys
import os
import json
import datetime

BASE     = os.path.dirname(os.path.abspath(__file__))
PERSONAL = os.path.join(BASE, "personal")
NOW      = datetime.datetime.utcnow().strftime("%H:%M")

def _detect_today() -> str:
    """Use UTC date (matches sub-script convention). Fall back to local."""
    return datetime.datetime.utcnow().strftime("%Y%m%d")

def _today_display(ymd: str) -> str:
    d = datetime.datetime.strptime(ymd, "%Y%m%d")
    return d.strftime("%B %d, %Y")

def _day_name(ymd: str) -> str:
    d = datetime.datetime.strptime(ymd, "%Y%m%d")
    return d.strftime("%A")

# BRIEFING_PATH set dynamically in main() after detecting TODAY


# ── Helpers ───────────────────────────────────────────────────────────────────

def run(label: str, script: str, cwd: str = BASE) -> bool:
    print(f"\n{'='*64}")
    print(f"  {label}")
    print(f"{'='*64}")
    r = subprocess.run([sys.executable, script], cwd=cwd)
    if r.returncode != 0:
        print(f"[WARN] {label} exited {r.returncode} — continuing")
        return False
    return True


def load_json(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def load_sla_sources() -> dict:
    p = os.path.join(BASE, "sources", f"daily_{TODAY}.json")
    return load_json(p)


def load_sla_posts() -> dict:
    p = os.path.join(BASE, "posts", f"posts_{TODAY}.json")
    return load_json(p)


def load_personal_sources() -> dict:
    p = os.path.join(PERSONAL, "sources", f"personal_{TODAY}.json")
    return load_json(p)


def load_personal_posts() -> dict:
    p = os.path.join(PERSONAL, "posts", f"personal_posts_{TODAY}.json")
    return load_json(p)


# ── Section builders ─────────────────────────────────────────────────────────

def section_wfp(er_path: str = None) -> str:
    """WFP verification confidence section for MASTER_BRIEFING."""
    if er_path is None:
        er_path = os.path.join(BASE, "entity_readings.json")
    try:
        er = json.loads(open(er_path).read())
    except Exception:
        return "## WFP VERIFICATION CONFIDENCE\n\n*entity_readings.json not found — run entity_readings_updater.py.*"

    wfp_score = er.get("wfp_score")
    wfp_block = er.get("wfp_block")
    lines = ["## WFP VERIFICATION CONFIDENCE\n"]
    if wfp_score is not None:
        lines.append(f"V (latest helix commit) = **{wfp_score:.1%}**")
        if wfp_block:
            lines.append(f"Helix block: {wfp_block}")
        lines.append("")
        lines.append("Component breakdown (WFP v2.1):")
        lines.append("- W_provenance: 0.98 (blockchain — immutable timestamp)")
        lines.append("- Fidelity: computed from wallet track record + PT at commit time")
        lines.append("- D: near-zero decay (on-chain anchor, on_chain_commit lambda = 0.001/yr)")
        lines.append("- Anchor_boost: 1.15 (HelixHash anchor_strength = 1.0)")
        lines.append("")
        if wfp_score >= 0.90:
            lines.append("Status: HIGH CONFIDENCE — institutional-grade verification.")
        elif wfp_score >= 0.75:
            lines.append("Status: STRONG — above licensed professional threshold.")
        elif wfp_score >= 0.60:
            lines.append("Status: MODERATE — above journalist primary threshold.")
        else:
            lines.append("Status: DEVELOPING — chain history building track record.")
    else:
        lines.append("*WFP score not yet computed — run entity_readings_updater.py.*")
    return "\n".join(lines)


def section_eigenstate(src: dict) -> str:
    readings = src.get("engine_readings", {})
    parkash  = src.get("parkash", {})
    block    = src.get("helix_block", "N/A")

    lines = ["## EIGENSTATE RESEARCH READINGS\n"]
    if readings:
        lines.append("| Entity | Phi_S | Status |")
        lines.append("|--------|-------|--------|")
        for entity, data in readings.items():
            phi = data.get("phi_s", "N/A")
            st  = data.get("status", "N/A")
            lines.append(f"| {entity} | {phi} | {st} |")
        lines.append("")
        if parkash:
            pt  = parkash.get("PT", "N/A")
            k   = parkash.get("kappa", "N/A")
            cov = parkash.get("coverage", 0)
            lines.append(f"PT: {pt} | kappa: {k} | Coverage: {cov*100:.1f}%")
        lines.append(f"Helix Block: {block}")
    else:
        lines.append("*Engine readings not available — run scan_sources.py first.*")
    return "\n".join(lines)


def section_posts(posts_data: dict, pipeline: str, today: str) -> str:
    posts = posts_data.get("posts", [])
    if not posts:
        return f"*No {pipeline} posts generated today.*"

    TIMES = {1: "08:00 AM", 2: "11:00 AM", 3: "01:00 PM", 4: "04:00 PM", 5: "07:00 PM"}
    P_TIMES = {1: "08:30 AM", 2: "12:00 PM", 3: "03:00 PM", 4: "06:00 PM", 5: "09:00 PM"}
    time_map = P_TIMES if pipeline == "personal" else TIMES

    if pipeline == "sla":
        vis_base = f"visuals/visual_{today}_"
    else:
        vis_base = f"personal/visuals/personal_visual_{today}_"

    sections = []
    for p in posts:
        pid   = p.get("id", "?")
        tpl   = p.get("template", "?")
        ptype = p.get("type", "").replace("_", " ").title()
        src   = p.get("source", "")
        tags  = " ".join(p.get("hashtags", []))
        chars = p.get("character_count", "?")
        text  = p.get("post_text", "*(post text missing)*")
        t     = time_map.get(pid, "")
        vis   = f"{vis_base}{pid}.png"

        sections.append(
            f"### Post {pid}  [{t}]\n"
            f"**Template:** {tpl} — {ptype}  \n"
            f"**Source:** {src}  \n"
            f"**Visual:** {vis}  \n"
            f"**Hashtags:** {tags}  \n"
            f"**Characters:** {chars}\n\n"
            f"{text}\n"
        )
    return "\n---\n\n".join(sections)


def section_watchlist(personal_src: dict) -> str:
    wl = personal_src.get("watch_list", {})
    if not wl:
        return "*Watch list not available.*"

    def flag(key: str, label: str) -> str:
        found = wl.get(key, False)
        mark  = "NEW CONTENT FOUND" if found else "nothing new today"
        return f"- {label}: {mark}"

    return "\n".join([
        flag("lyn_alden_new",   "Lyn Alden"),
        flag("howard_marks_new","Howard Marks"),
        flag("veritasium_new",  "Veritasium"),
        flag("imf_new",         "IMF"),
        flag("fed_speech_new",  "Federal Reserve speeches"),
    ])


def section_conversations(pipeline: str) -> str:
    if pipeline == "sla":
        return """\
### SLA Page (3 conversations)

1. **#GENIUSAct** — Senate timeline pressure on stablecoin issuers. Angle: reserve attestation infrastructure gap.
2. **#TokenizedAssets** — Institutional AUM crossing new thresholds. Angle: which compliance structures are absorbing the capital?
3. **#RWA** — SEC jurisdictional overlap with CFTC on custodied tokenized securities. Angle: where do your obligations sit?"""
    else:
        lines = [
            "### Personal Page (5 conversations)",
            "",
            "1. **#Macro** — Central bank policy divergence. Suggested comment: "
            '"The gap between Fed and ECB posture is the largest it has been since 2015. '
            'That spread is not priced into private credit yet."',
            "2. **#FixedIncome** — Duration risk in the current rate environment. Suggested comment: "
            '"Most institutional allocators are still treating this as a rate cycle. '
            'It looks more like a structural regime shift."',
            "3. **#PrivateCredit** — Capital flowing into direct lending. Suggested comment: "
            '"The move to private credit is real but the infrastructure to verify borrower '
            'compliance at scale is not keeping up."',
            "4. **#CapitalMarkets** — IPO window and liquidity conditions. Suggested comment: "
            '"The denominator effect from 2022 has not fully resolved. Family offices are still '
            'marking to model in places where the exit is unclear."',
            "5. **#DigitalAssets** — Institutional on-ramp infrastructure. Suggested comment: "
            '"What I watch is not price. It is how fast the compliance layer is being built '
            'behind the capital flows."',
        ]
        return "\n".join(lines)


def section_sources_summary(sla_src: dict, personal_src: dict) -> str:
    sla_arts      = sla_src.get("articles", [])
    personal_arts = personal_src.get("articles", [])
    sla_failed    = sla_src.get("failed_feeds", [])
    p_failed      = personal_src.get("failed_feeds", [])
    sla_total     = sla_src.get("total_scanned", len(sla_arts))
    p_total       = personal_src.get("total_scanned", len(personal_arts))

    lines = [
        f"**SLA pipeline:** {sla_total} articles scanned, {len(sla_arts)} kept",
        f"**Personal pipeline:** {p_total} articles scanned, {len(personal_arts)} kept",
        f"**Combined:** {sla_total + p_total} articles scanned, "
        f"{len(sla_arts) + len(personal_arts)} kept",
        "",
    ]
    if sla_failed:
        lines.append(f"SLA failed feeds: {', '.join(sla_failed)}")
    if p_failed:
        lines.append(f"Personal failed feeds: {', '.join(p_failed)}")

    if sla_arts:
        lines.append("\n**Top SLA stories:**")
        for a in sla_arts[:5]:
            lines.append(f"- [{a.get('title','')}]({a.get('url','')}) — {a.get('source','')} | Score {a.get('score',0)}")

    if personal_arts:
        lines.append("\n**Top personal stories:**")
        for a in personal_arts[:5]:
            lines.append(f"- [{a.get('title','')}]({a.get('url','')}) — {a.get('source','')} | Score {a.get('score',0)}")

    return "\n".join(lines)


# ── Build briefing ────────────────────────────────────────────────────────────

def build_briefing(sla_src, sla_posts, personal_src, personal_posts, today: str):
    sla_post_count      = len(sla_posts.get("posts", []))
    personal_post_count = len(personal_posts.get("posts", []))
    date_d   = _today_display(today)
    day_name = _day_name(today)

    md = f"""\
# DAILY CONTENT BRIEFING
# Settlement Layer Advisory + Kiran Kaur Personal
# {date_d} ({day_name}) | Generated {NOW}

---

{section_eigenstate(sla_src)}

---

{section_wfp()}

---

## SETTLEMENT LAYER ADVISORY PAGE
## {sla_post_count} posts ready

{section_posts(sla_posts, 'sla', today)}

---

## KIRAN KAUR PERSONAL PAGE
## {personal_post_count} posts ready

{section_posts(personal_posts, 'personal', today)}

---

## CONVERSATIONS TO JOIN TODAY

{section_conversations('sla')}

{section_conversations('personal')}

---

## SOURCES SCANNED TODAY

{section_sources_summary(sla_src, personal_src)}

---

## WATCH LIST

{section_watchlist(personal_src)}

---

*Generated by Settlement Layer Advisory content engine*
*Powered by Eigenstate Research | Base mainnet timestamped*
*settlementlayeradvisory.com*
"""
    return md


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    today    = _detect_today()
    date_d   = _today_display(today)
    day_name = _day_name(today)
    briefing_path = os.path.join(BASE, f"MASTER_BRIEFING_{today}.md")

    print("\n" + "="*64)
    print("  SETTLEMENT LAYER ADVISORY + KIRAN KAUR")
    print("  Combined Master Content Briefing")
    print(f"  {date_d} ({day_name})")
    print("="*64)

    # Step 0: Update entity readings from yesterday's scan (before today's scan runs)
    entity_updater = os.path.join(BASE, "entity_readings_updater.py")
    if os.path.exists(entity_updater):
        run("Update entity Phi_S readings", entity_updater)

    # Run SLA pipeline
    print("\n[PIPELINE 1] Settlement Layer Advisory")
    run("Scan SLA sources",    os.path.join(BASE, "scan_sources.py"))
    run("Generate SLA posts",  os.path.join(BASE, "generate_posts.py"))
    run("Generate SLA visuals",os.path.join(BASE, "generate_visuals.py"))

    # Run personal pipeline
    print("\n[PIPELINE 2] Kiran Kaur Personal")
    run("Scan personal sources",    os.path.join(PERSONAL, "scan_personal_sources.py"),    PERSONAL)
    run("Generate personal posts",  os.path.join(PERSONAL, "generate_personal_posts.py"),  PERSONAL)
    run("Generate personal visuals",os.path.join(PERSONAL, "generate_personal_visuals.py"),PERSONAL)

    # Load all outputs — detect actual date from generated files
    def _find_sources(directory: str, prefix: str) -> dict:
        if not os.path.isdir(directory):
            return {}
        candidates = sorted(
            [f for f in os.listdir(directory) if f.startswith(prefix) and f.endswith(".json")],
            reverse=True,
        )
        if candidates:
            p = os.path.join(directory, candidates[0])
            return load_json(p)
        return {}

    sla_src        = _find_sources(os.path.join(BASE, "sources"), "daily_")
    sla_posts_data = _find_sources(os.path.join(BASE, "posts"),   "posts_")
    personal_src   = _find_sources(os.path.join(PERSONAL, "sources"), "personal_")
    personal_posts = _find_sources(os.path.join(PERSONAL, "posts"),   "personal_posts_")

    # Detect actual file date from sources
    src_date = sla_src.get("date", "").replace("-", "") or today

    # Build and write master briefing
    md = build_briefing(sla_src, sla_posts_data, personal_src, personal_posts, src_date)
    with open(briefing_path, "w") as f:
        f.write(md)

    # Summary
    sla_vis_dir = os.path.join(BASE, "visuals")
    p_vis_dir   = os.path.join(PERSONAL, "visuals")
    sla_vis     = len([x for x in os.listdir(sla_vis_dir)  if src_date in x]) if os.path.isdir(sla_vis_dir) else 0
    p_vis       = len([x for x in os.listdir(p_vis_dir)    if src_date in x]) if os.path.isdir(p_vis_dir)   else 0

    sla_arts    = len(sla_src.get("articles", []))
    p_arts      = len(personal_src.get("articles", []))
    sla_posts_n = len(sla_posts_data.get("posts", []))
    p_posts_n   = len(personal_posts.get("posts", []))
    failed      = sla_src.get("failed_feeds", []) + personal_src.get("failed_feeds", [])

    print(f"\n{'='*64}")
    print("  MASTER BRIEFING COMPLETE")
    print(f"{'='*64}")
    print(f"  Articles scanned   : {sla_arts + p_arts} ({sla_arts} SLA + {p_arts} personal)")
    print(f"  Posts generated    : {sla_posts_n + p_posts_n} ({sla_posts_n} SLA + {p_posts_n} personal)")
    print(f"  Visuals created    : {sla_vis + p_vis} ({sla_vis} SLA + {p_vis} personal)")
    print(f"  Failed feeds       : {len(failed)}" + (f" ({', '.join(failed[:3])})" if failed else ""))
    print(f"  Master briefing    : {briefing_path}")
    print(f"{'='*64}\n")


if __name__ == "__main__":
    main()
