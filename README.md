# Content Engine

An AI content engine that:

1. Generates trending TOPICS on a button click.
2. Lets you pick one topic.
3. Generates a VIDEO with Veo 3.
4. Shows everything in an APPROVE / REJECT review queue (nothing posts or spends without approval).
5. On approve, posts the video to Instagram / Facebook / X / LinkedIn via the Upload-Post aggregator.
6. Also generates BLOGS and publishes them to WordPress (canonical) + Dev.to + Hashnode.

## DRY_RUN (default ON)

`DRY_RUN=true` (the default) makes the app fully runnable with ZERO paid keys and ZERO posting or spend:

- Veo returns a tiny placeholder mp4 (cost 0).
- Social and blog publishing only LOG what they WOULD send ("DRY_RUN (not sent)").
- Topic and blog TEXT use the real Gemini free-tier API if `GOOGLE_API_KEY` is set, otherwise realistic mock data.

Flip `DRY_RUN=false` and add keys to go live. Veo always respects a hard cost guard regardless.

## Run

```
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env          # optional; defaults already run in DRY_RUN

uvicorn app:app --reload
```

Open http://127.0.0.1:8000

### Click-through (works in DRY_RUN with no keys)

1. Topics -> Generate Topics -> Select one (creates a video asset + placeholder clip).
2. Review -> preview the clip -> Approve.
3. The background worker picks it up and logs `posted` (DRY_RUN: not sent).
4. Blogs -> enter a topic -> Generate -> Review -> Approve -> worker logs `posted`.

## Keys to go live (add to .env)

| Key | What it is | Where to get it |
| --- | --- | --- |
| `GOOGLE_API_KEY` | Gemini text + Veo video | Google AI Studio. Veo requires a billing-enabled Google Cloud / paid tier. |
| `UPLOAD_POST_API_KEY` | Social aggregator (IG/FB/X/LinkedIn) | upload-post.com dashboard. |
| `WORDPRESS_URL` / `WORDPRESS_USER` / `WORDPRESS_APP_PASSWORD` | Canonical blog (REST + Application Password) | WP admin -> Users -> Profile -> Application Passwords. |
| `DEVTO_API_KEY` | Dev.to cross-post | dev.to -> Settings -> Extensions -> API Keys. |
| `HASHNODE_TOKEN` / `HASHNODE_PUBLICATION_ID` | Hashnode cross-post (GraphQL PAT) | hashnode.com -> Developer Settings -> Personal Access Tokens; publication ID from your blog dashboard. |

Set `DRY_RUN=false` once keys are in place.

## Cost guard (Veo)

Veo generation is blocked BEFORE any spend if either cap would be exceeded:

- `VEO_MONTHLY_USD_CAP` (default 20) — total estimated Veo spend this month.
- `VEO_DAILY_CLIP_CAP` (default 10) — number of clips generated today.

Cost per clip is estimated as `seconds * VEO_USD_PER_SECOND`. In DRY_RUN the cost is always 0 and the guard is not triggered.

## Layout

```
.env.example      requirements.txt   config.py   db.py
app.py            worker.py          README.md   .gitignore
providers/        __init__.py gemini.py veo.py social.py blogpub.py
templates/        base.html dashboard.html topics.html review.html blogs.html settings.html
static/           style.css
data/             engine.db (created on first run; gitignored)
```

## Safety model

- Secrets live only in `.env` (never hardcoded; `.env` is gitignored).
- Every provider degrades gracefully: DRY_RUN or a missing key returns mock data or "not sent" and never crashes the app.
- The only intentional hard failure is the Veo cost guard, which protects against runaway spend.
