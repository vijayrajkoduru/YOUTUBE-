"""Gemini text provider: trending topics + blog drafting.

Uses the real google-genai SDK (model gemini-2.5-flash) whenever
GOOGLE_API_KEY is present. Text generation is free, so it runs even in
DRY_RUN (DRY_RUN only gates paid Veo generation and external posting).
Otherwise returns realistic mock data. Never raises on a missing key or an
SDK error -- always falls back to mock.
"""
import json
import logging

import config

log = logging.getLogger("content_engine.gemini")


# ---------------------------------------------------------------------------
# Mock data (used in DRY_RUN or when no key / on any error).
# ---------------------------------------------------------------------------
def _mock_topics(n):
    base = [
        {
            "title": "AI agents are quietly replacing SaaS dashboards",
            "hook": "Why click through 12 tabs when an agent does it in one prompt?",
            "why": "Agentic workflows are trending across dev and ops communities.",
        },
        {
            "title": "The 5-minute home lab for learning cybersecurity",
            "hook": "You do not need a $2000 rig to start breaking things safely.",
            "why": "Evergreen demand; beginners search this constantly.",
        },
        {
            "title": "Veo 3 changed short-form video overnight",
            "hook": "One prompt, eight seconds, broadcast quality. Here is the catch.",
            "why": "Generative video is the hottest creator topic right now.",
        },
        {
            "title": "Stop paying for 9 tools that one open-source app replaces",
            "hook": "Your stack is bloated. Here is the lean version.",
            "why": "Cost-cutting content performs well in a tight economy.",
        },
        {
            "title": "Prompt injection is the new SQL injection",
            "hook": "Your LLM app is one clever string away from leaking everything.",
            "why": "Security + AI overlap is high-engagement on every platform.",
        },
        {
            "title": "I automated my entire content pipeline with Python",
            "hook": "Topics to published in three clicks. Here is the build.",
            "why": "Build-in-public automation content reliably trends.",
        },
        {
            "title": "WordPress is still the smartest blog backbone in 2026",
            "hook": "Everyone left. The ones who stayed are winning SEO.",
            "why": "Contrarian SEO takes drive shares and comments.",
        },
        {
            "title": "The free tier that beats most paid AI plans",
            "hook": "You are probably overpaying for tokens you do not use.",
            "why": "Free-tier optimization is endlessly clickable.",
        },
        {
            "title": "How to ship a side project before you lose interest",
            "hook": "The 72-hour rule that actually finishes projects.",
            "why": "Productivity-for-builders content has a loyal audience.",
        },
        {
            "title": "Self-hosting in 2026: what finally got easy",
            "hook": "The homelab renaissance nobody is talking about.",
            "why": "Self-hosting is resurging with privacy-conscious users.",
        },
    ]
    out = []
    i = 0
    while len(out) < n:
        item = dict(base[i % len(base)])
        if i >= len(base):
            item["title"] = f"{item['title']} (variant {i // len(base) + 1})"
        out.append(item)
        i += 1
    return out[:n]


def _mock_blog(topic):
    title = topic.strip().rstrip(".") if topic else "Untitled Draft"
    title = title[:1].upper() + title[1:]
    html = (
        f"<h1>{title}</h1>"
        f"<p>This is a DRY_RUN placeholder blog draft about "
        f"<strong>{topic}</strong>. With a real GOOGLE_API_KEY and DRY_RUN=false, "
        f"this section is written by Gemini.</p>"
        f"<h2>Why it matters</h2>"
        f"<p>A short, punchy explanation of the trend and who should care.</p>"
        f"<h2>How to get started</h2>"
        f"<ol><li>Understand the core idea.</li>"
        f"<li>Try the smallest possible version.</li>"
        f"<li>Ship it and iterate.</li></ol>"
        f"<h2>Takeaway</h2>"
        f"<p>The practical one-line summary readers can act on today.</p>"
    )
    return {
        "title": title,
        "html": html,
        "tags": ["ai", "automation", "tutorial"],
    }


