"""FastAPI application: the content engine UI + routes.

Flow:
  /topics  -> generate topics -> select one
  select   -> generate scenes -> build (stitch) a multi-scene video -> draft
  /review  -> edit caption/networks (video) or title/html/targets (blog),
              then approve/reject. NOTHING posts or spends without approval.
  approve  -> worker picks it up and publishes to the chosen networks/targets
  /history -> posted + failed assets with their per-target result links
  /settings-> go-live checklist + Veo cost usage vs caps
"""
import os

from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import config
import db
from providers import gemini, video_pipeline
from worker import (
    start_worker,
    DEFAULT_VIDEO_NETWORKS,
    DEFAULT_BLOG_TARGETS,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(BASE_DIR, "data", "videos")

ALL_NETWORKS = ["instagram", "facebook", "x", "linkedin"]
ALL_BLOG_TARGETS = ["wordpress", "devto", "hashnode"]

app = FastAPI(title="Content Engine")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


@app.on_event("startup")
def _on_startup():
    db.init_db()
    start_worker()


def _ctx(request, **extra):
    """Base template context shared by every page."""
    ctx = {"request": request, "dry_run": config.DRY_RUN}
    ctx.update(extra)
    return ctx


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    all_assets = db.list_assets()
    counts = {s: 0 for s in db.VALID_STATUSES}
    for a in all_assets:
        counts[a["status"]] = counts.get(a["status"], 0) + 1
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        _ctx(
            request,
            counts=counts,
            total=len(all_assets),
            keys=config.keys_status(),
            recent=all_assets[:10],
        ),
    )


# ---------------------------------------------------------------------------
# Topics
# ---------------------------------------------------------------------------
@app.get("/topics", response_class=HTMLResponse)
def topics_page(request: Request):
    return templates.TemplateResponse(request, "topics.html", _ctx(request, topics=None))


@app.post("/topics/generate", response_class=HTMLResponse)
def topics_generate(request: Request):
    topics = gemini.generate_topics(n=10)
    return templates.TemplateResponse(request, "topics.html", _ctx(request, topics=topics))


@app.post("/topics/select")
def topics_select(title: str = Form(...), hook: str = Form("")):
    """Storyboard the topic, stitch a multi-scene video, create a draft.

    generate_scenes() is free Gemini text (runs even in DRY_RUN). build_video()
    runs the per-scene Veo clips through the cost guard + DRY_RUN placeholder and
    stitches them into one mp4. Nothing posts here -- the draft waits for review.
    """
    topic = f"{title}. {hook}".strip(". ").strip()
    detail = {"hook": hook}
    asset_id = db.create_asset(kind="video", topic=title, title=title, detail=detail)

    try:
        scenes = gemini.generate_scenes(topic or title, n_scenes=4)
        result = video_pipeline.build_video(scenes, VIDEO_DIR, seconds=8)
        db.update_asset(
            asset_id,
            scenes=scenes,
            caption=title,  # default caption = title; editable before approval
            networks=DEFAULT_VIDEO_NETWORKS,
            video_path=result.get("path"),
            cost=float(result.get("cost") or 0),
        )
        if not result.get("path"):
            db.set_status(asset_id, "failed", error="video build produced no file")
    except Exception as exc:  # cost guard or generation error -> mark failed
        db.set_status(asset_id, "failed", error=str(exc))
    return RedirectResponse(url="/review", status_code=303)


# ---------------------------------------------------------------------------
# Review queue
# ---------------------------------------------------------------------------
@app.get("/review", response_class=HTMLResponse)
def review_page(request: Request):
    drafts = db.list_assets(status="draft")
    return templates.TemplateResponse(
        request,
        "review.html",
        _ctx(
            request,
            drafts=drafts,
            all_networks=ALL_NETWORKS,
            all_blog_targets=ALL_BLOG_TARGETS,
        ),
    )


def _checked_list(raw, allowed):
    """Normalize a comma-joined / repeated form field into an allowed subset.

    The review form posts each checkbox under the same name; FastAPI's Form()
    with a single str gives the first value only, so the template joins selected
    boxes into a comma string in a hidden mirror. We accept either shape.
    """
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        items = list(raw)
    else:
        items = [p.strip() for p in str(raw).split(",")]
    return [i for i in items if i in allowed]


@app.post("/review/{asset_id}/approve")
async def review_approve(asset_id: int, request: Request):
    """Save the user's edits, then flip the asset to approved.

    Video: caption (textarea) + networks (checkboxes).
    Blog:  title + html (textareas) + targets (checkboxes).
    Reads the raw form so repeated checkbox fields are captured correctly.
    """
    asset = db.get_asset(asset_id)
    if not asset:
        return RedirectResponse(url="/review", status_code=303)

    form = await request.form()

    if asset["kind"] == "video":
        caption = (form.get("caption") or asset.get("caption") or asset.get("title") or "").strip()
        networks = _checked_list(form.getlist("networks"), ALL_NETWORKS)
        if not networks:
            networks = DEFAULT_VIDEO_NETWORKS
        db.update_asset(asset_id, caption=caption, networks=networks)
    else:  # blog
        title = (form.get("title") or asset.get("title") or "").strip()
        html = form.get("html")
        if html is None:
            html = asset.get("blog_html") or ""
        targets = _checked_list(form.getlist("targets"), ALL_BLOG_TARGETS)
        if not targets:
            targets = DEFAULT_BLOG_TARGETS
        db.update_asset(asset_id, title=title, blog_html=html, targets=targets)

    db.set_status(asset_id, "approved")
    return RedirectResponse(url="/review", status_code=303)


