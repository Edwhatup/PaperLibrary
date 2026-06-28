"""Fetch HuggingFace Daily Papers for a given date.

HF exposes a public JSON API:
    https://huggingface.co/api/daily_papers?date=YYYY-MM-DD

Each entry carries the paper title, abstract, arXiv id and up-votes.
We persist the raw list and return a normalized, up-vote-sorted slice.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone

import requests

import config

API = "https://huggingface.co/api/daily_papers"


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def fetch(date_str: str | None = None) -> list[dict]:
    date_str = date_str or _today()
    resp = requests.get(API, params={"date": date_str}, timeout=30)
    resp.raise_for_status()
    raw = resp.json()

    papers = []
    for item in raw:
        p = item.get("paper", item)
        arxiv_id = p.get("id") or p.get("arxiv_id") or ""
        papers.append(
            {
                "date": date_str,
                "arxiv_id": arxiv_id,
                "title": (p.get("title") or "").strip(),
                "abstract": (p.get("summary") or p.get("abstract") or "").strip(),
                "upvotes": p.get("upvotes", item.get("upvotes", 0)) or 0,
                "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "",
                "pdf": f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else "",
                "hf_url": f"https://huggingface.co/papers/{arxiv_id}" if arxiv_id else "",
            }
        )

    papers.sort(key=lambda x: x["upvotes"], reverse=True)

    out = config.PAPERS_DIR / f"{date_str}.json"
    out.write_text(json.dumps(papers, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[fetch] {date_str}: {len(papers)} papers -> {out}")
    return papers[: config.MAX_PAPERS]


if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else None
    got = fetch(d)
    for i, p in enumerate(got, 1):
        print(f"  {i}. [{p['upvotes']}★] {p['title']}  ({p['arxiv_id']})")