def _client():
    """Build a google-genai client, or None if unavailable."""
    try:
        from google import genai  # noqa: WPS433 (lazy import is intentional)
    except Exception as exc:
        log.warning("google-genai SDK not importable (%s); using mock data.", exc)
        return None
    try:
        return genai.Client(api_key=config.GOOGLE_API_KEY)
    except Exception as exc:
        log.warning("google-genai client init failed (%s); using mock data.", exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_topics(n=10):
    """Return a list of {"title","hook","why"} trending topic dicts.

    Text generation uses the real Gemini free-tier API whenever a key is
    present -- it is free and spends nothing, so DRY_RUN does NOT force mock
    here (DRY_RUN only gates paid Veo generation and external posting).
    """
    if not config.GOOGLE_API_KEY:
        return _mock_topics(n)

    client = _client()
    if client is None:
        return _mock_topics(n)

    try:
        prompt = (
            f"Generate {n} trending, high-engagement, high-CTR content topics for a "
            f"tech / AI / cybersecurity creator. Each must be genuinely click-worthy. "
            f"Return STRICT JSON: a JSON array of {n} objects, each with exactly the "
            f'keys "title" (a punchy headline), "hook" (a one-line scroll-stopper), '
            f'and "why" (why it trends / will get clicks). '
            f"Respond with ONLY the JSON array, no markdown, no commentary."
        )
        resp = client.models.generate_content(
            model=config.GEMINI_TEXT_MODEL,
            contents=prompt,
        )
        text = (getattr(resp, "text", "") or "").strip()
        data = _parse_json(text)
        if isinstance(data, dict):
            # Model sometimes wraps the list, e.g. {"topics": [...]}.
            data = _first_list(data)
        if not isinstance(data, list):
            raise ValueError("model output was not a JSON list of topics")
        cleaned = []
        for item in data:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            cleaned.append(
                {
                    "title": title,
                    "hook": str(item.get("hook", "")).strip(),
                    "why": str(item.get("why", "")).strip(),
                }
            )
            if len(cleaned) >= n:
                break
        if not cleaned:
            raise ValueError("no usable topics parsed from model output")
        return cleaned
    except Exception as exc:
        log.warning("generate_topics: real call failed (%s); using mock data.", exc)
        return _mock_topics(n)


def write_blog(topic):
    """Return {"title","html","tags":[...]} for the given topic.

    Like generate_topics, this uses the real (free) Gemini text API whenever
    GOOGLE_API_KEY is set; DRY_RUN does not force mock here.
    """
    if not config.GOOGLE_API_KEY:
        return _mock_blog(topic)

    client = _client()
    if client is None:
        return _mock_blog(topic)

    try:
        prompt = (
            f'Write a complete, well-structured blog post about: "{topic}". '
            f"Return STRICT JSON, a single object, with keys: "
            f'"title" (string), "html" (the full article body as clean HTML using '
            f"h1/h2/p/ul/ol/li tags, no inline styles, no <html>/<head>/<body> "
            f'wrapper), and "tags" (a list of 3-5 lowercase string tags). '
            f"Respond with ONLY the JSON object, no markdown fences, no commentary."
        )
        resp = client.models.generate_content(
            model=config.GEMINI_TEXT_MODEL,
            contents=prompt,
        )
        text = (getattr(resp, "text", "") or "").strip()
        data = _parse_json(text)
        if not isinstance(data, dict):
            raise ValueError("model output was not a JSON object")
        title = str(data.get("title", topic)).strip() or topic
        html = str(data.get("html", "")).strip()
        raw_tags = data.get("tags", [])
        if not isinstance(raw_tags, list):
            raw_tags = []
        tags = [str(t).strip().lower() for t in raw_tags if str(t).strip()]
        if not html:
            raise ValueError("model output had no html body")
        return {"title": title, "html": html, "tags": tags or ["ai"]}
    except Exception as exc:
        log.warning("write_blog: real call failed (%s); using mock data.", exc)
        return _mock_blog(topic)


def _strip_code_fence(text):
    """Remove a leading/trailing ```json ... ``` fence if the model added one."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1] if "\n" in t else t
        if t.endswith("```"):
            t = t[: -3]
        # drop a leading language tag line like "json"
        if t.lstrip().lower().startswith("json"):
            t = t.lstrip()[4:]
    return t.strip()


def _extract_json_blob(text):
    """Return the first balanced JSON array/object substring, or None.

    Handles the case where the model wraps valid JSON in prose. Respects
    strings and escapes so braces/brackets inside string values are ignored.
    """
    start = None
    opener = None
    closer = None
    for idx, ch in enumerate(text):
        if ch in "[{":
            start = idx
            opener = ch
            closer = "]" if ch == "[" else "}"
            break
    if start is None:
        return None
    depth = 0
    in_str = False
    escape = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return text[start: idx + 1]
    return None


def _parse_json(text):
    """Robustly parse JSON from a model response (list or dict).

    Tries the fenced/clean text first, then falls back to extracting a
    balanced JSON blob embedded in surrounding prose.
    """
    cleaned = _strip_code_fence(text)
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    blob = _extract_json_blob(cleaned) or _extract_json_blob(text)
    if blob is not None:
        return json.loads(blob)
    raise ValueError("no parseable JSON found in model output")


def _first_list(data):
    """Return the first list value found in a dict, else the dict itself."""
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                return value
    return data
