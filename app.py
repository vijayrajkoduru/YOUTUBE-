"""FastAPI application: the content engine UI + routes.

Flow:
  /topics  -> generate topics -> select one
  select   -> create video asset (draft) + generate Veo placeholder/clip
  /review  -> approve/reject drafts (nothing posts without approval)
  approve  -> worker picks it up and publishes
  /blogs   -> generate a blog draft -> review -> approve -> publish
"""
import os

from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import config
import db
from providers import gemini, veo
from worker import start_worker

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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
    # Create a video asset in draft, then generate the Veo clip immediately.
    detail = {"hook": hook}
    asset_id = db.create_asset(kind="video", topic=title, title=title, detail=detail)
    prompt = f"{title}. {hook}".strip()
    try:
        result = veo.generate_video(prompt=prompt, seconds=8)
        db.set_video(asset_id, result["path"], result["cost"])
    except Exception as exc:  # cost guard or generation error -> mark failed
        db.set_status(asset_id, "failed", error=str(exc))
    return RedirectResponse(url="/review", status_code=303)


# ---------------------------------------------------------------------------
# Review queue
# ---------------------------------------------------------------------------
@app.get("/review", response_class=HTMLResponse)
def review_page(request: Request):
    drafts = db.list_assets(status="draft")
    return templates.TemplateResponse(request, "review.html", _ctx(request, drafts=drafts))


@app.post("/review/{asset_id}/approve")
def review_approve(asset_id: int):
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
    return RedirectResponse(url="/review", status_code=303)


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
# Settings
# ---------------------------------------------------------------------------
@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    return templates.TemplateResponse(
        request,
        "settings.html",
        _ctx(
            request,
            keys=config.keys_status(),
            veo_model=config.VEO_MODEL,
            month_cost=db.month_cost_usd(),
            monthly_cap=config.VEO_MONTHLY_USD_CAP,
            day_clips=db.day_clip_count(),
            daily_cap=config.VEO_DAILY_CLIP_CAP,
        ),
    )
