"""
Your PRIVATE channel analytics, via the YouTube Analytics API.

This is the data that actually drives growth decisions — watch time, average
view percentage (retention), and where your traffic comes from. The public API
(youtube_client.py) can't see these; this needs OAuth login (see auth.py).
"""
from datetime import date, timedelta

from src.auth import analytics_service


def overview(days=28):
    """
    Returns top-line numbers for the last `days` days:
    views, watch-time minutes, average view duration & percentage, subs, likes.
    """
    ya = analytics_service()
    end = date.today()
    start = end - timedelta(days=days)

    resp = ya.reports().query(
        ids="channel==MINE",
        startDate=start.isoformat(),
        endDate=end.isoformat(),
        metrics=("views,estimatedMinutesWatched,averageViewDuration,"
                 "averageViewPercentage,subscribersGained,likes"),
    ).execute()

    headers = [h["name"] for h in resp.get("columnHeaders", [])]
    rows = resp.get("rows", [])
    if not rows:
        return None
    values = dict(zip(headers, rows[0]))
    return {
        "days": days,
        "views": int(values.get("views", 0)),
        "watch_time_minutes": int(values.get("estimatedMinutesWatched", 0)),
        "avg_view_duration_sec": int(values.get("averageViewDuration", 0)),
        "avg_view_percentage": round(float(values.get("averageViewPercentage", 0)), 1),
        "subscribers_gained": int(values.get("subscribersGained", 0)),
        "likes": int(values.get("likes", 0)),
    }


def top_videos(days=28, limit=10):
    """Returns your best videos by views in the period, with retention %."""
    ya = analytics_service()
    end = date.today()
    start = end - timedelta(days=days)

    resp = ya.reports().query(
        ids="channel==MINE",
        startDate=start.isoformat(),
        endDate=end.isoformat(),
        metrics="views,averageViewPercentage",
        dimensions="video",
        sort="-views",
        maxResults=limit,
    ).execute()

    results = []
    for row in resp.get("rows", []):
        results.append({
            "video_id": row[0],
            "views": int(row[1]),
            "avg_view_percentage": round(float(row[2]), 1),
        })
    return results


def traffic_sources(days=28):
    """Returns where your views came from (search, suggested, browse, etc.)."""
    ya = analytics_service()
    end = date.today()
    start = end - timedelta(days=days)

    resp = ya.reports().query(
        ids="channel==MINE",
        startDate=start.isoformat(),
        endDate=end.isoformat(),
        metrics="views",
        dimensions="insightTrafficSourceType",
        sort="-views",
    ).execute()

    return [{"source": row[0], "views": int(row[1])} for row in resp.get("rows", [])]
