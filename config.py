"""
Loads your settings from the .env file so the rest of the code can use them.
You should never need to edit this file — just fill in .env.
"""
import os
from dotenv import load_dotenv

# Reads the .env file and makes its values available to the program.
load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
MY_CHANNEL_ID = os.getenv("MY_CHANNEL_ID")

# Optional: only needed for the AI Ideas and Script tools (Claude API).
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Where the A/B test tracker saves its data.
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def check_setup():
    """Returns a friendly error message if something isn't configured yet."""
    problems = []
    if not YOUTUBE_API_KEY or YOUTUBE_API_KEY == "paste_your_api_key_here":
        problems.append("YOUTUBE_API_KEY is missing in your .env file.")
    if not MY_CHANNEL_ID or MY_CHANNEL_ID == "paste_your_channel_id_here":
        problems.append("MY_CHANNEL_ID is missing in your .env file.")
    return problems
