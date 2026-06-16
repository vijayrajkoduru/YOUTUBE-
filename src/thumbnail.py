"""
Generate YouTube thumbnails (1280x720) from text, using Pillow.

Fully offline — no API key needed. Fonts are bundled in assets/fonts so this
works the same on any computer. These are starting points: a clean, readable
thumbnail you can refine in Canva/Photopea afterward.
"""
import os

from PIL import Image, ImageDraw, ImageFont

import config

WIDTH, HEIGHT = 1280, 720  # standard YouTube thumbnail size
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(ROOT, "assets", "fonts")
OUT_DIR = os.path.join(config.DATA_DIR, "thumbnails")

# (background, text) color pairs.
PALETTES = {
    "red": ((230, 0, 40), (255, 255, 255)),
    "dark": ((17, 17, 17), (255, 210, 60)),
    "blue": ((37, 99, 235), (255, 255, 255)),
    "green": ((22, 163, 74), (255, 255, 255)),
}


def _font(size, bold=True):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def _wrap(draw, text, font, max_width):
    """Greedy word-wrap so the title fits the thumbnail width."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = (current + " " + word).strip()
        if current and draw.textlength(candidate, font=font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def make_thumbnail(title, subtitle="", color="red"):
    """Renders a thumbnail PNG and returns its file path."""
    bg, fg = PALETTES.get(color, PALETTES["red"])
    img = Image.new("RGB", (WIDTH, HEIGHT), bg)
    draw = ImageDraw.Draw(img)

    title_font = _font(112)
    lines = _wrap(draw, title.upper(), title_font, WIDTH - 160)
    line_height = 128
    block_height = len(lines) * line_height
    y = (HEIGHT - block_height) // 2 - (40 if subtitle else 0)

    for line in lines:
        x = (WIDTH - draw.textlength(line, font=title_font)) // 2
        # Black outline keeps text readable over any background.
        draw.text((x, y), line, font=title_font, fill=fg,
                  stroke_width=7, stroke_fill=(0, 0, 0))
        y += line_height

    if subtitle:
        sub_font = _font(50, bold=False)
        x = (WIDTH - draw.textlength(subtitle, font=sub_font)) // 2
        draw.text((x, y + 12), subtitle, font=sub_font, fill=fg,
                  stroke_width=4, stroke_fill=(0, 0, 0))

    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "thumbnail.png")
    img.save(path)
    return path
