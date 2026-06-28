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
import fetch_fulltext
import fetch_papers
import lib
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
            mins = make_script.target_minutes(paper)
            tag = "相关·长" if make_script.is_relevant(paper) else "概览·短"
            print(f"[script] {tag} target≈{mins}min")
            full_text = fetch_fulltext.fetch_fulltext(paper["arxiv_id"])
            script = make_script.make_script(paper, full_text)
            script_path.write_text(script, encoding="utf-8")

        audio_name = f"{base}.mp3"
        audio_path = config.AUDIO_DIR / audio_name
        if audio_path.exists():
            print(f"[tts] reuse {audio_name}")
        else:
            synth_audio.synth(script, audio_path)

        # Chinese show-notes = first paragraph of the script (the podcast app
        # shows this); fall back to the English abstract.
        notes = next((p.strip() for p in script.split("\n") if p.strip()), "")[:300]

        build_feed.add_episode(
            {
                "date": paper["date"],
                "title": paper["title"],
                "abstract": paper["abstract"],
                "notes": notes,
                "url": paper["url"],
                "upvotes": paper["upvotes"],
                "audio": audio_name,
                "size": audio_path.stat().st_size,
                "published": datetime.now(timezone.utc).isoformat(),
            }
        )

    build_feed.build_all()
    lib.build_library()  # refresh paper cards + index (preserves notes/status)
    print("\n[run] done.")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else None)
