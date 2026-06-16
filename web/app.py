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

from flask import Flask, redirect, render_template, request, url_for

import config
from src import ab_testing, auth, seo

app = Flask(__name__)

# Where uploaded video files are temporarily saved before sending to YouTube.
UPLOAD_DIR = os.path.join(ROOT, "data", "uploads")


@app.route("/")
def home():
    """Dashboard landing page. Shows whether setup is finished."""
    problems = config.check_setup()
    return render_template("index.html", problems=problems,
                           logged_in=auth.is_authorized())


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


@app.route("/ideas", methods=["GET", "POST"])
def ideas_page():
    """AI video-idea generator (Claude API)."""
    ideas = error = topic = None
    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        try:
            from src import ai
            ideas = ai.generate_ideas(topic, count=10)
        except Exception as e:
            error = str(e)
    return render_template("ideas.html", ideas=ideas, error=error, topic=topic)


@app.route("/script", methods=["GET", "POST"])
def script_page():
    """AI script writer (Claude API)."""
    script = error = topic = None
    minutes = 8
    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        try:
            minutes = int(request.form.get("minutes", "8") or 8)
        except ValueError:
            minutes = 8
        style = request.form.get("style", "").strip() or "energetic and friendly"
        try:
            from src import ai
            script = ai.generate_script(topic, minutes=minutes, style=style)
        except Exception as e:
            error = str(e)
    return render_template("script.html", script=script, error=error,
                           topic=topic, minutes=minutes)


@app.route("/status")
def status_page():
    """System Check: verifies credentials/connectivity and feature readiness."""
    from src import healthcheck
    checks = healthcheck.run_checks()
    features = healthcheck.feature_readiness(checks)
    return render_template("status.html", checks=checks, features=features)


@app.route("/analytics")
def analytics_page():
    """Your PRIVATE channel analytics (needs OAuth login)."""
    if not auth.is_authorized():
        return render_template("analytics.html", logged_in=False)

    error = stats = None
    sources = []
    try:
        from src import analytics_api
        stats = analytics_api.overview(days=28)
        sources = analytics_api.traffic_sources(days=28)
    except Exception as e:
        error = str(e)
    return render_template("analytics.html", logged_in=True,
                           stats=stats, sources=sources, error=error)


@app.route("/upload", methods=["GET", "POST"])
def upload_page():
    """Upload a video file as PRIVATE (the review gate). Needs OAuth login."""
    if not auth.is_authorized():
        return render_template("upload.html", logged_in=False)

    message = error = None
    if request.method == "POST":
        try:
            from src import uploader
            file = request.files.get("video")
            if not file or not file.filename:
                raise ValueError("Please choose a video file.")
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            saved = os.path.join(UPLOAD_DIR, file.filename)
            file.save(saved)

            tags = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
            publish_at = uploader.to_rfc3339(request.form.get("publish_at", "").strip())
            vid = uploader.upload_video(
                file_path=saved,
                title=request.form.get("title", "").strip(),
                description=request.form.get("description", "").strip(),
                tags=tags,
                made_with_ai=bool(request.form.get("made_with_ai")),
                publish_at=publish_at,
            )
            os.remove(saved)
            message = (f"Uploaded as PRIVATE (id: {vid}). "
                       "Review it in the Queue, then publish when ready.")
        except Exception as e:
            error = str(e)
    return render_template("upload.html", logged_in=True, message=message, error=error)


@app.route("/queue", methods=["GET", "POST"])
def queue_page():
    """Review queue: see your private/scheduled videos and publish them."""
    if not auth.is_authorized():
        return render_template("queue.html", logged_in=False)

    error = message = None
    videos = []
    try:
        from src import uploader
        if request.method == "POST":
            video_id = request.form.get("video_id", "").strip()
            uploader.publish_now(video_id)
            message = f"Published video {video_id}. It's now public."
        videos = uploader.list_my_videos()
    except Exception as e:
        error = str(e)
    return render_template("queue.html", logged_in=True,
                           videos=videos, message=message, error=error)


if __name__ == "__main__":
    # When hosted online, the host tells us which port to use via $PORT.
    # On your own computer it falls back to 5000.
    port = int(os.environ.get("PORT", 5000))
    # host="0.0.0.0" lets the hosting service expose the site to the internet.
    app.run(host="0.0.0.0", port=port)
