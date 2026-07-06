"""Ingest a CURATED list of papers (data/curated/reading.json) — not from HF
Daily — and run them through the full pipeline (digest -> hashed audio -> feed
-> card), then apply their tags + a one-time note.

Resumable: papers whose script already exists are reused; papers whose LLM
generation fails (e.g. 429) are skipped and picked up on the next run.

Usage:  python scripts/add_papers.py [path/to/list.json]
"""
from __future__ import annotations

import json
import sys

import build_feed
import config
import fetch_arxiv
import lib
import run_daily

CURATED = config.DATA / "curated"
LIST = CURATED / "reading.json"
# Persisted here so lib.build_library() makes a card for every paper, even ones
# whose audio generation hasn't succeeded yet.
PAPERS_OUT = config.PAPERS_DIR / "curated.json"


def _paper_from_entry(entry: dict, meta: dict) -> tuple[dict, str | None]:
    """Return (paper_dict, full_text_override). arXiv papers fetch full text
    later (override=None); non-arXiv papers supply their abstract as the text."""
    if entry.get("arxiv_id"):
        return meta.get(entry["arxiv_id"]), None
    paper = {
        "date": entry.get("date", "2020-01-01"),
        "arxiv_id": entry["id"],          # synthetic stable id (card filename/key)
        "title": entry["title"],
        "abstract": entry.get("abstract", ""),
        "upvotes": 0,
        "url": entry.get("url", ""),
        "pdf": entry.get("pdf", ""),
        "hf_url": "",
    }
    return paper, (entry.get("fulltext") or entry.get("abstract") or "")


def main(list_path=LIST):
    entries = json.loads(open(list_path, encoding="utf-8").read())
    meta = fetch_arxiv.fetch_many([e["arxiv_id"] for e in entries if e.get("arxiv_id")])

    plan, papers = [], []
    for e in entries:
        paper, full_text = _paper_from_entry(e, meta)
        if not paper:
            print(f"[add] no metadata for {e.get('arxiv_id')}, skipping")
            continue
        papers.append(paper)
        plan.append((paper, full_text, e.get("tags", []), e.get("note", "")))

    # Persist all papers first so every one gets a (possibly no-audio) card.
    PAPERS_OUT.parent.mkdir(parents=True, exist_ok=True)
    PAPERS_OUT.write_text(json.dumps(papers, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[add] {len(papers)} curated papers -> {PAPERS_OUT.name}")

    done = skipped = 0
    for paper, full_text, _tags, _note in plan:
        ok = run_daily.process_paper(paper, full_text=full_text)
        done += ok
        skipped += (not ok)

    build_feed.build_all()
    lib.build_library()

    # Apply tags + the curated note to each card (idempotent).
    for paper, _ft, tags, note in plan:
        cid = paper["arxiv_id"]
        if (lib.CARDS / f"{cid}.md").exists():
            if tags:
                cur = set(lib.parse_card((lib.CARDS / f"{cid}.md").read_text("utf-8"))[0].get("tags") or [])
                lib._edit_meta(cid, tags=sorted(cur | set(tags)))
            lib.note_once(cid, note)
    lib.write_index()
    print(f"\n[add] done. audio published: {done}, skipped (retry next run): {skipped}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else LIST)
