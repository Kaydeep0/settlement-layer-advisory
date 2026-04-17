#!/usr/bin/env python3
"""
linkedin_dispatch.py — Settlement Layer Advisory LinkedIn dispatch module.

Posts daily content to both the SLA company page and Kiran's personal
LinkedIn profile. Reads posts from the content_engine output directories
and dispatches according to DISPATCH_MODE.

Usage:
    python3 linkedin_dispatch.py              # preview all 10 posts
    python3 linkedin_dispatch.py --dispatch   # run dispatch loop
"""

import argparse
import datetime
import json
import os
import sys
import time

import requests
import schedule

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE     = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.expanduser("~/SETTLEMENT_LAYER_ADVISORY/.env")

POSTS_DIR    = os.path.join(BASE, "posts")
VISUALS_DIR  = os.path.join(BASE, "visuals")
PERSONAL_DIR = os.path.join(BASE, "personal")

CANCEL_FILE  = os.path.join(BASE, "CANCEL_TODAY")

# ---------------------------------------------------------------------------
# Schedule times
# ---------------------------------------------------------------------------

SLA_TIMES      = ["08:00", "11:00", "13:00", "16:00", "19:00"]
PERSONAL_TIMES = ["08:30", "12:00", "15:00", "18:00", "21:00"]

# ---------------------------------------------------------------------------
# Env loader
# ---------------------------------------------------------------------------

def load_env(path: str) -> dict:
    """Parse a key=value .env file and return a dict. Ignores blank lines
    and lines starting with #. Does not raise on missing file."""
    result = {}
    if not os.path.exists(path):
        return result
    with open(path, "r") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            result[key.strip()] = val.strip()
    return result

# ---------------------------------------------------------------------------
# Cancel mechanism
# ---------------------------------------------------------------------------

def is_cancelled() -> bool:
    return os.path.exists(CANCEL_FILE)

def clear_cancel():
    """Remove cancel file (called at midnight reset)."""
    if os.path.exists(CANCEL_FILE):
        os.remove(CANCEL_FILE)
        print("[INFO] CANCEL_TODAY file removed (midnight reset)")

# ---------------------------------------------------------------------------
# LinkedIn API: image upload
# ---------------------------------------------------------------------------

def upload_image(token: str, author_urn: str, image_path: str) -> str:
    """Upload image to LinkedIn and return asset URN."""
    # Step 1: Register upload
    register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    register_payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": author_urn,
            "serviceRelationships": [{
                "relationshipType": "OWNER",
                "identifier": "urn:li:userGeneratedContent"
            }]
        }
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    r = requests.post(register_url, json=register_payload, headers=headers)
    r.raise_for_status()
    data = r.json()
    upload_url = data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    asset_urn  = data["value"]["asset"]

    # Step 2: Upload binary
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    upload_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "image/png",
    }
    r2 = requests.put(upload_url, data=img_bytes, headers=upload_headers)
    r2.raise_for_status()

    return asset_urn

# ---------------------------------------------------------------------------
# LinkedIn API: create post
# ---------------------------------------------------------------------------

def create_post(token: str, author_urn: str, text: str, asset_urn: str = None) -> dict:
    """Create a LinkedIn UGC post. Returns API response dict."""
    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    if asset_urn:
        media = [{
            "status": "READY",
            "description": {"text": text[:100]},
            "media": asset_urn,
            "title": {"text": text.split("\n")[0][:70]},
        }]
        share_category = "IMAGE"
    else:
        media = []
        share_category = "NONE"

    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": share_category,
                "media": media,
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    r = requests.post(url, json=payload, headers=headers)
    r.raise_for_status()
    return r.json()

# ---------------------------------------------------------------------------
# Dispatch one post
# ---------------------------------------------------------------------------

