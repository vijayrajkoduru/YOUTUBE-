"""
Turn script text into a spoken-voice MP3 (text-to-speech).

Uses gTTS, which is free and needs no API key, but does require an internet
connection at runtime (it calls Google's free TTS voice). The voice is basic —
fine for drafts and faceless-video tests. You can swap in a higher-quality
paid voice (ElevenLabs, Google Cloud TTS) later by editing this one file.
"""
import os

import config

OUT_DIR = os.path.join(config.DATA_DIR, "voiceovers")


def make_voiceover(text, filename="voiceover.mp3", lang="en"):
    """Converts text to an MP3 and returns its file path."""
    from gtts import gTTS

    if not text or not text.strip():
        raise ValueError("There's no text to convert to speech.")

    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, filename)
    gTTS(text=text, lang=lang).save(path)
    return path
