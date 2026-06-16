"""Background publishing worker.

Polls the DB for approved assets and publishes them:
  - video -> social.post_video(video_path, caption, networks)
  - blog  -> blogpub.publish_blog(title, html, tags, targets)

On success: status -> 'posted' and the per-target results are stored in the
            post_result JSON column.
On error:   status -> 'failed' with the error message (one retry first).

Scheduling: if an asset has scheduled_at set and it is still in the future, the
worker skips it until due.

The loop is idempotent: it only ever picks up assets still in 'approved' status,
flips them out of it while working, and sleeps ~3s between passes. Safe to run
as a daemon thread.
"""
import threading
import time
from datetime import datetime, timezone

import db
from providers import blogpub, social

POLL_SECONDS = 3
_thread = None
_started = False

# Default publishing targets when an asset did not specify its own.
DEFAULT_VIDEO_NETWORKS = ["instagram", "facebook", "x", "linkedin"]
DEFAULT_BLOG_TARGETS = ["wordpress", "devto", "hashnode"]


def _is_due(asset):
    """True if the asset is ready to publish now.

    Assets with no scheduled_at are always due. Assets with a scheduled_at in the
    future are skipped until that time arrives. A malformed timestamp is treated
    as due (fail-open: better to publish an approved asset than strand it).
    """
    raw = asset.get("scheduled_at")
    if not raw:
        return True
    try:
        when = datetime.fromisoformat(str(raw))
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= when
    except (ValueError, TypeError):
        return True


def _publish(asset):
    """Run the actual publish for one asset. Returns the per-target results dict.

    Raises on provider transport errors so the caller can retry once. Provider
    functions themselves capture per-target failures, so this mostly surfaces
    truly unexpected errors.
    """
    kind = asset["kind"]
    if kind == "video":
        networks = asset.get("networks") or asset.get("targets") or DEFAULT_VIDEO_NETWORKS
        caption = (
            asset.get("caption")
            or asset.get("title")
            or asset.get("topic")
            or ""
        )
        result = social.post_video(asset.get("video_path"), caption, networks)
        return result.get("results", {})

    if kind == "blog":
        targets = asset.get("targets") or DEFAULT_BLOG_TARGETS
        title = asset.get("title") or ""
        html = asset.get("blog_html") or ""
        detail = asset.get("detail")
        tags = detail.get("tags") if isinstance(detail, dict) else None
        result = blogpub.publish_blog(title, html, tags or [], targets)
        return result.get("results", {})

    raise ValueError(f"unknown kind: {kind}")


def _process_asset(asset):
    asset_id = asset["id"]
    kind = asset["kind"]

    if not _is_due(asset):
        # Scheduled for later -> leave it approved and revisit next pass.
        return

    # One automatic retry on an unexpected exception before giving up.
    last_exc = None
    for attempt in range(2):
        try:
            results = _publish(asset)
            db.update_asset(asset_id, post_result=results)
            db.set_status(asset_id, "posted")
            print(f"[worker] {kind} asset {asset_id} posted: {results}")
            return
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            print(f"[worker] asset {asset_id} attempt {attempt + 1} failed: {exc}")
            if attempt == 0:
                time.sleep(1)  # brief backoff before the single retry

    db.set_status(asset_id, "failed", error=str(last_exc))
    print(f"[worker] asset {asset_id} FAILED after retry: {last_exc}")


def _loop():
    print(
        "[worker] started; polling for approved assets every "
        f"{POLL_SECONDS}s"
    )
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