def dispatch_post(post: dict, author_urn: str, token: str, pipeline: str, today: str):
    """Dispatch one post to LinkedIn. Handles image upload and text post."""
    if is_cancelled():
        print(f"[CANCELLED] Skipping post {post['id']} — CANCEL_TODAY file exists")
        return None

    post_text = post["post_text"]
    hashtags  = " ".join(post.get("hashtags", []))
    full_text = post_text.strip()
    if hashtags and hashtags not in full_text:
        full_text = full_text + "\n\n" + hashtags

    # Resolve visual path
    if pipeline == "sla":
        vis_path = os.path.join(VISUALS_DIR, f"visual_{today}_{post['id']}.png")
    else:
        vis_path = os.path.join(PERSONAL_DIR, "visuals",
                                f"personal_visual_{today}_{post['id']}.png")

    asset_urn = None
    if os.path.exists(vis_path):
        try:
            asset_urn = upload_image(token, author_urn, vis_path)
            print(f"  [UPLOAD] Image uploaded: {asset_urn}")
        except Exception as e:
            print(f"  [WARN] Image upload failed: {e} — posting text only")

    try:
        result = create_post(token, author_urn, full_text, asset_urn)
        post_id = result.get("id", "unknown")
        print(f"  [POSTED] Post {post['id']} → LinkedIn post ID: {post_id}")
        return result
    except Exception as e:
        print(f"  [ERROR] Post {post['id']} failed: {e}")
        return None

# ---------------------------------------------------------------------------
# Post loaders
# ---------------------------------------------------------------------------

def load_posts(today: str) -> list:
    """Load SLA company page posts for today. Returns list or empty list."""
    path = os.path.join(POSTS_DIR, f"posts_{today}.json")
    if not os.path.exists(path):
        print(f"[WARN] SLA posts file not found: {path}")
        return []
    with open(path, "r") as fh:
        data = json.load(fh)
    return data.get("posts", [])

def load_personal_posts(today: str) -> list:
    """Load personal profile posts for today. Returns list or empty list."""
    path = os.path.join(PERSONAL_DIR, "posts", f"personal_posts_{today}.json")
    if not os.path.exists(path):
        print(f"[WARN] Personal posts file not found: {path}")
        return []
    with open(path, "r") as fh:
        data = json.load(fh)
    return data.get("posts", [])

# ---------------------------------------------------------------------------
# Preview helpers
# ---------------------------------------------------------------------------

def _vis_path_for(post: dict, pipeline: str, today: str) -> str:
    if pipeline == "sla":
        return os.path.join(VISUALS_DIR, f"visual_{today}_{post['id']}.png")
    return os.path.join(PERSONAL_DIR, "visuals",
                        f"personal_visual_{today}_{post['id']}.png")

def preview_posts(sla_posts: list, personal_posts: list, today: str):
    """Print a structured preview of all posts without dispatching."""
    display_date = datetime.datetime.strptime(today, "%Y%m%d").strftime("%Y-%m-%d")
    print(f"\n{'='*64}")
    print(f"  SLA Company Page Posts — {display_date}")
    print(f"{'='*64}")
    for post in sla_posts:
        vis = _vis_path_for(post, "sla", today)
        vis_status = "EXISTS" if os.path.exists(vis) else "MISSING"
        print(f"\n  [{post['id']}] {post.get('best_time', '??:??')} "
              f"| {post.get('type', 'unknown')} "
              f"| {post.get('character_count', len(post['post_text']))} chars")
        print(f"  Visual: {vis} [{vis_status}]")
        print(f"  ---")
        # Truncate long posts for readability
        text_preview = post["post_text"][:300].replace("\n", "\n  ")
        if len(post["post_text"]) > 300:
            text_preview += "..."
        print(f"  {text_preview}")

    print(f"\n{'='*64}")
    print(f"  Personal Profile Posts — {display_date}")
    print(f"{'='*64}")
    for post in personal_posts:
        vis = _vis_path_for(post, "personal", today)
        vis_status = "EXISTS" if os.path.exists(vis) else "MISSING"
        print(f"\n  [{post['id']}] {post.get('best_time', '??:??')} "
              f"| {post.get('type', 'unknown')} "
              f"| {post.get('character_count', len(post['post_text']))} chars")
        print(f"  Visual: {vis} [{vis_status}]")
        print(f"  ---")
        text_preview = post["post_text"][:300].replace("\n", "\n  ")
        if len(post["post_text"]) > 300:
            text_preview += "..."
        print(f"  {text_preview}")

# ---------------------------------------------------------------------------
# Review-mode helpers
# ---------------------------------------------------------------------------

REVIEW_DELAY_SECONDS = 30 * 60  # 30 minutes

