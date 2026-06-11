"""
The web frontend. It connects your browser to the backend tools in src/.

Run it with:   python web/app.py
Then open the address it prints (usually http://127.0.0.1:5000) in your browser.

This is the "glue" between the front (HTML pages you see) and the back
(the Python tools that fetch data and generate text).
"""
import os
import sys

# Make the project root importable so "from src import ..." works when you
# run this file directly. (Beginner-friendly: no extra setup needed.)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from flask import Flask, render_template, request

import config
from src import ab_testing, seo

app = Flask(__name__)


@app.route("/")
def home():
    """Dashboard landing page. Shows whether setup is finished."""
    problems = config.check_setup()
    return render_template("index.html", problems=problems)


@app.route("/report")
def report():
    """Shows your channel stats and recent videos as a table."""
    problems = config.check_setup()
    if problems:
        return render_template("report.html", problems=problems)

    error = None
    stats = None
    videos = []
    try:
        # Imported here (not at top) so the rest of the dashboard works even
        # before the YouTube API libraries are fully set up.
        from src import youtube_client
        stats = youtube_client.get_channel_stats(config.MY_CHANNEL_ID)
        videos = youtube_client.get_recent_videos(config.MY_CHANNEL_ID, max_results=10)
        # Add an engagement % to each video for the table.
        for v in videos:
            v["engagement"] = (
                round((v["likes"] + v["comments"]) / v["views"] * 100, 2)
                if v["views"] else 0.0
            )
    except Exception as e:
        error = str(e)

    return render_template("report.html", stats=stats, videos=videos, error=error)


@app.route("/seo", methods=["GET", "POST"])
def seo_page():
    """Form to generate titles, a description, and tags for a topic."""
    result = None
    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        raw_points = request.form.get("points", "").strip()
        points = [p.strip() for p in raw_points.split(",") if p.strip()]
        if topic:
            result = {
                "topic": topic,
                "titles": seo.suggest_titles(topic),
                "description": seo.build_description(topic, points),
                "tags": ", ".join(seo.suggest_tags(topic)),
            }
    return render_template("seo.html", result=result)


@app.route("/experiments", methods=["GET", "POST"])
def experiments_page():
    """List thumbnail/title experiments and add new ones."""
    if request.method == "POST":
        ab_testing.add_variant(
            request.form.get("video", "").strip(),
            request.form.get("variant", "").strip(),
            request.form.get("thumbnail_idea", "").strip(),
            request.form.get("hook_title", "").strip(),
        )
    experiments = ab_testing.list_experiments()
    return render_template("experiments.html", experiments=experiments)


@app.route("/comments", methods=["GET", "POST"])
def comments_page():
    """Form to read public comments on a video."""
    problems = config.check_setup()
    comments = None
    error = None
    video_id = ""
    if request.method == "POST" and not problems:
        video_id = request.form.get("video_id", "").strip()
        try:
            from src import youtube_client
            comments = youtube_client.get_video_comments(video_id)
        except Exception as e:
            error = str(e)
    return render_template(
        "comments.html", problems=problems, comments=comments,
        error=error, video_id=video_id,
    )


if __name__ == "__main__":
    # When hosted online, the host tells us which port to use via $PORT.
    # On your own computer it falls back to 5000.
    port = int(os.environ.get("PORT", 5000))
    # host="0.0.0.0" lets the hosting service expose the site to the internet.
    app.run(host="0.0.0.0", port=port)