@app.post("/review/{asset_id}/reject")
def review_reject(asset_id: int):
    db.set_status(asset_id, "rejected")
    return RedirectResponse(url="/review", status_code=303)


# ---------------------------------------------------------------------------
# Blogs
# ---------------------------------------------------------------------------
@app.get("/blogs", response_class=HTMLResponse)
def blogs_page(request: Request):
    return templates.TemplateResponse(request, "blogs.html", _ctx(request))


@app.post("/blogs/generate")
def blogs_generate(topic: str = Form(...)):
    blog = gemini.write_blog(topic)
    detail = {"tags": blog.get("tags", [])}
    asset_id = db.create_asset(
        kind="blog", topic=topic, title=blog["title"], detail=detail
    )
    db.set_blog(asset_id, blog["html"], blog["title"])
    db.update_asset(asset_id, targets=DEFAULT_BLOG_TARGETS)
    return RedirectResponse(url="/review", status_code=303)


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------
@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request):
    assets = db.list_assets(statuses=("posted", "failed"))
    return templates.TemplateResponse(request, "history.html", _ctx(request, assets=assets))


# ---------------------------------------------------------------------------
# Media serving
# ---------------------------------------------------------------------------
@app.get("/media/{asset_id}")
def media(asset_id: int):
    asset = db.get_asset(asset_id)
    if not asset or not asset.get("video_path") or not os.path.exists(asset["video_path"]):
        return HTMLResponse("media not found", status_code=404)
    return FileResponse(asset["video_path"], media_type="video/mp4")


# ---------------------------------------------------------------------------
# Settings / go-live checklist
# ---------------------------------------------------------------------------
def _go_live_checklist():
    """Per-integration readiness: configured? what is still missing?

    Returns a list of {name, ok, missing} rows describing exactly what needs to
    be set to go live for each integration.
    """
    checklist = []

    def add(name, ok, missing):
        checklist.append({"name": name, "ok": bool(ok), "missing": missing})

    # Generation
    add(
        "Gemini text (topics + blogs + scenes)",
        bool(config.GOOGLE_API_KEY),
        "" if config.GOOGLE_API_KEY else "set GOOGLE_API_KEY (free tier works)",
    )
    add(
        "Veo video generation",
        bool(config.GOOGLE_API_KEY),
        "" if config.GOOGLE_API_KEY else "set GOOGLE_API_KEY (paid; gated by cost caps)",
    )

    # Social fan-out
    add(
        "Social posting (Upload-Post)",
        bool(config.UPLOAD_POST_API_KEY),
        "" if config.UPLOAD_POST_API_KEY else "set UPLOAD_POST_API_KEY (and UPLOAD_POST_USER)",
    )

    # Blog targets
    wp_missing = []
    if not config.WORDPRESS_URL:
        wp_missing.append("WORDPRESS_URL")
    if not config.WORDPRESS_USER:
        wp_missing.append("WORDPRESS_USER")
    if not config.WORDPRESS_APP_PASSWORD:
        wp_missing.append("WORDPRESS_APP_PASSWORD")
    add(
        "WordPress",
        not wp_missing,
        "" if not wp_missing else "set " + ", ".join(wp_missing),
    )
    add(
        "Dev.to",
        bool(config.DEVTO_API_KEY),
        "" if config.DEVTO_API_KEY else "set DEVTO_API_KEY",
    )
    hn_missing = []
    if not config.HASHNODE_TOKEN:
        hn_missing.append("HASHNODE_TOKEN")
    if not config.HASHNODE_PUBLICATION_ID:
        hn_missing.append("HASHNODE_PUBLICATION_ID")
    add(
        "Hashnode",
        not hn_missing,
        "" if not hn_missing else "set " + ", ".join(hn_missing),
    )

    # The final go-live switch.
    add(
        "DRY_RUN turned off",
        not config.DRY_RUN,
        "" if not config.DRY_RUN else "set DRY_RUN=false in .env to actually post/spend",
    )

    return checklist


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    checklist = _go_live_checklist()
    ready = all(row["ok"] for row in checklist)
    return templates.TemplateResponse(
        request,
        "settings.html",
        _ctx(
            request,
            keys=config.keys_status(),
            checklist=checklist,
            ready=ready,
            veo_model=config.VEO_MODEL,
            month_cost=db.month_cost_usd(),
            monthly_cap=config.VEO_MONTHLY_USD_CAP,
            day_clips=db.day_clip_count(),
            daily_cap=config.VEO_DAILY_CLIP_CAP,
        ),
    )