def _review_countdown(post_label: str, delay: int):
    """Block for `delay` seconds, printing a simple countdown."""
    print(f"\n[REVIEW] {post_label} — dispatching in {delay // 60} minutes.")
    print(f"         To cancel ALL posts today: touch {CANCEL_FILE}")
    print(f"         To cancel this post only:  Ctrl+C within the next "
          f"{delay // 60} minutes.")
    interval = 60  # tick every 60 seconds
    elapsed  = 0
    while elapsed < delay:
        if is_cancelled():
            print(f"\n[CANCELLED] Cancel file detected — skipping {post_label}")
            return False
        remaining = delay - elapsed
        mins = remaining // 60
        print(f"  ... {mins} min remaining", flush=True)
        sleep_for = min(interval, remaining)
        time.sleep(sleep_for)
        elapsed += sleep_for
    return True

# ---------------------------------------------------------------------------
# Schedule runner
# ---------------------------------------------------------------------------

def schedule_runner():
    """Run the schedule loop until midnight, then clear the cancel file."""
    print("[SCHEDULER] Running. Press Ctrl+C to stop.")
    midnight = datetime.datetime.combine(
        datetime.date.today() + datetime.timedelta(days=1),
        datetime.time.min
    )
    try:
        while datetime.datetime.now() < midnight:
            schedule.run_pending()
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n[SCHEDULER] Interrupted by user.")
    finally:
        clear_cancel()

# ---------------------------------------------------------------------------
# Main dispatch runner
# ---------------------------------------------------------------------------

def run_dispatch(today: str = None):
    """Main entry: load posts, check mode, dispatch or schedule."""

    # 1. Load env
    env = load_env(ENV_PATH)

    # 2. Check credentials
    token    = env.get("LINKEDIN_ACCESS_TOKEN", "").strip()
    org_urn  = env.get("LINKEDIN_ORG_ID", "").strip()
    person_urn = env.get("LINKEDIN_PERSON_ID", "").strip()
    mode     = env.get("DISPATCH_MODE", "review").strip().lower()

    credentials_present = all([token, org_urn, person_urn])
    if not credentials_present:
        print("LinkedIn credentials not configured. Running in briefing-only mode.")
        return

    # 3. Detect today
    if today is None:
        today = datetime.datetime.utcnow().strftime("%Y%m%d")

    # 4. Load posts
    sla_posts      = load_posts(today)
    personal_posts = load_personal_posts(today)

    if not sla_posts and not personal_posts:
        print(f"[WARN] No posts found for {today}. Exiting.")
        return

    # 5. Route by mode
    if mode == "manual":
        print(f"\n[MANUAL MODE] Displaying posts for {today}. No dispatch will occur.\n")
        display_date = datetime.datetime.strptime(today, "%Y%m%d").strftime("%Y-%m-%d")
        print(f"--- SLA Posts ({display_date}) ---")
        for post in sla_posts:
            vis = _vis_path_for(post, "sla", today)
            print(f"\n[{post['id']}] {post.get('best_time', '??:??')} | "
                  f"{post.get('character_count', len(post['post_text']))} chars")
            print(f"Visual: {vis}")
            print(post["post_text"])
        print(f"\n--- Personal Posts ({display_date}) ---")
        for post in personal_posts:
            vis = _vis_path_for(post, "personal", today)
            print(f"\n[{post['id']}] {post.get('best_time', '??:??')} | "
                  f"{post.get('character_count', len(post['post_text']))} chars")
            print(f"Visual: {vis}")
            print(post["post_text"])
        return

    if mode == "review":
        _run_review_mode(sla_posts, personal_posts, org_urn, person_urn, token, today)

    elif mode == "auto":
        _run_auto_mode(sla_posts, personal_posts, org_urn, person_urn, token, today)

    else:
        print(f"[WARN] Unknown DISPATCH_MODE '{mode}'. Defaulting to review mode.")
        _run_review_mode(sla_posts, personal_posts, org_urn, person_urn, token, today)


