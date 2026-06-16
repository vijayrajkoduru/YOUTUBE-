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


def _mock_scenes(topic, n):
    """Return n {"prompt","narration"} scene dicts for the given topic."""
    topic = (topic or "this topic").strip().rstrip(".") or "this topic"
    templates = [
        {
            "prompt": (
                f"Cinematic opening shot, slow push-in on a modern desk setup at "
                f"golden hour, soft bokeh, a glowing screen showing the words about "
                f"{topic}, shallow depth of field, 4k, photorealistic."
            ),
            "narration": f"Here is what nobody tells you about {topic}.",
        },
        {
            "prompt": (
                f"Dynamic mid shot, hands typing fast on a mechanical keyboard, "
                f"close macro on the keys, cool blue rim light, subtle motion blur, "
                f"illustrating the core idea behind {topic}, 4k, photorealistic."
            ),
            "narration": f"It starts with one simple shift in how you think about {topic}.",
        },
        {
            "prompt": (
                f"Sweeping aerial-style camera move over a stylised data landscape, "
                f"floating UI panels and charts animating, clean tech aesthetic, "
                f"teal and orange palette, representing the impact of {topic}, 4k."
            ),
            "narration": f"And that is exactly why {topic} is changing everything right now.",
        },
        {
            "prompt": (
                f"Confident closing shot, a creator facing the camera in a softly lit "
                f"studio, warm tones, slight slow-motion, gesturing toward the viewer, "
                f"a call-to-action energy about {topic}, 4k, photorealistic."
            ),
            "narration": f"Try {topic} this week, and follow for more like this.",
        },
    ]
    out = []
    i = 0
    while len(out) < n:
        item = dict(templates[i % len(templates)])
        if i >= len(templates):
            item["prompt"] = f"{item['prompt']} Variation {i // len(templates) + 1}."
        out.append(item)
        i += 1
    return out[:n]


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


def generate_scenes(topic, n_scenes=4):
    """Return a list of n_scenes {"prompt","narration"} scene dicts.

    Each "prompt" is an English Veo video-generation prompt describing one
    ~8 second scene; each "narration" is the spoken line for that scene.
    Stitching these clips together produces one multi-scene video.

    Like generate_topics, this uses the real (free) Gemini text API whenever
    GOOGLE_API_KEY is set; DRY_RUN does NOT force mock here (text is free --
    DRY_RUN only gates paid Veo generation and external posting). On any
    error it falls back to a sensible mock list of n_scenes scenes.
    """
    try:
        n_scenes = int(n_scenes)
    except Exception:
        n_scenes = 4
    if n_scenes < 1:
        n_scenes = 1

    if not config.GOOGLE_API_KEY:
        return _mock_scenes(topic, n_scenes)

    client = _client()
    if client is None:
        return _mock_scenes(topic, n_scenes)

    try:
        prompt = (
            f'Break the short-form video idea "{topic}" into a storyboard of exactly '
            f"{n_scenes} sequential scenes. Each scene is about 8 seconds long, and "
            f"together they form one coherent narrative. "
            f"Return STRICT JSON: a JSON array of {n_scenes} objects, each with exactly "
            f'the keys "prompt" and "narration". '
            f'"prompt" must be a vivid English text-to-video generation prompt suitable '
            f"for Google Veo, describing the camera, subject, lighting, mood and motion "
            f"for that single 8-second scene (no spoken words inside the prompt). "
            f'"narration" must be the single spoken line for that scene, short enough to '
            f"say in about 8 seconds. "
            f"Respond with ONLY the JSON array, no markdown fences, no commentary."
        )
        resp = client.models.generate_content(
            model=config.GEMINI_TEXT_MODEL,
            contents=prompt,
        )
        text = (getattr(resp, "text", "") or "").strip()
        data = _parse_json(text)
        if isinstance(data, dict):
            # Model sometimes wraps the list, e.g. {"scenes": [...]}.
            data = _first_list(data)
        if not isinstance(data, list):
            raise ValueError("model output was not a JSON list of scenes")
        cleaned = []
        for item in data:
            if not isinstance(item, dict):
                continue
            scene_prompt = str(item.get("prompt", "")).strip()
            narration = str(item.get("narration", "")).strip()
            if not scene_prompt:
                continue
            cleaned.append({"prompt": scene_prompt, "narration": narration})
            if len(cleaned) >= n_scenes:
                break
        if not cleaned:
            raise ValueError("no usable scenes parsed from model output")
        # Pad with mock scenes if the model returned too few.
        if len(cleaned) < n_scenes:
            extra = _mock_scenes(topic, n_scenes)[len(cleaned):]
            cleaned.extend(extra)
        return cleaned[:n_scenes]
    except Exception as exc:
        log.warning("generate_scenes: real call failed (%s); using mock data.", exc)
        return _mock_scenes(topic, n_scenes)


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
