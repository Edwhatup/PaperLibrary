"""End-to-end daily run:

    fetch HF daily papers
      -> generate a 导读 script per paper
        -> synthesize MP3 with edge-tts
          -> record episode + rebuild RSS feed and library index

Usage:
    python scripts/run_daily.py [YYYY-MM-DD]
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

from slugify import slugify

import build_feed
import config
import fetch_papers
import make_script
import synth_audio


def run(date_str: str | None = None) -> None:
    papers = fetch_papers.fetch(date_str)
    if not papers:
        print("[run] no papers for this date; nothing to do.")
        return

    for i, paper in enumerate(papers, 1):
        print(f"\n=== {i}/{len(papers)}: {paper['title']} ===")

        slug = slugify(paper["title"])[:60] or f"paper-{i}"
        base = f"{paper['date']}-{slug}"
        script_path = config.SCRIPTS_DIR / f"{base}.txt"

        # A hand-written / previously generated script wins: this lets you
        # commit a polished 导读 and have CI reuse it verbatim (no LLM needed),
        # and makes re-runs of the same date idempotent.
        if script_path.exists():
            script = script_path.read_text(encoding="utf-8")
            print(f"[script] reuse {script_path.name}")
        else:
            script = make_script.make_script(paper)
            script_path.write_text(script, encoding="utf-8")

        audio_name = f"{base}.mp3"
        audio_path = config.AUDIO_DIR / audio_name
        if audio_path.exists():
            print(f"[tts] reuse {audio_name}")
        else:
            synth_audio.synth(script, audio_path)

        build_feed.add_episode(
            {
                "date": paper["date"],
                "title": paper["title"],
                "abstract": paper["abstract"],
                "url": paper["url"],
                "upvotes": paper["upvotes"],
                "audio": audio_name,
                "size": audio_path.stat().st_size,
                "published": datetime.now(timezone.utc).isoformat(),
            }
        )

    build_feed.build_all()
    print("\n[run] done.")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else None)
