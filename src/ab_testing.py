"""
A simple tracker for thumbnail/title experiments.

Click-through rate (CTR) — the % of people who click after seeing your
thumbnail — is one of the biggest growth levers. The honest way to improve
it is to test different thumbnails/titles and keep what wins. This tool
just records your experiments so you can compare them over time.

Data is saved to data/experiments.json on your own computer.
"""
import json
import os
from datetime import date

import config

_FILE = os.path.join(config.DATA_DIR, "experiments.json")


def _load():
    if not os.path.exists(_FILE):
        return []
    with open(_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(experiments):
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(_FILE, "w", encoding="utf-8") as f:
        json.dump(experiments, f, indent=2, ensure_ascii=False)


def add_variant(video_title, variant_label, thumbnail_idea, hook_title):
    """Records one thumbnail/title idea you want to try."""
    experiments = _load()
    experiments.append({
        "date": date.today().isoformat(),
        "video": video_title,
        "variant": variant_label,
        "thumbnail_idea": thumbnail_idea,
        "hook_title": hook_title,
        "impressions": None,
        "clicks": None,
        "ctr_percent": None,
    })
    _save(experiments)


def record_result(video_title, variant_label, impressions, clicks):
    """
    Fill in the real numbers after a few days.
    Get impressions/clicks from YouTube Studio > Analytics > Reach.
    """
    experiments = _load()
    for exp in experiments:
        if exp["video"] == video_title and exp["variant"] == variant_label:
            exp["impressions"] = impressions
            exp["clicks"] = clicks
            exp["ctr_percent"] = round(clicks / impressions * 100, 2) if impressions else None
    _save(experiments)


def list_experiments():
    """Returns all recorded experiments."""
    return _load()
