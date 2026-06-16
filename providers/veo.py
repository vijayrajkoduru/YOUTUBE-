"""Veo video provider with a HARD cost guard.

generate_video() ALWAYS checks the cost guard before spending. In DRY_RUN it
writes a tiny placeholder mp4 and reports cost 0. With real keys + DRY_RUN=false
it calls Veo via google-genai, polls the long-running op, downloads the mp4 and
charges seconds * rate -- but only after the monthly USD cap and daily clip cap
are confirmed not exceeded.
"""
import os
import time

import config
import db


# Minimal valid MP4 (ftyp + empty moov) so a browser <video> element can load
# the placeholder without erroring. Not a real playable clip -- it is a marker.
_PLACEHOLDER_MP4 = bytes.fromhex(
    "0000001c66747970"  # box size 28, 'ftyp'
    "69736f6d0000020069736f6d69736f32"  # major 'isom', minor, compat brands
    "0000000c6d6f6f76"  # box size 12, 'moov' (empty)
    "00000000"
)


# Per-second USD rate lookup by model. veo-3.1-fast at 720p is the default
# pipeline model and bills ~0.10/sec. Unknown models fall back to the configured
# config.VEO_USD_PER_SECOND so accounting never silently drops to zero.
_VEO_RATE_BY_MODEL = {
    "veo-3.1-fast-generate-preview": 0.10,
    "veo-3.1-generate-preview": 0.40,
    "veo-3.0-fast-generate-preview": 0.10,
    "veo-3.0-generate-preview": 0.40,
}


def _rate_for_model(model):
    """USD per generated second for the given Veo model.

    Defaults to 0.10/sec (veo-3.1-fast 720p). Unknown models fall back to the
    configured per-second rate so cost is never undercounted.
    """
    if model in _VEO_RATE_BY_MODEL:
        return _VEO_RATE_BY_MODEL[model]
    return config.VEO_USD_PER_SECOND


def _check_cost_guard(seconds):
    """Raise RuntimeError if generating this clip would breach a cap.

    Only enforced for real (non-DRY_RUN) generation. DRY_RUN never spends.
    """
    month_cost = db.month_cost_usd()
    day_clips = db.day_clip_count()
    projected = seconds * config.VEO_USD_PER_SECOND

    if day_clips >= config.VEO_DAILY_CLIP_CAP:
        raise RuntimeError(
            f"Veo daily clip cap reached: {day_clips}/{config.VEO_DAILY_CLIP_CAP} "
            f"clips already generated today. Generation blocked."
        )
    if month_cost + projected > config.VEO_MONTHLY_USD_CAP:
        raise RuntimeError(
            f"Veo monthly cost cap would be exceeded: "
            f"${month_cost:.2f} spent + ${projected:.2f} this clip "
            f"> ${config.VEO_MONTHLY_USD_CAP:.2f} cap. Generation blocked."
        )


def generate_video(prompt, seconds=8, out_dir=None):
    """Generate a video. Returns {"path": <abs mp4 path>, "cost": <usd float>}.

    The cost guard runs FIRST for real generation. DRY_RUN skips spend and
    writes a placeholder file.
    """
    if out_dir is None:
        out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "videos")
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    ts = int(time.time() * 1000)
    out_path = os.path.join(out_dir, f"clip_{ts}.mp4")

    # --- DRY_RUN or no key: placeholder, zero spend ------------------------
    if config.DRY_RUN or not config.GOOGLE_API_KEY:
        with open(out_path, "wb") as fh:
            fh.write(_PLACEHOLDER_MP4)
        return {"path": out_path, "cost": 0.0}

    # --- Real generation: enforce the cost guard BEFORE anything else ------
    _check_cost_guard(seconds)

    # --- Real Veo generation via google-genai ------------------------------
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=config.GOOGLE_API_KEY)

        # Submit the generation request. Duration is requested in seconds;
        # 720p / 16:9 keeps us on the default veo-3.1-fast pricing tier.
        operation = client.models.generate_videos(
            model=config.VEO_MODEL,
            prompt=prompt,
            config=types.GenerateVideosConfig(
                number_of_videos=1,
                duration_seconds=seconds,
                aspect_ratio="16:9",
                resolution="720p",
            ),
        )

        # Poll the long-running operation until it completes. Cap the total
        # wait so a stuck op cannot block the worker indefinitely.
        deadline = time.time() + 600  # 10 minutes
        while not operation.done:
            if time.time() > deadline:
                raise RuntimeError("Veo operation timed out before completion.")
            time.sleep(10)
            operation = client.operations.get(operation)

        if getattr(operation, "error", None):
            raise RuntimeError(f"Veo operation returned an error: {operation.error}")

        response = operation.response
        generated = getattr(response, "generated_videos", None)
        if not generated:
            raise RuntimeError("Veo operation completed but returned no videos.")

        video = generated[0]
        # Pull the bytes down from the Files API, then persist to out_path.
        client.files.download(file=video.video)
        video.video.save(out_path)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Veo generation failed: {exc}") from exc

    # Charge by the per-model per-second rate (default 0.10/sec for veo-3.1-fast).
    cost = seconds * _rate_for_model(config.VEO_MODEL)
    return {"path": out_path, "cost": cost}
