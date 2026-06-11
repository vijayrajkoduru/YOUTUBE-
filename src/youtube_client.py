"""
A thin wrapper around the official YouTube Data API.

This only READS public data (your channel stats, your videos, public comments).
It never tries to fake views, likes, or comments — that would get your
channel banned and isn't what this project is for.
"""
from googleapiclient.discovery import build

import config


def _service():
    """Builds the API client using your API key."""
    return build("youtube", "v3", developerKey=config.YOUTUBE_API_KEY)


def get_channel_stats(channel_id):
    """Returns subscriber count, total views, and video count for a channel."""
    youtube = _service()
    response = youtube.channels().list(
        part="snippet,statistics",
        id=channel_id,
    ).execute()

    items = response.get("items", [])
    if not items:
        return None

    channel = items[0]
    stats = channel["statistics"]
    return {
        "title": channel["snippet"]["title"],
        "subscribers": int(stats.get("subscriberCount", 0)),
        "total_views": int(stats.get("viewCount", 0)),
        "video_count": int(stats.get("videoCount", 0)),
    }


def get_recent_videos(channel_id, max_results=10):
    """Returns the channel's most recent uploads with their stats."""
    youtube = _service()

    # Every channel has a hidden "uploads" playlist that holds all its videos.
    channel = youtube.channels().list(
        part="contentDetails", id=channel_id
    ).execute()
    items = channel.get("items", [])
    if not items:
        return []
    uploads_playlist = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    playlist = youtube.playlistItems().list(
        part="contentDetails",
        playlistId=uploads_playlist,
        maxResults=max_results,
    ).execute()
    video_ids = [v["contentDetails"]["videoId"] for v in playlist.get("items", [])]
    if not video_ids:
        return []

    videos = youtube.videos().list(
        part="snippet,statistics",
        id=",".join(video_ids),
    ).execute()

    results = []
    for v in videos.get("items", []):
        stats = v["statistics"]
        results.append({
            "video_id": v["id"],
            "title": v["snippet"]["title"],
            "published": v["snippet"]["publishedAt"][:10],
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
        })
    return results


def get_video_comments(video_id, max_results=20):
    """Returns the top public comments on a video so you can reply faster."""
    youtube = _service()
    response = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=max_results,
        order="relevance",
    ).execute()

    comments = []
    for thread in response.get("items", []):
        top = thread["snippet"]["topLevelComment"]["snippet"]
        comments.append({
            "author": top["authorDisplayName"],
            "text": top["textDisplay"],
            "likes": top["likeCount"],
        })
    return comments
