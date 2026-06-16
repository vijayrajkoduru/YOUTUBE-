"""
Upload, schedule, review, and publish videos on YOUR OWN channel.

Safety by design — the REVIEW GATE:
Every upload goes up as PRIVATE first. Nothing becomes public automatically.
You review it in the queue and explicitly publish (now) or schedule (later).
This keeps you in control and avoids YouTube's spam/inauthentic-content flags.
"""
from datetime import datetime, timezone

from src.auth import youtube_service

# Common YouTube category IDs. 22 = People & Blogs (a safe default).
DEFAULT_CATEGORY = "22"


def upload_video(file_path, title, description, tags=None,
                 category_id=DEFAULT_CATEGORY, made_with_ai=False, publish_at=None):
    """
    Uploads a video file as PRIVATE (the review gate).

    - made_with_ai: if True, adds an AI-content note to the description. You must
      ALSO toggle "Altered or synthetic content" in YouTube Studio — YouTube
      requires disclosing realistic AI-generated video.
    - publish_at: optional RFC3339 UTC time (e.g. "2026-06-20T15:00:00Z"). If set,
      YouTube auto-publishes then; until then it stays private.

    Returns the new video's id.
    """
    from googleapiclient.http import MediaFileUpload

    youtube = youtube_service()

    if made_with_ai:
        description = (description or "") + "\n\nThis video contains AI-generated content."

    body = {
        "snippet": {
            "title": title,
            "description": description or "",
            "tags": tags or [],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": "private",          # always private on upload
            "selfDeclaredMadeForKids": False,
        },
    }
    if publish_at:
        # Scheduled: stays private until publish_at, then goes public.
        body["status"]["publishAt"] = publish_at

    media = MediaFileUpload(file_path, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        _, response = request.next_chunk()
    return response["id"]


def list_my_videos(max_results=25):
    """
    Lists your recent uploads INCLUDING private/scheduled ones, with their
    status — this is your review queue.
    """
    youtube = youtube_service()

    channel = youtube.channels().list(part="contentDetails", mine=True).execute()
    items = channel.get("items", [])
    if not items:
        return []
    uploads = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    playlist = youtube.playlistItems().list(
        part="contentDetails", playlistId=uploads, maxResults=max_results
    ).execute()
    ids = [v["contentDetails"]["videoId"] for v in playlist.get("items", [])]
    if not ids:
        return []

    videos = youtube.videos().list(part="snippet,status", id=",".join(ids)).execute()
    results = []
    for v in videos.get("items", []):
        status = v["status"]
        results.append({
            "video_id": v["id"],
            "title": v["snippet"]["title"],
            "privacy": status.get("privacyStatus"),
            "publish_at": status.get("publishAt"),  # set if scheduled
        })
    return results


def publish_now(video_id):
    """Approves a private video and makes it public immediately."""
    youtube = youtube_service()
    return youtube.videos().update(
        part="status",
        body={"id": video_id, "status": {"privacyStatus": "public"}},
    ).execute()


def to_rfc3339(local_datetime_text):
    """
    Turns a form value like '2026-06-20T15:00' into '2026-06-20T15:00:00Z'.
    Assumes the time you typed is in UTC. Returns None if empty/invalid.
    """
    if not local_datetime_text:
        return None
    try:
        dt = datetime.fromisoformat(local_datetime_text)
        return dt.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
