"""
Turns raw API numbers into a readable report about your own channel,
so you can see which videos work and why.
"""
from tabulate import tabulate

from src import youtube_client


def channel_report(channel_id):
    """Prints a summary of the channel + a table of recent videos."""
    stats = youtube_client.get_channel_stats(channel_id)
    if not stats:
        return "Could not find that channel. Double-check MY_CHANNEL_ID in .env."

    lines = []
    lines.append(f"Channel: {stats['title']}")
    lines.append(f"Subscribers: {stats['subscribers']:,}")
    lines.append(f"Total views: {stats['total_views']:,}")
    lines.append(f"Videos: {stats['video_count']:,}")
    lines.append("")

    videos = youtube_client.get_recent_videos(channel_id, max_results=10)
    if videos:
        # Engagement rate = (likes + comments) / views. A rough "did people care" signal.
        rows = []
        for v in videos:
            engagement = 0.0
            if v["views"]:
                engagement = round((v["likes"] + v["comments"]) / v["views"] * 100, 2)
            rows.append([
                v["title"][:40],
                v["published"],
                f"{v['views']:,}",
                f"{v['likes']:,}",
                f"{v['comments']:,}",
                f"{engagement}%",
            ])
        headers = ["Title", "Date", "Views", "Likes", "Comments", "Engagement"]
        lines.append(tabulate(rows, headers=headers, tablefmt="github"))
        lines.append("")
        lines.append("Tip: your highest-engagement video is your audience telling you")
        lines.append("what to make more of. Lean into that topic and format.")

    return "\n".join(lines)
