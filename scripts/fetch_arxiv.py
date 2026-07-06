"""Fetch paper metadata from the arXiv API by id, for curated (non-HF) papers.

Returns dicts in the same shape as fetch_papers, so the rest of the pipeline
(script -> audio -> feed -> card) works unchanged.
"""
from __future__ import annotations

import time
import xml.etree.ElementTree as ET

import requests

API = "https://export.arxiv.org/api/query"
ATOM = "{http://www.w3.org/2005/Atom}"


def _norm_id(raw: str) -> str:
    raw = raw.strip()
    for p in ("arxiv:", "arXiv:", "https://arxiv.org/abs/", "http://arxiv.org/abs/"):
        if raw.lower().startswith(p.lower()):
            raw = raw[len(p):]
    return raw.split("v")[0] if raw and raw[-1].isdigit() and "v" in raw.split("/")[-1] else raw


def fetch_many(ids: list[str]) -> dict[str, dict]:
    """Map arxiv_id -> metadata dict for the given ids (best effort)."""
    ids = [_norm_id(i) for i in ids if i]
    out: dict[str, dict] = {}
    if not ids:
        return out
    r = requests.get(API, params={"id_list": ",".join(ids), "max_results": len(ids)},
                     timeout=40, headers={"User-Agent": "paper-library/1.0"})
    r.raise_for_status()
    root = ET.fromstring(r.text)
    for e in root.findall(f"{ATOM}entry"):
        idurl = (e.findtext(f"{ATOM}id") or "").strip()
        aid = _norm_id(idurl)
        title = " ".join((e.findtext(f"{ATOM}title") or "").split())
        summary = " ".join((e.findtext(f"{ATOM}summary") or "").split())
        published = (e.findtext(f"{ATOM}published") or "")[:10] or "2020-01-01"
        if not aid or not title:
            continue
        out[aid] = {
            "date": published,
            "arxiv_id": aid,
            "title": title,
            "abstract": summary,
            "upvotes": 0,
            "url": f"https://arxiv.org/abs/{aid}",
            "pdf": f"https://arxiv.org/pdf/{aid}",
            "hf_url": "",
        }
    return out


def fetch_one(arxiv_id: str, retries: int = 3) -> dict | None:
    for i in range(retries):
        try:
            got = fetch_many([arxiv_id])
            if got:
                return next(iter(got.values()))
        except Exception as e:
            print(f"[arxiv] {arxiv_id} attempt {i+1} failed: {e}")
        time.sleep(3 * (i + 1))
    return None


if __name__ == "__main__":
    import sys
    ids = sys.argv[1:] or ["2310.06770", "2306.00107"]
    for aid, m in fetch_many(ids).items():
        print(f"{aid}  {m['date']}  {m['title'][:70]}")
