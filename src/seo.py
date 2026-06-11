"""
Generates SEO-friendly titles, descriptions, and tags for a video.

These are TEMPLATES to start from — always edit them so they sound like you.
Good metadata helps YouTube understand and recommend your video. It is 100%
allowed and is one of the few "free" wins available to a small channel.
"""

# Proven title shapes. {topic} gets replaced with your video's subject.
TITLE_FORMULAS = [
    "How to {topic} (Step-by-Step for Beginners)",
    "{topic} — 7 Mistakes Everyone Makes",
    "I Tried {topic} for 30 Days. Here's What Happened",
    "The Truth About {topic} Nobody Tells You",
    "{topic} Explained in 10 Minutes",
    "Stop Doing {topic} Wrong — Do This Instead",
    "{topic}: A Complete Guide for 2026",
]


def suggest_titles(topic):
    """Returns a list of ready-to-tweak title options for a topic."""
    return [formula.format(topic=topic) for formula in TITLE_FORMULAS]


def build_description(topic, key_points, links=None):
    """
    Builds a structured description.
    - First 2 lines matter most (they show above "...more").
    - key_points: a list of strings, turned into timestamps/bullets.
    - links: optional dict like {"Instagram": "https://..."}.
    """
    lines = []
    lines.append(f"In this video you'll learn everything about {topic}.")
    lines.append("Watch till the end for the part most people miss. 👇")
    lines.append("")

    if key_points:
        lines.append("What's covered:")
        for point in key_points:
            lines.append(f"• {point}")
        lines.append("")

    if links:
        lines.append("Find me here:")
        for name, url in links.items():
            lines.append(f"{name}: {url}")
        lines.append("")

    lines.append("If this helped, like and subscribe for more. 🙏")
    return "\n".join(lines)


def suggest_tags(topic, extra=None):
    """Returns a tag list: the topic, common variations, and any extras."""
    base = [
        topic,
        f"{topic} tutorial",
        f"{topic} for beginners",
        f"how to {topic}",
        f"{topic} 2026",
        f"{topic} explained",
        f"best {topic} tips",
    ]
    if extra:
        base.extend(extra)
    # Remove duplicates while keeping order.
    seen = set()
    return [t for t in base if not (t in seen or seen.add(t))]
