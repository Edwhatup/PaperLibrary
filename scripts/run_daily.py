"""End-to-end daily run:

    fetch HF daily papers
      -> generate a 导读 script per paper
        -> synthesize MP3 with edge-tts
          -> record episode + rebuild RSS feed and library index

Usage:
    python scripts/run_daily.py [YYYY-MM-DD]
"""
from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone

from slugify import slugify

import build_feed
import build_site
import config
import fetch_fulltext
import fetch_papers
import lib
import make_script
import synth_audio


def process_paper(paper: dict, label: str = "", full_text: str | None = None) -> bool:
    """Build one episode (script -> hashed audio -> feed entry). Returns True if
    published, False if skipped (LLM failure). `full_text=None` fetches from
    arXiv; pass a string to supply text for non-arXiv papers."""
    print(f"\n=== {label}{paper['title']} ===")
    slug = slugify(paper["title"])[:60] or slugify(paper.get("arxiv_id", "paper"))
    base = f"{paper['date']}-{slug}"
    script_path = config.SCRIPTS_DIR / f"{base}.txt"

    # A hand-written / previously generated script wins (idempotent re-runs).
    # Reused scripts still get de-markdown'd (older ones contain ** etc. that
    # TTS reads aloud); the file is rewritten so the card's digest is clean too.
    if script_path.exists():
        raw = script_path.read_text(encoding="utf-8")
        script = make_script.clean_for_tts(raw)
        if script != raw.strip():
            script_path.write_text(script, encoding="utf-8")
            print(f"[script] reuse {script_path.name} (cleaned markdown)")
        else:
            print(f"[script] reuse {script_path.name}")
    else:
        mins = make_script.target_minutes(paper)
        tag = "相关·长" if make_script.is_relevant(paper) else "概览·短"
        print(f"[script] {tag} target≈{mins}min")
        if full_text is None:
            full_text = fetch_fulltext.fetch_fulltext(paper["arxiv_id"])
        script = make_script.make_script(paper, full_text)
        if not script:
            print(f"[run] SKIP — no script for {paper.get('arxiv_id') or base}")
            return False
        script_path.write_text(script, encoding="utf-8")

    # Hash covers the script AND the TTS settings, so changing either yields a
    # NEW url + guid -> podcast apps auto-fetch it without re-subscribing.
    h = hashlib.sha1(f"{script}|{synth_audio.signature()}".encode("utf-8")).hexdigest()[:8]
    audio_name = f"{base}-{h}.mp3"
    audio_path = config.AUDIO_DIR / audio_name
    for stale in config.AUDIO_DIR.glob(f"{base}*.mp3"):
        if stale.name != audio_name:
            stale.unlink()
    # Guard against a previously truncated synthesis: plausible duration AND
    # an STT pass must hear the script's ending (cached per hashed filename).
    if audio_path.exists():
        import stt_check
        if not synth_audio.duration_ok(script, audio_path):
            print("[tts] existing audio fails duration check — re-synthesizing")
            audio_path.unlink()
        elif not stt_check.check_and_record(script, audio_path):
            print("[tts] existing audio fails STT ending check — re-synthesizing")
            audio_path.unlink()
    if audio_path.exists():
        print(f"[tts] reuse {audio_name}")
    else:
        try:
            synth_audio.synth(script, audio_path)
        except Exception as e:
            print(f"[tts] FAILED ({str(e)[:120]}) — skipping, retry next run")
            audio_path.unlink(missing_ok=True)
            return False

    notes = next((p.strip() for p in script.split("\n") if p.strip()), "")[:300]
    build_feed.add_episode({
        "key": paper.get("arxiv_id") or base,
        "date": paper["date"],
        "title": paper["title"],
        "abstract": paper["abstract"],
        "notes": notes,
        "url": paper["url"],
        "upvotes": paper.get("upvotes", 0),
        "audio": audio_name,
        "size": audio_path.stat().st_size,
        "published": datetime.now(timezone.utc).isoformat(),
    })
    return True


def run(date_str: str | None = None) -> None:
    papers = fetch_papers.fetch(date_str)
    if not papers:
        print("[run] no papers for this date; nothing to do.")
        return
    for i, paper in enumerate(papers, 1):
        process_paper(paper, label=f"{i}/{len(papers)}: ")
    build_feed.build_all()
    lib.build_library()  # refresh paper cards + index (preserves notes/status)
    build_site.build_site()  # regenerate the static blog into public/
    print("\n[run] done.")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else None)