def _run_review_mode(sla_posts, personal_posts, org_urn, person_urn, token, today):
    """Review mode: print 30-min notice per post then dispatch sequentially."""
    display_date = datetime.datetime.strptime(today, "%Y%m%d").strftime("%Y-%m-%d")
    print(f"\n[REVIEW MODE] Date: {display_date}")
    print(f"Each post will wait 30 minutes before dispatch.\n")

    # Pair posts with their target URN and pipeline label
    all_posts = (
        [(p, org_urn,    "sla",      SLA_TIMES[i])      for i, p in enumerate(sla_posts)]      +
        [(p, person_urn, "personal", PERSONAL_TIMES[i]) for i, p in enumerate(personal_posts)]
    )
    # Sort by scheduled time so interleaved SLA + personal posts fire in order
    all_posts.sort(key=lambda x: x[3])

    for post, author_urn, pipeline, sched_time in all_posts:
        label = f"Post {post['id']} ({pipeline}) scheduled for {sched_time}"
        print(f"\n[REVIEW] {label}. Will dispatch at +30 min.")
        print(f"         To cancel ALL posts today: touch {CANCEL_FILE}")
        print(f"         To cancel this post only:  Ctrl+C within the next 30 minutes.")
        ok = _review_countdown(label, REVIEW_DELAY_SECONDS)
        if ok:
            dispatch_post(post, author_urn, token, pipeline, today)
        else:
            # Cancelled just for this post (cancel file not set); continue loop
            pass


def _run_auto_mode(sla_posts, personal_posts, org_urn, person_urn, token, today):
    """Auto mode: schedule posts at their best_time fields and run loop."""
    display_date = datetime.datetime.strptime(today, "%Y%m%d").strftime("%Y-%m-%d")
    print(f"\n[AUTO MODE] Date: {display_date}")
    print(f"Scheduling {len(sla_posts)} SLA posts and {len(personal_posts)} personal posts.\n")

    def _make_job(post, author_urn, pipeline):
        def job():
            print(f"\n[AUTO] Firing post {post['id']} ({pipeline})")
            dispatch_post(post, author_urn, token, pipeline, today)
        return job

    for post in sla_posts:
        t = post.get("best_time", "08:00")
        schedule.every().day.at(t).do(_make_job(post, org_urn, "sla"))
        print(f"  Scheduled SLA post {post['id']} at {t}")

    for post in personal_posts:
        t = post.get("best_time", "08:30")
        schedule.every().day.at(t).do(_make_job(post, person_urn, "personal"))
        print(f"  Scheduled personal post {post['id']} at {t}")

    schedule_runner()

# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="LinkedIn dispatch for Settlement Layer Advisory"
    )
    parser.add_argument(
        "--dispatch",
        action="store_true",
        help="Run the dispatch loop (schedule or immediate depending on DISPATCH_MODE)"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Override date in YYYYMMDD format (default: today UTC)"
    )
    args = parser.parse_args()

    # Resolve date
    today = args.date or datetime.datetime.utcnow().strftime("%Y%m%d")

    # Load env for preview header
    env = load_env(ENV_PATH)
    token      = env.get("LINKEDIN_ACCESS_TOKEN", "").strip()
    org_urn    = env.get("LINKEDIN_ORG_ID", "").strip()
    person_urn = env.get("LINKEDIN_PERSON_ID", "").strip()
    mode       = env.get("DISPATCH_MODE", "review").strip().lower() or "review"

    credentials_present = all([token, org_urn, person_urn])

    display_date = datetime.datetime.strptime(today, "%Y%m%d").strftime("%Y-%m-%d")
    print(f"\nSettlement Layer Advisory — LinkedIn Dispatch")
    print(f"Date:          {display_date}")
    print(f"Mode:          {mode.upper()}")
    print(f"Credentials:   {'CONFIGURED' if credentials_present else 'NOT CONFIGURED'}")
    print(f"Cancel file:   {CANCEL_FILE}")

    if not credentials_present:
        print("\nLinkedIn credentials not configured. Running in briefing-only mode.")

    # Load posts regardless (for preview)
    sla_posts      = load_posts(today)
    personal_posts = load_personal_posts(today)

    total = len(sla_posts) + len(personal_posts)
    print(f"Posts loaded:  {len(sla_posts)} SLA + {len(personal_posts)} personal = {total} total\n")

    # Always preview
    if sla_posts or personal_posts:
        preview_posts(sla_posts, personal_posts, today)

    if not args.dispatch:
        print("\n[INFO] Preview complete. Pass --dispatch to run the dispatch loop.")
        return

    if not credentials_present:
        print("\n[INFO] Cannot dispatch — LinkedIn credentials not configured.")
        return

    # Run dispatch
    run_dispatch(today)


if __name__ == "__main__":
    main()
