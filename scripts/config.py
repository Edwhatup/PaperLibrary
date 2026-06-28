"""Central config. Everything is overridable via environment variables so the
GitHub Action and local runs share the same code."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# --- Paths ---------------------------------------------------------------
DATA = ROOT / "data"
PAPERS_DIR = DATA / "papers"      # raw HF daily-paper metadata (json)
SCRIPTS_DIR = DATA / "scripts"    # generated 导读 scripts (md/txt)
LIBRARY = ROOT / "library"        # human-readable markdown library
PUBLIC = ROOT / "public"          # published site: audio + rss.xml + index
AUDIO_DIR = PUBLIC / "audio"

for _p in (PAPERS_DIR, SCRIPTS_DIR, LIBRARY, AUDIO_DIR):
    _p.mkdir(parents=True, exist_ok=True)

# --- Fetch ---------------------------------------------------------------
# How many top (most up-voted) papers per day to turn into audio.
MAX_PAPERS = int(os.getenv("MAX_PAPERS", "5"))

# --- Script / 导读 language ----------------------------------------------
# "zh" -> Chinese digest (needs an LLM), "en" -> English digest.
DIGEST_LANG = os.getenv("DIGEST_LANG", "zh")

# LLM backend for turning an abstract into a spoken 导读 script.
# One of: "gemini", "anthropic", "none" (none -> read the abstract verbatim).
LLM_BACKEND = os.getenv("LLM_BACKEND", "none")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

# --- TTS (edge-tts, free) ------------------------------------------------
# Voices: zh-CN-XiaoxiaoNeural / zh-CN-YunxiNeural / en-US-AriaNeural ...
# `edge-tts --list-voices` shows the full list.
TTS_VOICE_ZH = os.getenv("TTS_VOICE_ZH", "zh-CN-YunxiNeural")
TTS_VOICE_EN = os.getenv("TTS_VOICE_EN", "en-US-AndrewNeural")
TTS_RATE = os.getenv("TTS_RATE", "+8%")   # a touch faster for podcast feel

# --- Feed metadata -------------------------------------------------------
# Set FEED_BASE_URL to where `public/` is served (e.g. GitHub Pages URL),
# otherwise audio links in the RSS will be relative and most podcast apps
# won't be able to download them.
FEED_BASE_URL = os.getenv("FEED_BASE_URL", "").rstrip("/")
FEED_TITLE = os.getenv("FEED_TITLE", "我的论文电台 · Paper Library Radio")
FEED_DESC = os.getenv(
    "FEED_DESC",
    "每日 HuggingFace Daily Papers 的中文/英文导读，开车也能听。",
)
FEED_AUTHOR = os.getenv("FEED_AUTHOR", "Paper Library")
