"""Maintenance pass over EVERY episode in the manifest: re-clean the saved
script (Markdown out), re-hash (script + TTS voice/rate/volume) and
re-synthesize any episode whose audio filename no longer matches or whose
audio fails the duration check (truncated tail).

Free to run — only edge-tts is invoked, never the LLM (scripts are reused).
Idempotent: once everything matches, it's a no-op. Episodes keep their feed
position (add_episode preserves `published`), but get a new URL+GUID so
podcast apps re-fetch the fixed audio automatically.

Usage:  python scripts/resynth.py
"""
from __future__ import annotations

from slugify import slugify

import build_feed
import config
import lib
import run_daily


def main() -> None:
    episodes = build_feed.load_manifest()
    done = skipped = 0
    for ep in episodes:
        slug = slugify(ep["title"])[:60] or slugify(ep.get("key") or "paper")
        base = f"{ep['date']}-{slug}"
        if not (config.SCRIPTS_DIR / f"{base}.txt").exists():
            print(f"[resynth] no script for {base} — leaving as is")
            skipped += 1
            continue
        paper = {
            "date": ep["date"],
            "arxiv_id": ep.get("key"),
            "title": ep["title"],
            "abstract": ep.get("abstract", ""),
            "url": ep.get("url", ""),
            "upvotes": ep.get("upvotes", 0),
        }
        ok = run_daily.process_paper(paper, label="resynth: ")
        done += ok
        skipped += not ok
    build_feed.build_all()
    lib.build_library()
    import stt_check
    stt_check.prune({p.name for p in config.AUDIO_DIR.glob("*.mp3")})
    print(f"\n[resynth] done. up to date: {done}, skipped: {skipped}")


if __name__ == "__main__":
    main()
