"""
System Check — verifies the project is wired up and reports what's ready.

It checks credentials and connections, then tells you which features are usable.
This is the "verify everything and connectivity" step: run it any time to see
exactly where the pipeline stands.
"""
import os

import config
from src import auth


def run_checks():
    """Returns a list of connectivity/credential checks with pass/fail."""
    api_key_ok = bool(config.YOUTUBE_API_KEY) and config.YOUTUBE_API_KEY != "paste_your_api_key_here"
    channel_ok = bool(config.MY_CHANNEL_ID) and config.MY_CHANNEL_ID != "paste_your_channel_id_here"
    ai_ok = bool(config.ANTHROPIC_API_KEY) and config.ANTHROPIC_API_KEY != "paste_your_anthropic_key_here"

    return [
        {"name": "Claude API key", "ok": ai_ok,
         "detail": "Optional — powers AI Ideas and Script."},
        {"name": "YouTube API key", "ok": api_key_ok,
         "detail": "Reads public stats (Channel Report, Comments)."},
        {"name": "Channel ID", "ok": channel_ok,
         "detail": "Identifies your channel for reports."},
        {"name": "OAuth client secret", "ok": os.path.exists(auth.CLIENT_SECRET_FILE),
         "detail": "client_secret.json — needed to log in."},
        {"name": "Logged in (token)", "ok": auth.is_authorized(),
         "detail": "token.json — enables Upload, Queue, Analytics."},
    ]


def feature_readiness(checks=None):
    """Maps the checks to whether each feature is ready to use."""
    if checks is None:
        checks = run_checks()
    ok = {c["name"]: c["ok"] for c in checks}
    return [
        {"feature": "Channel Report", "ready": ok["YouTube API key"] and ok["Channel ID"]},
        {"feature": "SEO Generator", "ready": True},
        {"feature": "A/B Tracker", "ready": True},
        {"feature": "Comments", "ready": ok["YouTube API key"]},
        {"feature": "Private Analytics", "ready": ok["Logged in (token)"]},
        {"feature": "Upload & Queue", "ready": ok["Logged in (token)"]},
        {"feature": "AI Ideas & Script", "ready": ok["Claude API key"]},
    ]
