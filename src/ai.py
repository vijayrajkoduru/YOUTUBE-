"""
AI-powered idea generation and script writing, via the Claude API.

This is the only part of the project that uses a paid AI service. You need an
ANTHROPIC_API_KEY in your .env (get one at https://console.anthropic.com).
The YouTube tools all work without it — only Ideas and Script need this.
"""
import config

# Anthropic's most capable widely available model.
MODEL = "claude-opus-4-8"


def _client():
    """Builds the Claude client, with a friendly error if the key is missing."""
    import anthropic
    if not config.ANTHROPIC_API_KEY or config.ANTHROPIC_API_KEY == "paste_your_anthropic_key_here":
        raise RuntimeError(
            "ANTHROPIC_API_KEY is missing in your .env file. "
            "Get one at https://console.anthropic.com and add it to use Ideas and Script."
        )
    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def _complete(system, prompt, max_tokens):
    """One streamed Claude call; returns the full text response."""
    client = _client()
    # Stream + get_final_message avoids timeouts on longer outputs.
    with client.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        message = stream.get_final_message()

    if message.stop_reason == "refusal":
        return "(The request was declined. Try rephrasing the topic.)"
    return "".join(b.text for b in message.content if b.type == "text").strip()


def generate_ideas(topic, count=10):
    """Returns a list of video ideas (title + one-line hook) for a niche."""
    system = (
        "You are a seasoned YouTube growth strategist. You suggest video ideas "
        "that are specific, searchable, and have strong click-through potential. "
        "You never suggest anything that fakes engagement or violates YouTube policy."
    )
    prompt = (
        f"My channel is about: {topic}.\n"
        f"Give me {count} video ideas I could realistically make. "
        "For each, output exactly one line in the form:\n"
        "Title — a short reason it would get clicks\n"
        "No numbering, no extra commentary."
    )
    text = _complete(system, prompt, max_tokens=1500)
    ideas = []
    for line in text.splitlines():
        line = line.strip().lstrip("-•").strip()
        if line:
            ideas.append(line)
    return ideas


def generate_script(topic, minutes=8, style="energetic and friendly"):
    """Returns a full video script for the given topic, length, and style."""
    system = (
        "You are an expert YouTube scriptwriter. You write tightly-paced scripts "
        "with a strong hook in the first 15 seconds, clear sections, and a natural "
        "call to action. You write for the ear, not the page."
    )
    prompt = (
        f"Write a YouTube video script.\n"
        f"Topic: {topic}\n"
        f"Target length: about {minutes} minutes when spoken.\n"
        f"Tone/style: {style}.\n\n"
        "Structure it with: a HOOK, then labeled sections, then an OUTRO with a "
        "call to action. Mark rough timestamps. Keep sentences speakable."
    )
    return _complete(system, prompt, max_tokens=6000)
