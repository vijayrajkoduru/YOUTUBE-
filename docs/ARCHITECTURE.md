# Project Architecture

A map of how the pieces fit together, so you know where to add things later.

## The big picture

```
You (terminal)
      │
      ▼
   main.py              ← the menu you interact with
      │
      ▼
   src/                 ← the actual tools
   ├── youtube_client.py   talks to YouTube's official API (READ only)
   ├── analytics.py        turns raw numbers into a readable report
   ├── seo.py              generates titles, descriptions, tags
   └── ab_testing.py       records thumbnail/title experiments
      │
      ▼
   config.py            ← loads your secrets from .env
      │
      ▼
   .env                 ← your private API key + channel ID (never shared)

   data/                ← files the tools save (experiments.json)
   templates/           ← fill-in-the-blank docs for your video workflow
   docs/                ← this file + the roadmap
```

## What each file does

| File | Job | Edit it when... |
|------|-----|-----------------|
| `main.py` | The menu / front door | You add a new tool or menu option |
| `config.py` | Loads settings from `.env` | Almost never |
| `src/youtube_client.py` | All API calls live here | You need a new piece of YouTube data |
| `src/analytics.py` | Formats data into reports | You want a new kind of report |
| `src/seo.py` | Title/description/tag templates | You think of better title formulas |
| `src/ab_testing.py` | Saves/loads experiments | You change what you track |

## Design rules (keep the project clean)

1. **All API calls go in `youtube_client.py`.** Don't scatter them around.
2. **Secrets only live in `.env`.** Never type a key directly into code.
3. **One file = one job.** If a file does two unrelated things, split it.
4. **Read-only by default.** This project never tries to post, like, or
   manufacture engagement automatically — that's against YouTube's rules.

## How many "tools" is this?

Four, on purpose — small enough for a beginner to understand fully:
1. Channel report  2. SEO generator  3. A/B experiment tracker  4. Comment reader.

Master these before adding more. A small project you understand beats a big
one you don't.
```
