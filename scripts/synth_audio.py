"""Synthesize narration text into an MP3 with edge-tts (free, no API key).

Includes a duration sanity check: edge-tts occasionally drops the tail of a
long text (the stream ends early but still writes a valid mp3), which is heard
as the narration cutting off mid-sentence. We estimate how long the audio
SHOULD be from the text and retry/fail if the file comes up short.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

import edge_tts

import config


def _voice() -> str:
    return config.TTS_VOICE_ZH if config.DIGEST_LANG == "zh" else config.TTS_VOICE_EN


def signature() -> str:
    """Identifies the TTS settings that shape the audio. Hashed into the audio
    filename so a voice/rate/volume change republishes every episode with a
    new URL+GUID (podcast apps re-fetch without re-subscribing)."""
    return f"{_voice()}|{config.TTS_RATE}|{config.TTS_VOLUME}"


def expected_seconds(text: str) -> float:
    """Rough narration length: CJK chars at CHARS_PER_MIN, latin words ~170/min."""
    cjk = sum(1 for c in text if "一" <= c <= "鿿")
    words = len(re.findall(r"[A-Za-z0-9]+", text))
    return cjk / config.CHARS_PER_MIN * 60 + words / 170 * 60


def duration_seconds(path: Path) -> float:
    return path.stat().st_size * 8 / 48000  # edge-tts mp3 is ~48kbps


def duration_ok(text: str, path: Path) -> bool:
    """True if the audio is plausibly a full reading of `text` (30% slack for
    estimation error); False = the tail was likely dropped."""
    return duration_seconds(path) >= 0.7 * expected_seconds(text)


async def _synth(text: str, out_path: Path) -> None:
    communicate = edge_tts.Communicate(
        text, _voice(), rate=config.TTS_RATE, volume=config.TTS_VOLUME
    )
    await communicate.save(str(out_path))


def synth(text: str, out_path: Path, attempts: int = 3) -> Path:
    """Synthesize and VERIFY: duration must be plausible AND an STT pass must
    hear the script's ending at the end of the audio. No verified ending ->
    the file is deleted and the episode does not ship."""
    import stt_check  # deferred: keeps edge-tts usable without whisper installed

    out_path.parent.mkdir(parents=True, exist_ok=True)
    want = expected_seconds(text)
    for i in range(1, attempts + 1):
        asyncio.run(_synth(text, out_path))
        got = duration_seconds(out_path)
        if not duration_ok(text, out_path):
            print(f"[tts] WARNING: audio too short (~{got/60:.1f}min, expected "
                  f"~{want/60:.1f}min) — tail dropped? attempt {i}/{attempts}")
            out_path.unlink(missing_ok=True)
            continue
        if not stt_check.check_and_record(text, out_path):
            print(f"[tts] WARNING: STT did not hear the script's ending — "
                  f"attempt {i}/{attempts}")
            out_path.unlink(missing_ok=True)
            continue
        print(f"[tts] {out_path}  ({out_path.stat().st_size // 1024} KB, "
              f"~{got/60:.1f}min / expected ~{want/60:.1f}min, ending verified)")
        return out_path
    raise RuntimeError(
        f"TTS kept truncating (duration/STT check failed) for {out_path.name}"
    )


if __name__ == "__main__":
    synth("这是一个测试。Hello world.", config.AUDIO_DIR / "_test.mp3")
