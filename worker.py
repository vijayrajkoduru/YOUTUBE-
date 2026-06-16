"""Background publishing worker.

Polls the DB for approved assets and publishes them:
  - video -> social.post_video to its target networks
  - blog  -> blogpub.publish_blog to its targets

On success: status -> 'posted' and the result urls are stored in detail.
On error:   status -> 'failed' with the error message.

The loop is idempotent: it only ever picks up assets still in 'approved'
status, flips them out of it before/while working, and sleeps ~3s between
passes. Safe to run as a daemon thread.
"""
import threading
import time

import db
from providers import blogpub, social

POLL_SECONDS = 3
_thread = None
_started = False

# Default publishing targets when an asset did not specify its own.
DEFAULT_VIDEO_NETWORKS = ["instagram", "facebook", "x", "linkedin"]
DEFAULT_BLOG_TARGETS = ["wordpress", "devto", "hashnode"]


def _process_asset(asset):
    asset_id = asset["id"]
    kind = asset["kind"]
    detail = asset.get("detail")
    if not isinstance(detail, dict):
        detail = {}

    try:
        if kind == "video":
            networks = asset.get("targets") or DEFAULT_VIDEO_NETWORKS
            caption = asset.get("title") or asset.get("topic") or ""
            result = social.post_video(asset.get("video_path"), caption, networks)
            detail["publish_result"] = result.get("results", {})
            db.update_detail(asset_id, detail)
            db.set_status(asset_id, "posted")
            print(f"[worker] video asset {asset_id} posted: {result.get('results')}")

        elif kind == "blog":
            targets = asset.get("targets") or DEFAULT_BLOG_TARGETS
            title = asset.get("title") or ""
            html = asset.get("blog_html") or ""
            tags = detail.get("tags") or []
            result = blogpub.publish_blog(title, html, tags, targets)
            detail["publish_result"] = result.get("results", {})
            db.update_detail(asset_id, detail)
            db.set_status(asset_id, "posted")
            print(f"[worker] blog asset {asset_id} posted: {result.get('results')}")

        else:
            db.set_status(asset_id, "failed", error=f"unknown kind: {kind}")

    except Exception as exc:  # noqa: BLE001
        db.set_status(asset_id, "failed", error=str(exc))
        print(f"[worker] asset {asset_id} FAILED: {exc}")


def _loop():
    print("[worker] started; polling for approved assets every "
          f"{POLL_SECONDS}s")
    while True:
        try:
            approved = db.list_assets(status="approved")
            for asset in approved:
                _process_asset(asset)
        except Exception as exc:  # noqa: BLE001  (keep the loop alive)
            print(f"[worker] loop error: {exc}")
        time.sleep(POLL_SECONDS)


def start_worker():
    """Start the worker thread exactly once."""
    global _thread, _started
    if _started:
        return
    _started = True
    _thread = threading.Thread(target=_loop, name="publish-worker", daemon=True)
    _thread.start()
