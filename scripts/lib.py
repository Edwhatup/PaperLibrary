#!/usr/bin/env python3
"""Lightweight, git-native paper library — operated by Claude Code or by hand.

The library lives entirely in the repo:
  library/index.jsonl       one compact line per paper (the fast lookup table)
  library/papers/<id>.md     one card per paper: meta + digest links + your
                             notes / Q&A (user sections are NEVER overwritten
                             by `build`)

Quizzing ("test if I understood") is a Claude Code skill (.claude/skills/quiz-me)
and is intentionally NOT persisted here.

Commands (run `python scripts/lib.py -h`):
  build                       (re)generate cards + index from data/ (idempotent;
                              preserves tags/status/notes/Q&A/quiz)
  index                       rebuild index.jsonl from the cards' frontmatter
  search QUERY                grep the index (id/title/summary/tags)
  list [--unread ...]         filter the index by status/tag
  show ID                     print a card's path (open it to read)
  read/unread ID              mark read status
  listened/unlistened ID      mark listened status
  tag ID TAG...               add tags
  untag ID TAG...             remove tags
  note ID "text"              append a dated note
  qa ID -q "..." -a "..."     append a dated Q&A entry

Frontmatter values are JSON-encoded (valid YAML), so they parse unambiguously
with the stdlib — no extra dependencies beyond python-slugify (already used).
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from slugify import slugify

ROOT = Path(__file__).resolve().parent.parent
PAPERS_DATA = ROOT / "data" / "papers"
SCRIPTS_DATA = ROOT / "data" / "scripts"
AUDIO_DIR = ROOT / "public" / "audio"
LIB = ROOT / "library"
CARDS = LIB / "papers"
INDEX = LIB / "index.jsonl"

USER_SECTIONS = ["笔记", "问答记录"]
_FIRST_USER_HEADER = f"## {USER_SECTIONS[0]}"


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# --- frontmatter (JSON-encoded values = valid YAML, stdlib-parseable) -------
def parse_card(text: str) -> tuple[dict, str]:
    """Return (frontmatter dict, user_tail) for an existing card."""
    meta: dict = {}
    tail = ""
    if text.startswith("---"):
        _, fm, body = text.split("---", 2)
        for line in fm.strip().splitlines():
            if ":" not in line:
                continue
            k, _, v = line.partition(":")
            v = v.strip()
            try:
                meta[k.strip()] = json.loads(v)
            except Exception:
                meta[k.strip()] = v
        i = body.find(_FIRST_USER_HEADER)
        tail = body[i:] if i != -1 else ""
    return meta, tail


def _dump_fm(meta: dict) -> str:
    order = ["id", "title", "date", "arxiv", "pdf", "upvotes", "audio",
             "digest", "tags", "listened", "read"]
    keys = order + [k for k in meta if k not in order]
    lines = [f"{k}: {json.dumps(meta[k], ensure_ascii=False)}"
             for k in keys if k in meta]
    return "---\n" + "\n".join(lines) + "\n---\n"


def _empty_tail() -> str:
    return "\n".join(f"## {s}\n" for s in USER_SECTIONS) + "\n"


def render_card(meta: dict, abstract: str, summary: str, tail: str) -> str:
    audio = meta.get("audio")
    digest = meta.get("digest")
    refs = []
    if digest:
        refs.append(f"**导读全文:** `{digest}`")
    if audio:
        refs.append(f"**音频:** `{audio}`")
    refs.append(f"**arXiv:** {meta.get('arxiv','')}")
    head = (
        _dump_fm(meta)
        + f"\n# {meta['title']}\n\n"
        + (f"> {summary}\n\n" if summary else "")
        + (f"**摘要 (EN):** {abstract}\n\n" if abstract else "")
        + "　".join(refs) + "\n\n---\n"
    )
    return head + (tail if tail.strip() else _empty_tail())


# --- build from data/ -------------------------------------------------------
def _collect_papers() -> list[dict]:
    seen: dict[str, dict] = {}
    for f in sorted(glob.glob(str(PAPERS_DATA / "*.json"))):
        for p in json.load(open(f, encoding="utf-8")):
            aid = p.get("arxiv_id")
            if aid and aid not in seen:
                seen[aid] = p
    papers = list(seen.values())
    papers.sort(key=lambda p: (p.get("date", ""), p.get("upvotes", 0)), reverse=True)
    return papers


def _assets(paper: dict) -> tuple[str | None, str | None]:
    """Return (digest_path, audio_path) relative to repo root, if present.
    Audio carries a content hash in the name, so match by prefix."""
    base = f"{paper['date']}-{slugify(paper['title'])[:60]}"
    d = SCRIPTS_DATA / f"{base}.txt"
    auds = sorted(AUDIO_DIR.glob(f"{base}*.mp3"))
    return (str(d.relative_to(ROOT)) if d.exists() else None,
            str(auds[0].relative_to(ROOT)) if auds else None)


def _summary(paper: dict, digest_path: str | None) -> str:
    if digest_path:
        txt = (ROOT / digest_path).read_text(encoding="utf-8")
        first = next((l.strip() for l in txt.splitlines() if l.strip()), "")
        if first:
            return first[:120]
    return (paper.get("abstract", "") or "")[:120]


def build_library() -> int:
    CARDS.mkdir(parents=True, exist_ok=True)
    papers = _collect_papers()
    for paper in papers:
        aid = paper["arxiv_id"]
        path = CARDS / f"{aid}.md"
        digest, audio = _assets(paper)
        # Preserve user-owned frontmatter + sections across rebuilds.
        tail = ""
        prev: dict = {}
        if path.exists():
            prev, tail = parse_card(path.read_text(encoding="utf-8"))
        meta = {
            "id": aid,
            "title": paper["title"],
            "date": paper["date"],
            "arxiv": paper.get("url", ""),
            "pdf": paper.get("pdf", ""),
            "upvotes": paper.get("upvotes", 0),
            "audio": audio,
            "digest": digest,
            "tags": prev.get("tags", []),
            "listened": prev.get("listened", False),
            "read": prev.get("read", False),
        }
        summary = _summary(paper, digest)
        path.write_text(
            render_card(meta, paper.get("abstract", ""), summary, tail),
            encoding="utf-8",
        )
    n = write_index()
    print(f"[lib] {len(papers)} cards -> {CARDS}/  | index: {n} rows")
    return len(papers)


# --- index ------------------------------------------------------------------
def write_index() -> int:
    rows = []
    for path in CARDS.glob("*.md"):
        meta, _ = parse_card(path.read_text(encoding="utf-8"))
        if not meta:
            continue
        rows.append({
            "id": meta.get("id"),
            "title": meta.get("title", ""),
            "date": meta.get("date", ""),
            "tags": meta.get("tags", []),
            "listened": meta.get("listened", False),
            "read": meta.get("read", False),
            "audio": bool(meta.get("audio")),
            "summary": _index_summary(path, meta),
        })
    rows.sort(key=lambda r: r.get("date", ""), reverse=True)
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows)


def _index_summary(path: Path, meta: dict) -> str:
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("> "):
            return line[2:].strip()
    return ""


def load_index() -> list[dict]:
    if not INDEX.exists():
        return []
    return [json.loads(l) for l in INDEX.read_text(encoding="utf-8").splitlines() if l.strip()]


# --- card edits -------------------------------------------------------------
def _card_path(aid: str) -> Path:
    p = CARDS / f"{aid}.md"
    if not p.exists():
        sys.exit(f"no card for id '{aid}' (run: python scripts/lib.py build)")
    return p


def _edit_meta(aid: str, **changes) -> dict:
    path = _card_path(aid)
    meta, tail = parse_card(path.read_text(encoding="utf-8"))
    meta.update(changes)
    # Re-render keeping abstract: pull it back out of the existing body.
    text = path.read_text(encoding="utf-8")
    abstract = ""
    for line in text.splitlines():
        if line.startswith("**摘要 (EN):**"):
            abstract = line.split("**", 2)[-1].strip()
            break
    summary = _index_summary(path, meta)
    path.write_text(render_card(meta, abstract, summary, tail), encoding="utf-8")
    write_index()
    return meta


def note_once(aid: str, text: str) -> None:
    """Append a note only if that exact text isn't already in the card
    (idempotent — safe to call on every re-run)."""
    text = (text or "").strip()
    if not text:
        return
    path = CARDS / f"{aid}.md"
    if not path.exists() or text in path.read_text(encoding="utf-8"):
        return
    _append_section(aid, "笔记", f"- {text}")


def _append_section(aid: str, section: str, block: str) -> None:
    path = _card_path(aid)
    text = path.read_text(encoding="utf-8")
    header = f"## {section}"
    idx = text.find(header)
    if idx == -1:
        sys.exit(f"section '{section}' not found in card")
    nxt = text.find("\n## ", idx + len(header))
    insert_at = nxt if nxt != -1 else len(text)
    new = text[:insert_at].rstrip() + "\n" + block.rstrip() + "\n\n" + text[insert_at:].lstrip("\n")
    path.write_text(new if new.endswith("\n") else new + "\n", encoding="utf-8")


# --- CLI --------------------------------------------------------------------
def _print_row(r: dict) -> None:
    flags = ("L" if r["listened"] else "-") + ("R" if r["read"] else "-")
    tags = ",".join(r.get("tags") or [])
    print(f"{r['id']:<14} [{flags}] {r['date']}  {r['title'][:60]}"
          + (f"  #{tags}" if tags else ""))


def cmd_search(args):
    q = args.query.lower()
    for r in load_index():
        hay = f"{r['id']} {r['title']} {r.get('summary','')} {' '.join(r.get('tags') or [])}".lower()
        if q in hay:
            _print_row(r)


def cmd_list(args):
    for r in load_index():
        if args.unread and r["read"]:
            continue
        if args.unlistened and r["listened"]:
            continue
        if args.tag and args.tag not in (r.get("tags") or []):
            continue
        _print_row(r)


def cmd_show(args):
    print(_card_path(args.id))


def cmd_status(args, **changes):
    m = _edit_meta(args.id, **changes)
    print(f"{args.id}: listened={m['listened']} read={m['read']}")


def cmd_tag(args):
    path = _card_path(args.id)
    meta, _ = parse_card(path.read_text(encoding="utf-8"))
    tags = set(meta.get("tags") or [])
    if args.remove:
        tags -= set(args.tags)
    else:
        tags |= set(args.tags)
    _edit_meta(args.id, tags=sorted(tags))
    print(f"{args.id}: tags={sorted(tags)}")


def cmd_note(args):
    _append_section(args.id, "笔记", f"- ({_today()}) {args.text}")
    print(f"{args.id}: note added")


def cmd_qa(args):
    _append_section(args.id, "问答记录",
                    f"- **Q** ({_today()}): {args.q}\n  **A:** {args.a}")
    print(f"{args.id}: Q&A logged")


def main():
    ap = argparse.ArgumentParser(description="git-native paper library")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("build").set_defaults(func=lambda a: build_library())
    sub.add_parser("index").set_defaults(func=lambda a: write_index())

    s = sub.add_parser("search"); s.add_argument("query"); s.set_defaults(func=cmd_search)
    s = sub.add_parser("list")
    s.add_argument("--unread", action="store_true")
    s.add_argument("--unlistened", action="store_true")
    s.add_argument("--tag")
    s.set_defaults(func=cmd_list)
    s = sub.add_parser("show"); s.add_argument("id"); s.set_defaults(func=cmd_show)

    for name, kw in [("read", {"read": True}), ("unread", {"read": False}),
                     ("listened", {"listened": True}), ("unlistened", {"listened": False})]:
        s = sub.add_parser(name); s.add_argument("id")
        s.set_defaults(func=lambda a, kw=kw: cmd_status(a, **kw))

    s = sub.add_parser("tag"); s.add_argument("id"); s.add_argument("tags", nargs="+")
    s.add_argument("--remove", action="store_true"); s.set_defaults(func=cmd_tag)
    s = sub.add_parser("untag"); s.add_argument("id"); s.add_argument("tags", nargs="+")
    s.set_defaults(func=lambda a: cmd_tag(argparse.Namespace(id=a.id, tags=a.tags, remove=True)))

    s = sub.add_parser("note"); s.add_argument("id"); s.add_argument("text"); s.set_defaults(func=cmd_note)
    s = sub.add_parser("qa"); s.add_argument("id")
    s.add_argument("-q", required=True); s.add_argument("-a", required=True); s.set_defaults(func=cmd_qa)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
