"""Synthesize narration text into an MP3 with edge-tts (free, no API key)."""
from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts

import config


def _voice() -> str:
    return config.TTS_VOICE_ZH if config.DIGEST_LANG == "zh" else config.TTS_VOICE_EN


async def _synth(text: str, out_path: Path) -> None:
    communicate = edge_tts.Communicate(text, _voice(), rate=config.TTS_RATE)
    await communicate.save(str(out_path))


def synth(text: str, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_synth(text, out_path))
    print(f"[tts] {out_path}  ({out_path.stat().st_size // 1024} KB)")
    return out_path


if __name__ == "__main__":
    synth("这是一个测试。Hello world.", config.AUDIO_DIR / "_test.mp3")
