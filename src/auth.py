"""
Google OAuth login for actions on YOUR OWN channel.

Reading public stats only needs an API key (see youtube_client.py). But to
UPLOAD videos, change their status, or read your PRIVATE analytics, Google
requires you to log in and grant permission. That login is OAuth.

How it works for you:
1. You download a "client_secret.json" file from Google Cloud (one time).
2. You run `python authorize.py` once — a browser opens, you click "Allow".
3. A "token.json" file is saved. After that, everything just works.

token.json and client_secret.json are secrets — .gitignore already blocks them.
"""
import os

# The exact permissions we ask Google for. Nothing more than needed.
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",      # upload videos
    "https://www.googleapis.com/auth/youtube",             # update/publish videos
    "https://www.googleapis.com/auth/youtube.readonly",    # list your videos
    "https://www.googleapis.com/auth/yt-analytics.readonly",  # private analytics
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_SECRET_FILE = os.path.join(ROOT, "client_secret.json")
TOKEN_FILE = os.path.join(ROOT, "token.json")


def is_authorized():
    """True if you've already logged in (token.json exists)."""
    return os.path.exists(TOKEN_FILE)


def get_credentials():
    """
    Returns valid Google credentials, refreshing or prompting login as needed.
    The first call (no token yet) opens a browser for you to approve access.
    """
    # Imported here so the app can start even before these libs are installed.
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET_FILE):
                raise FileNotFoundError(
                    "client_secret.json not found. Download it from Google Cloud "
                    "Console (see docs/OAUTH-SETUP.md) and put it in the project folder."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            # Opens your browser, you approve, and it captures the result locally.
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return creds


def youtube_service():
    """An authenticated YouTube Data API client (for uploads, publishing)."""
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=get_credentials())


def analytics_service():
    """An authenticated YouTube Analytics API client (for private stats)."""
    from googleapiclient.discovery import build
    return build("youtubeAnalytics", "v2", credentials=get_credentials())
