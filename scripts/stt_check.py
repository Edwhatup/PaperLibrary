"""STT gate: an episode may only ship if speech-to-text of the audio's tail
actually contains the script's ending — catching dropped endings that a
duration estimate alone can miss.

How it works
  1. faster-whisper (free, local CPU) transcribes only the LAST ~30s of the
     mp3 (clip_timestamps), so a check costs seconds, not minutes.
  2. Whisper often emits Traditional Chinese; both sides are normalized via
     OpenCC t2s + stripped to CJK/alnum before comparison.
  3. The script's final sentence(s) must appear in the transcript: character-
     bigram coverage >= STT_MIN_COVERAGE. Bigrams tolerate scattered STT
     substitutions but drop to ~0 when the ending is genuinely missing.

Verified files are recorded in data/audio_checks.json keyed by audio filename
(filenames are content-hashed, so a pass never needs re-checking).
"""
from __future__ import annotations

import difflib
import json
import re

import config

CHECKS_PATH = config.DATA / "audio_checks.json"

_model = None
_t2s = None


def _load_checks() -> dict:
    if CHECKS_PATH.exists():
        return json.loads(CHECKS_PATH.read_text(encoding="utf-8"))
    return {}


def verified(audio_name: str) -> bool:
    return _load_checks().get(audio_name) == "tail_ok"


def mark_ok(audio_name: str) -> None:
    checks = _load_checks()
    checks[audio_name] = "tail_ok"
    CHECKS_PATH.write_text(
        json.dumps(checks, ensure_ascii=False, indent=0, sort_keys=True),
        encoding="utf-8",
    )


def prune(valid_names: set[str]) -> None:
    """Drop cache entries for audio files that no longer exist."""
    checks = _load_checks()
    kept = {k: v for k, v in checks.items() if k in valid_names}
    if kept != checks:
        CHECKS_PATH.write_text(
            json.dumps(kept, ensure_ascii=False, indent=0, sort_keys=True),
            encoding="utf-8",
        )


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(config.STT_MODEL, device="cpu", compute_type="int8")
    return _model


def _norm(text: str) -> str:
    """Simplified Chinese + lowercase, CJK/alnum only (drop punct/space)."""
    global _t2s
    if _t2s is None:
        from opencc import OpenCC
        _t2s = OpenCC("t2s")
    text = _t2s.convert(text)
    return re.sub(r"[^0-9a-z一-鿿]+", "", text.lower())


def _script_ending(script: str, min_chars: int = 16) -> str:
    """The script's final sentence, extended backwards until >= min_chars."""
    parts = [p for p in re.split(r"(?<=[。！？.!?])", script.strip()) if p.strip()]
    tail = ""
    while parts and len(_norm(tail)) < min_chars:
        tail = parts.pop() + tail
    return _norm(tail)


def _bigram_coverage(want: str, heard: str) -> float:
    if len(want) < 2:
        return 1.0 if want in heard else 0.0
    grams = {want[i:i + 2] for i in range(len(want) - 1)}
    hgrams = {heard[i:i + 2] for i in range(len(heard) - 1)}
    return len(grams & hgrams) / len(grams)


def transcribe_tail(path, tail_seconds: float | None = None) -> str:
    tail_seconds = tail_seconds or config.STT_TAIL_SECONDS
    duration = path.stat().st_size * 8 / 48000  # edge-tts mp3 ~48kbps
    start = max(0.0, duration - tail_seconds)
    lang = "zh" if config.DIGEST_LANG == "zh" else "en"
    segments, _info = _get_model().transcribe(
        str(path),
        language=lang,
        clip_timestamps=[start],
        initial_prompt="以下是简体中文普通话的句子。" if lang == "zh" else None,
    )
    return "".join(seg.text for seg in segments)


def tail_matches(script: str, path) -> bool:
    """True if the script's ending is audibly present at the end of the audio."""
    want = _script_ending(script)
    if not want:
        return True
    heard = _norm(transcribe_tail(path))
    if not heard:
        print("[stt] transcript of tail is EMPTY")
        return False
    if want in heard:
        return True
    cov = _bigram_coverage(want, heard)
    ok = cov >= config.STT_MIN_COVERAGE
    if not ok:
        ratio = difflib.SequenceMatcher(a=want, b=heard[-len(want) * 3:]).ratio()
        print(f"[stt] ending NOT heard (coverage {cov:.2f}, ratio {ratio:.2f})\n"
              f"      want …{want[-40:]!r}\n      heard …{heard[-60:]!r}")
    return ok


def check_and_record(script: str, path) -> bool:
    """Cached wrapper: verify once per (content-hashed) audio filename."""
    if verified(path.name):
        return True
    if tail_matches(script, path):
        mark_ok(path.name)
        return True
    return False
