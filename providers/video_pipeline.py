"""Multi-scene video pipeline: generate per-scene Veo clips, then stitch.

A "real" video here is several Veo clips concatenated into one mp4. This module
owns the orchestration:

  1. For every scene it calls providers.veo.generate_video(prompt, seconds,
     out_dir). veo.py already enforces the HARD cost guard + writes the
     DRY_RUN placeholder, so we never touch spend logic here.
  2. It loads each returned clip with moviepy and concatenates them into a
     single mp4 written to out_dir.

Cost is the sum of per-clip costs (0.0 in DRY_RUN). "clips" is the number of
clips that were stitched. In DRY_RUN this MUST never raise -- placeholders are
real tiny clips, and if any clip is somehow unreadable / 0-byte we substitute a
generated 1s color clip so the concatenation always succeeds.

moviepy 2.x API only:
    from moviepy import VideoFileClip, concatenate_videoclips, ImageClip
    clip.with_duration(...) / clip.with_fps(...)
"""
import os
import time

import config
from providers import veo


def _is_dry_run():
    """True when no real spend is allowed (DRY_RUN or no Google key)."""
    return bool(config.DRY_RUN or not config.GOOGLE_API_KEY)


def _fallback_clip(seconds=1):
    """A valid in-memory 1s color clip used when a real clip cannot be read.

    Built from a tiny numpy frame via ImageClip so the stitch never breaks on a
    placeholder that ended up empty / corrupt. Returns None only if moviepy or
    numpy is unavailable (extremely unlikely; handled by the caller).
    """
    try:
        import numpy as np
        from moviepy import ImageClip

        # 320x180 dark slate frame (HxWx3 uint8) -> a real 1s, 8fps clip.
        frame = np.zeros((180, 320, 3), dtype="uint8")
        frame[:, :] = (20, 24, 28)
        return ImageClip(frame).with_duration(max(1, int(seconds))).with_fps(8)
    except Exception:  # noqa: BLE001
        return None


def _load_clip(path, seconds):
    """Load one scene clip for stitching, or a fallback if it is unusable.

    Tries VideoFileClip first. If the file is missing / 0-byte / unreadable
    (e.g. a degraded placeholder), falls back to a generated color clip so the
    concatenation still works. Returns a moviepy clip or None.
    """
    try:
        if path and os.path.exists(path) and os.path.getsize(path) > 0:
            from moviepy import VideoFileClip

            clip = VideoFileClip(path)
            # A readable clip with a real duration is good to stitch.
            if clip.duration and clip.duration > 0:
                return clip
            clip.close()
    except Exception:  # noqa: BLE001
        # Unreadable file (bad placeholder, corrupt download, etc.) -> fallback.
        pass
    return _fallback_clip(seconds=1)


def build_video(scenes, out_dir, seconds=8):
    """Generate a clip per scene then stitch them into one mp4.

    Args:
        scenes:  list of dicts, each with a "prompt" key (the scene prompt).
        out_dir: directory to write the per-clip mp4s and the final stitched
                 mp4 into. Created if missing.
        seconds: per-clip duration passed straight to veo.generate_video.

    Returns:
        {"path": <final stitched mp4 path or None>,
         "cost": <float, sum of per-clip costs>,
         "clips": <int, number of clips stitched>}

    In DRY_RUN this never raises: placeholders are real tiny clips and any
    unreadable clip is replaced by a generated color clip before stitching.
    """
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    scenes = scenes or []
    total_cost = 0.0
    clip_paths = []

    # --- 1. Generate one clip per scene (veo handles cost guard + DRY_RUN) ---
    for scene in scenes:
        if isinstance(scene, dict):
            prompt = scene.get("prompt", "")
        else:
            prompt = str(scene)
        try:
            result = veo.generate_video(prompt, seconds, out_dir)
            total_cost += float(result.get("cost", 0.0) or 0.0)
            path = result.get("path")
            if path:
                clip_paths.append(path)
        except Exception as exc:  # noqa: BLE001
            # In DRY_RUN veo never raises; if real generation raised (e.g. the
            # cost guard tripped) we must not swallow that outside DRY_RUN.
            if not _is_dry_run():
                raise
            print(f"[video_pipeline] scene skipped in DRY_RUN: {exc}")

    if not clip_paths:
        return {"path": None, "cost": total_cost, "clips": 0}

    # --- 2. Stitch all clips into one mp4 -----------------------------------
    loaded = []
    final_path = None
    try:
        from moviepy import concatenate_videoclips

        for path in clip_paths:
            clip = _load_clip(path, seconds)
            if clip is not None:
                loaded.append(clip)

        if not loaded:
            return {"path": None, "cost": total_cost, "clips": 0}

        ts = int(time.time() * 1000)
        final_path = os.path.join(out_dir, f"video_{ts}.mp4")

        final = concatenate_videoclips(loaded, method="compose")
        try:
            final.write_videofile(
                final_path,
                codec="libx264",
                audio=False,
                logger=None,
            )
        finally:
            final.close()

        return {"path": final_path, "cost": total_cost, "clips": len(loaded)}

    except Exception as exc:  # noqa: BLE001
        # Stitch failure must never break DRY_RUN. Degrade gracefully to the
        # first generated clip so the pipeline still yields a playable asset.
        if not _is_dry_run():
            raise
        print(f"[video_pipeline] stitch failed in DRY_RUN, using first clip: {exc}")
        fallback = clip_paths[0] if clip_paths else None
        return {"path": fallback, "cost": total_cost, "clips": len(clip_paths)}

    finally:
        for clip in loaded:
            try:
                clip.close()
            except Exception:  # noqa: BLE001
                pass
