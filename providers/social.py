"""Social video publishing via the Upload-Post aggregator.

post_video() posts a single video to multiple networks at once. In DRY_RUN or
when UPLOAD_POST_API_KEY is missing it returns "DRY_RUN (not sent)" per network
and posts NOTHING. Never raises -- failures are captured per network.
"""
import os

import requests

import config

# --- Upload-Post API contract (upload-post.com) ----------------------------
# Confirmed against https://docs.upload-post.com/api/upload-video/ .
# If any of these need correcting, change them HERE only.
#   * One multipart POST uploads the video AND fans it out to every platform.
#   * Auth header is literally "Apikey <key>" (note the single word "Apikey").
#   * Fields: video (file), title (text), user (REQUIRED text), platform[] (array).
#   * Response: {"success": bool, "results": {network: {"success": bool,
#                 "url"/"post_id"/"video_id": ..., "error": ...}}, ...}
UPLOAD_POST_ENDPOINT = "https://api.upload-post.com/api/upload"
# Upload-Post ties uploads to a "user"/profile created in their dashboard. It is
# a required form field. Override via env if your profile name differs.
UPLOAD_POST_USER = os.getenv("UPLOAD_POST_USER", "").strip() or "default"
# Per-network keys Upload-Post may use to carry the published post link.
_URL_KEYS = ("url", "post_url", "permalink", "link")


def post_video(video_path, caption, networks):
    """Post a video to the given networks.

    Returns {"results": {network: status_string}}.
    """
    networks = networks or []

    # --- DRY_RUN or no key: log-only, post nothing -------------------------
    if config.DRY_RUN or not config.UPLOAD_POST_API_KEY:
        return {"results": {n: "DRY_RUN (not sent)" for n in networks}}

    # --- Real publishing via Upload-Post -----------------------------------
    results = {}

    if not video_path or not os.path.exists(video_path):
        return {"results": {n: "FAILED (video file missing)" for n in networks}}

    # Single upload + fan-out request. The whole HTTP call is wrapped so a
    # transport/parse error degrades every network gracefully instead of
    # raising out of the provider. Per-network outcomes are read back from the
    # Upload-Post "results" object below.
    try:
        headers = {"Authorization": f"Apikey {config.UPLOAD_POST_API_KEY}"}
        with open(video_path, "rb") as fh:
            files = {"video": (os.path.basename(video_path), fh, "video/mp4")}
            # `platform[]` repeats once per network; requests serializes a list
            # value under a single key as repeated form fields, which matches
            # Upload-Post's `-F 'platform[]=instagram' -F 'platform[]=x'` shape.
            data = {
                "title": caption or "",
                "user": UPLOAD_POST_USER,  # required by Upload-Post
                "platform[]": networks,
            }
            resp = requests.post(
                UPLOAD_POST_ENDPOINT,
                headers=headers,
                data=data,
                files=files,
                timeout=180,
            )

        # Try to parse the JSON body; fall back to raw status if it is not JSON.
        try:
            body = resp.json()
        except ValueError:
            body = None

        if not isinstance(body, dict):
            status = "posted" if resp.status_code < 400 else (
                f"FAILED (HTTP {resp.status_code})"
            )
            for n in networks:
                results[n] = status
            return {"results": results}

        # Top-level failure (e.g. bad key, missing user) -> mark all networks.
        if resp.status_code >= 400 or body.get("success") is False and not body.get("results"):
            msg = body.get("message") or body.get("error") or f"HTTP {resp.status_code}"
            for n in networks:
                results[n] = f"FAILED ({msg})"
            return {"results": results}

        # Per-network results. Each entry is handled in its own try/except so a
        # malformed per-network payload can never abort the others.
        net_results = body.get("results") or {}
        for n in networks:
            try:
                info = net_results.get(n)
                if info is None:
                    results[n] = "posted" if body.get("success") else "FAILED (no result returned)"
                    continue
                if info.get("success"):
                    url = next((info[k] for k in _URL_KEYS if info.get(k)), None)
                    results[n] = url if url else "posted"
                else:
                    err = info.get("error") or info.get("message") or "unknown error"
                    results[n] = f"FAILED ({err})"
            except Exception as exc:  # noqa: BLE001  (per-network isolation)
                results[n] = f"FAILED ({exc})"
    except Exception as exc:  # noqa: BLE001  (must never raise out of provider)
        for n in networks:
            results.setdefault(n, f"FAILED ({exc})")

    return {"results": results}
