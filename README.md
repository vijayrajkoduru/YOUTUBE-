# YouTube Growth Toolkit 🎬

A beginner-friendly Python project that helps you grow a real YouTube channel
using YouTube's **official API** — the safe, allowed way. No bots, no fake
views, no banned-account risk.

It gives you four tools:
1. **Channel report** — your subscribers, views, and recent-video stats.
2. **SEO generator** — title, description, and tag suggestions for any video.
3. **A/B test tracker** — log thumbnail/title experiments and compare CTR.
4. **Comment reader** — pull a video's comments so you can reply faster.

> New here? Read [`docs/ROADMAP.md`](docs/ROADMAP.md) first — it explains what to
> learn, what to do, and what to remember, step by step.

---

## Why this instead of "VPN + fake views" automation?

Faking views with VPNs and bot emails **gets channels permanently banned**, and
the fake engagement actually *lowers* your reach (bots hurt your retention and
click-through stats — the things the algorithm rewards). This toolkit improves
the metrics that genuinely grow a channel, and nothing in it can get you banned.

---

## Setup (one time)

### Step 1: Install Python and the libraries
1. Install **Python 3.10+** from [python.org](https://www.python.org/downloads/).
2. Open a terminal in this folder and run:
   ```bash
   python -m venv .venv
   # Activate it:
   #   Windows:  .venv\Scripts\activate
   #   Mac/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```

### Step 2: Get your API key (free)
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (any name).
3. In "APIs & Services", click **Enable APIs**, search for
   **YouTube Data API v3**, and enable it.
4. Go to **Credentials → Create Credentials → API key**. Copy the key.
5. Find your channel ID at
   [youtube.com/account_advanced](https://www.youtube.com/account_advanced)
   (it starts with `UC...`).

### Step 3: Add your secrets
1. Make a copy of `.env.example` and rename the copy to `.env`.
2. Paste your API key and channel ID into it.
3. Save. (The `.gitignore` already stops `.env` from being uploaded — keep it that way.)

---

## Run it

```bash
python main.py
```

Pick a number from the menu and follow the prompts. Start with option **1** to
confirm your setup works.

---

## Project layout

```
main.py          The menu you run
config.py        Loads your settings from .env
src/             The four tools (see docs/ARCHITECTURE.md)
templates/       Fill-in-the-blank docs for your video workflow
docs/            ROADMAP.md (start here) + ARCHITECTURE.md
data/            Files the tools save locally
```

## Safe by design

This project only **reads** public YouTube data and helps you organize your own
work. It never posts, auto-likes, auto-comments, or fakes activity. That's the
point: real, sustainable growth that won't put your channel at risk.
