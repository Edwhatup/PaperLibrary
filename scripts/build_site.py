#!/usr/bin/env python3
"""Generate a static personal blog into ``public/`` from the paper library.

The blog is *notes-first*: papers where you've written a ``## 笔记`` section
become blog **posts** (your writing, in English — this is what promotes you);
every other paper is part of a browsable **reading list**. The daily audio
digest (电台) is an attached feature, not the headline.

Output (all under ``public/``, alongside the existing ``audio/`` + ``rss.xml``):

  index.html            home: bio/pitch + featured writing + latest reading
  writing.html          every post (cards that have your notes)
  library.html          all papers, client-side search + tag filter
  radio.html            the 电台 — episode list + inline player
  papers/<id>.html      one page per paper (notes on top, then abstract,
                        collapsible Chinese 导读, audio player)
  assets/style.css      dark, minimal theme (single configurable accent)
  assets/app.js         library search/filter
  papers.json           data powering the library search

Config lives in ``data/site.json`` (title, bio, links, accent) — edit it to
make the site yours. Idempotent: safe to run on every build.

Run standalone:  ``python scripts/build_site.py``
It is also invoked at the end of ``run_daily.py`` so the site refreshes daily.
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "library"
CARDS = LIB / "papers"
INDEX = LIB / "index.jsonl"
PUBLIC = ROOT / "public"
SITE_JSON = ROOT / "data" / "site.json"

DEFAULT_SITE = {
    "title": "Paper Notes",
    "tagline": "Reading papers, writing notes.",
    "author": "",
    "bio": "",
    "accent": "#f0803c",
    "links": {},
    "featured_tag": "",
    "footer": "",
}


# --------------------------------------------------------------------------- #
# Tiny, dependency-free Markdown -> HTML (enough for personal notes).
# --------------------------------------------------------------------------- #
_URL_RE = re.compile(r"(?<![\"'=(])\bhttps?://[^\s<>)\]]+")


def _inline(text: str) -> str:
    """Render inline markdown on an ALREADY html-escaped string."""
    # Protect inline code spans first so their contents aren't reformatted.
    spans: list[str] = []

    def _stash(m: "re.Match[str]") -> str:
        spans.append(m.group(1))
        return f"\x00{len(spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", _stash, text)
    # links: [text](url)
    text = re.sub(
        r"\[([^\]]+)\]\((https?://[^\s)]+|mailto:[^\s)]+|[^\s)]+)\)",
        r'<a href="\2">\1</a>',
        text,
    )
    # bare autolinks
    text = _URL_RE.sub(lambda m: f'<a href="{m.group(0)}">{m.group(0)}</a>', text)
    # bold then italic
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", text)
    # restore code spans
    text = re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{spans[int(m.group(1))]}</code>", text)
    return text


def markdown(src: str) -> str:
    """Block-level markdown: headings, lists, blockquotes, code fences, rules."""
    if not src or not src.strip():
        return ""
    lines = src.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    i, n = 0, len(lines)
    para: list[str] = []

    def flush_para() -> None:
        if para:
            out.append("<p>" + _inline(" ".join(para).strip()) + "</p>")
            para.clear()

    while i < n:
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):  # fenced code
            flush_para()
            i += 1
            buf: list[str] = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>" + html.escape("\n".join(buf)) + "</code></pre>")
            continue

        if not stripped:  # blank -> paragraph break
            flush_para()
            i += 1
            continue

        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):  # hr
            flush_para()
            out.append("<hr>")
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)  # heading
        if m:
            flush_para()
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{_inline(html.escape(m.group(2).strip()))}</h{lvl}>")
            i += 1
            continue

        if re.match(r"^([-*+])\s+", stripped):  # unordered list
            flush_para()
            items: list[str] = []
            while i < n and re.match(r"^\s*([-*+])\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*+]\s+", "", lines[i]).rstrip())
                i += 1
            out.append("<ul>" + "".join(f"<li>{_inline(html.escape(x))}</li>" for x in items) + "</ul>")
            continue

        if re.match(r"^\d+[.)]\s+", stripped):  # ordered list
            flush_para()
            items = []
            while i < n and re.match(r"^\s*\d+[.)]\s+", lines[i]):
                items.append(re.sub(r"^\s*\d+[.)]\s+", "", lines[i]).rstrip())
                i += 1
            out.append("<ol>" + "".join(f"<li>{_inline(html.escape(x))}</li>" for x in items) + "</ol>")
            continue

        if stripped.startswith(">"):  # blockquote
            flush_para()
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append("<blockquote>" + markdown("\n".join(buf)) + "</blockquote>")
            continue

        para.append(html.escape(stripped))
        i += 1

    flush_para()
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Card parsing
# --------------------------------------------------------------------------- #
def _frontmatter(text: str) -> tuple[dict, str]:
    meta: dict = {}
    if not text.startswith("---"):
        return meta, text
    _, fm, body = text.split("---", 2)
    for line in fm.strip().splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        try:
            meta[k.strip()] = json.loads(v.strip())
        except Exception:
            meta[k.strip()] = v.strip()
    return meta, body


def _section(body: str, header: str, stops: list[str]) -> str:
    i = body.find(header)
    if i == -1:
        return ""
    seg = body[i + len(header):]
    end = len(seg)
    for s in stops:
        j = seg.find(s)
        if j != -1:
            end = min(end, j)
    return seg[:end].strip()


def _abstract(body: str) -> str:
    m = re.search(r"\*\*摘要 \(EN\):\*\*\s*(.+)", body)
    return m.group(1).strip() if m else ""


def _rel_audio(audio: str, depth: int) -> str:
    """Card stores ``public/audio/x.mp3``; make it relative to page depth."""
    if not audio:
        return ""
    name = audio.split("/audio/", 1)[-1] if "/audio/" in audio else audio.split("/")[-1]
    return ("../" * depth) + "audio/" + name


def load_cards() -> list[dict]:
    cards = []
    for path in CARDS.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        meta, body = _frontmatter(text)
        if not meta.get("id"):
            continue
        notes = _section(body, "## 笔记", ["## 问答记录", "## 测验"])
        qa = _section(body, "## 问答记录", ["## 测验", "## 笔记"])
        digest_text = ""
        dp = meta.get("digest")
        if dp:
            f = ROOT / dp
            if f.exists():
                digest_text = f.read_text(encoding="utf-8").strip()
        cards.append({
            "id": meta["id"],
            "title": meta.get("title", meta["id"]),
            "date": meta.get("date", ""),
            "tags": meta.get("tags", []) or [],
            "arxiv": meta.get("arxiv", ""),
            "pdf": meta.get("pdf", ""),
            "audio": meta.get("audio", ""),
            "summary": next((l[2:].strip() for l in body.splitlines() if l.startswith("> ")), ""),
            "abstract": _abstract(body),
            "notes": notes,
            "qa": qa,
            "digest": digest_text,
            "has_notes": bool(notes.strip()),
        })
    cards.sort(key=lambda c: c["date"], reverse=True)
    return cards


# --------------------------------------------------------------------------- #
# HTML helpers
# --------------------------------------------------------------------------- #
def e(s: str) -> str:
    return html.escape(s or "")


def _fmt_date(d: str) -> str:
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%b %d, %Y")
    except Exception:
        return d


def _reading_time(text: str) -> int:
    words = len(re.findall(r"\w+", text))
    return max(1, round(words / 200))


def layout(site: dict, title: str, body: str, depth: int, active: str = "") -> str:
    up = "../" * depth
    nav = [("Home", "index.html"), ("Writing", "writing.html"),
           ("Library", "library.html"), ("电台 Radio", "radio.html")]
    nav_html = "".join(
        '<a href="{u}{h}"{cls}>{l}</a>'.format(
            u=up, h=href, l=e(label),
            cls=' class="active"' if active == href else "")
        for label, href in nav
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<link rel="stylesheet" href="{up}assets/style.css">
<link rel="alternate" type="application/rss+xml" title="Radio" href="{up}rss.xml">
</head>
<body>
<header class="site-head">
  <a class="brand" href="{up}index.html">{e(site["title"])}</a>
  <nav>{nav_html}</nav>
</header>
<main>
{body}
</main>
<footer class="site-foot">
  <span>{e(site.get("footer", ""))}</span>
  <span>© {datetime.now().year} {e(site.get("author") or site["title"])} · <a href="{up}rss.xml">RSS</a></span>
</footer>
</body>
</html>
"""


def post_card_html(c: dict, depth: int) -> str:
    up = "../" * depth
    tags = "".join(f'<span class="tag">{e(t)}</span>' for t in c["tags"][:4])
    excerpt = re.sub(r"\s+", " ", re.sub(r"[#>*`\-]", "", c["notes"]))[:180]
    rt = _reading_time(c["notes"])
    return f"""<article class="post-card">
  <a class="post-card-link" href="{up}papers/{e(c['id'])}.html">
    <div class="post-card-meta"><time>{_fmt_date(c['date'])}</time> · {rt} min read</div>
    <h3>{e(c['title'])}</h3>
    <p>{e(excerpt)}…</p>
    <div class="tags">{tags}</div>
  </a>
</article>"""


def reading_row_html(c: dict, depth: int) -> str:
    up = "../" * depth
    badge = ' <span class="badge">notes</span>' if c["has_notes"] else ""
    audio = ' <span class="badge audio">♪</span>' if c["audio"] else ""
    return f"""<a class="read-row" href="{up}papers/{e(c['id'])}.html">
  <time>{_fmt_date(c['date'])}</time>
  <span class="read-title">{e(c['title'])}{badge}{audio}</span>
</a>"""


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
def page_home(site: dict, cards: list[dict]) -> str:
    posts = [c for c in cards if c["has_notes"]]
    links = " ".join(
        f'<a class="pill" href="{e(url)}">{e(label)}</a>'
        for label, url in site.get("links", {}).items()
    )
    hero = f"""<section class="hero">
  <h1>{e(site['title'])}</h1>
  <p class="tagline">{e(site['tagline'])}</p>
  <div class="bio">{markdown(site.get('bio', ''))}</div>
  <div class="pills">{links}</div>
</section>"""

    featured = posts[:3]
    feat_html = ""
    if featured:
        feat_html = (
            '<section class="section"><div class="section-head"><h2>Featured writing</h2>'
            '<a class="more" href="writing.html">All posts →</a></div>'
            '<div class="post-grid">'
            + "".join(post_card_html(c, 0) for c in featured)
            + "</div></section>"
        )

    rest_posts = posts[3:9]
    rest_html = ""
    if rest_posts:
        rest_html = (
            '<section class="section"><h2>More notes</h2><div class="post-list">'
            + "".join(post_card_html(c, 0) for c in rest_posts)
            + "</div></section>"
        )

    latest = cards[:8]
    latest_html = (
        '<section class="section"><div class="section-head"><h2>From the reading list</h2>'
        '<a class="more" href="library.html">Browse all →</a></div>'
        '<div class="read-list">'
        + "".join(reading_row_html(c, 0) for c in latest)
        + "</div></section>"
    )

    body = hero + feat_html + rest_html + latest_html
    return layout(site, site["title"], body, 0, "index.html")


def page_writing(site: dict, cards: list[dict]) -> str:
    posts = [c for c in cards if c["has_notes"]]
    intro = f'<section class="page-head"><h1>Writing</h1><p>{len(posts)} posts — my notes and takes on papers I\'ve read.</p></section>'
    grid = '<div class="post-list wide">' + "".join(post_card_html(c, 0) for c in posts) + "</div>"
    if not posts:
        grid = '<p class="empty">No notes yet. Add a note with <code>lib.py note &lt;id&gt; "..."</code> and it shows up here.</p>'
    return layout(site, "Writing · " + site["title"], intro + grid, 0, "writing.html")


def page_library(site: dict, cards: list[dict]) -> str:
    all_tags = sorted({t for c in cards for t in c["tags"]})
    tag_opts = "".join(f'<button class="tag-filter" data-tag="{e(t)}">{e(t)}</button>' for t in all_tags)
    data = [{
        "id": c["id"], "title": c["title"], "date": c["date"], "tags": c["tags"],
        "summary": c["summary"], "has_notes": c["has_notes"], "audio": bool(c["audio"]),
    } for c in cards]
    # Inline the data so search works on any host (incl. file://), no fetch.
    data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    body = f"""<section class="page-head">
  <h1>Library</h1><p>{len(cards)} papers. Search titles, summaries and tags.</p>
</section>
<div class="lib-controls">
  <input id="q" type="search" placeholder="Search {len(cards)} papers…" autocomplete="off">
  <div class="tag-filters">{tag_opts}</div>
</div>
<div id="lib-results" class="read-list"></div>
<script>window.__PAPERS__ = {data_json};</script>
<script src="assets/app.js"></script>"""
    return layout(site, "Library · " + site["title"], body, 0, "library.html")


def page_radio(site: dict, cards: list[dict]) -> str:
    eps = [c for c in cards if c["audio"]]
    rows = "".join(
        f"""<div class="ep">
  <div class="ep-meta"><time>{_fmt_date(c['date'])}</time>
    <a href="papers/{e(c['id'])}.html">{e(c['title'])}</a></div>
  <audio controls preload="none" src="{_rel_audio(c['audio'], 0)}"></audio>
</div>"""
        for c in eps
    )
    body = f"""<section class="page-head">
  <h1>电台 · Radio</h1>
  <p>{len(eps)} episodes — a Chinese audio digest (导读) of each paper. Subscribe via <a href="rss.xml">RSS</a>.</p>
</section>
<div class="radio-list">{rows}</div>"""
    return layout(site, "Radio · " + site["title"], body, 0, "radio.html")


def page_paper(site: dict, c: dict) -> str:
    tags = "".join(f'<span class="tag">{e(t)}</span>' for t in c["tags"])
    links = []
    if c["arxiv"]:
        links.append(f'<a href="{e(c["arxiv"])}">arXiv</a>')
    if c["pdf"]:
        links.append(f'<a href="{e(c["pdf"])}">PDF</a>')
    links_html = " · ".join(links)

    notes_html = ""
    if c["has_notes"]:
        notes_html = f'<section class="notes"><h2>Notes</h2>{markdown(c["notes"])}</section>'
    else:
        notes_html = ('<section class="notes empty-notes"><p>No notes on this paper yet — '
                      'it\'s on the reading list.</p></section>')

    qa_html = ""
    if c["qa"].strip():
        qa_html = f'<section class="qa"><h2>Q&amp;A</h2>{markdown(c["qa"])}</section>'

    audio_html = ""
    if c["audio"]:
        audio_html = f"""<section class="audio-block">
  <h2>Audio digest (电台)</h2>
  <audio controls preload="none" src="{_rel_audio(c['audio'], 1)}"></audio>
</section>"""

    abstract_html = ""
    if c["abstract"]:
        abstract_html = f'<details class="abstract" open><summary>Abstract</summary><p>{e(c["abstract"])}</p></details>'

    digest_html = ""
    if c["digest"]:
        digest_html = f'<details class="digest"><summary>Chinese digest · 导读全文</summary><div class="digest-body">{markdown(c["digest"])}</div></details>'

    rt = _reading_time(c["notes"]) if c["has_notes"] else 0
    rt_html = f" · {rt} min read" if rt else ""

    body = f"""<article class="paper">
  <header class="paper-head">
    <div class="paper-meta"><time>{_fmt_date(c['date'])}</time>{rt_html}{(' · ' + links_html) if links_html else ''}</div>
    <h1>{e(c['title'])}</h1>
    <div class="tags">{tags}</div>
  </header>
  {notes_html}
  {qa_html}
  {audio_html}
  {abstract_html}
  {digest_html}
  <div class="back"><a href="../writing.html">← Writing</a> · <a href="../library.html">Library</a></div>
</article>"""
    return layout(site, c["title"] + " · " + site["title"], body, 1)


# --------------------------------------------------------------------------- #
# Assets
# --------------------------------------------------------------------------- #
def css(site: dict) -> str:
    accent = site.get("accent", "#f0803c")
    return """
:root {
  --bg: #14161a; --panel: #1b1e24; --panel-2: #22262e;
  --text: #e7e9ee; --muted: #9aa2b1; --line: #2c313b;
  --accent: %(accent)s;
  --serif: Georgia, 'Times New Roman', serif;
  --sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
  font-family: var(--sans); line-height: 1.6; -webkit-font-smoothing: antialiased; }
a { color: inherit; text-decoration: none; }
main { max-width: 820px; margin: 0 auto; padding: 0 20px 80px; }
img { max-width: 100%%; }

.site-head { max-width: 820px; margin: 0 auto; padding: 22px 20px;
  display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.brand { font-weight: 800; font-size: 1.15rem; letter-spacing: -.01em; }
.site-head nav { display: flex; gap: 18px; flex-wrap: wrap; }
.site-head nav a { color: var(--muted); font-size: .93rem; }
.site-head nav a:hover, .site-head nav a.active { color: var(--text); }

.hero { padding: 46px 0 26px; border-bottom: 1px solid var(--line); margin-bottom: 30px; }
.hero h1 { font-size: 2.5rem; margin: 0 0 .3em; letter-spacing: -.02em; }
.tagline { font-size: 1.2rem; color: var(--muted); margin: 0 0 1.1em; max-width: 640px; }
.bio { color: var(--text); max-width: 660px; }
.bio p { margin: .5em 0; }
.pills { margin-top: 18px; display: flex; gap: 10px; flex-wrap: wrap; }
.pill { border: 1px solid var(--line); padding: 7px 14px; border-radius: 999px;
  font-size: .88rem; color: var(--muted); transition: .15s; }
.pill:hover { border-color: var(--accent); color: var(--text); }

.section { margin: 42px 0; }
.section-head { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 16px; }
.section h2, .page-head h1 { letter-spacing: -.01em; }
.more { color: var(--accent); font-size: .9rem; }

.post-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
.post-list { display: flex; flex-direction: column; gap: 4px; }
.post-list.wide { gap: 6px; }
.post-card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px;
  transition: .15s; overflow: hidden; }
.post-card:hover { border-color: var(--accent); transform: translateY(-2px); }
.post-card-link { display: block; padding: 18px; }
.post-card-meta { color: var(--muted); font-size: .82rem; margin-bottom: 8px; }
.post-card h3 { margin: 0 0 .4em; font-size: 1.12rem; line-height: 1.35; }
.post-card p { margin: 0 0 12px; color: var(--muted); font-size: .92rem; }

.read-list { display: flex; flex-direction: column; }
.read-row { display: flex; gap: 16px; padding: 13px 4px; border-bottom: 1px solid var(--line); transition: .12s; }
.read-row:hover { background: var(--panel); padding-left: 12px; }
.read-row time { color: var(--accent); font-size: .82rem; min-width: 96px; padding-top: 2px; font-variant-numeric: tabular-nums; }
.read-title { flex: 1; }

.tags { display: flex; gap: 6px; flex-wrap: wrap; }
.tag { background: var(--panel-2); color: var(--muted); font-size: .74rem;
  padding: 2px 9px; border-radius: 999px; }
.badge { background: var(--accent); color: #14161a; font-size: .68rem; font-weight: 700;
  padding: 1px 7px; border-radius: 999px; vertical-align: middle; }
.badge.audio { background: var(--panel-2); color: var(--accent); }

.page-head { padding: 40px 0 24px; }
.page-head h1 { font-size: 2.1rem; margin: 0 0 .2em; }
.page-head p { color: var(--muted); margin: 0; }
.empty { color: var(--muted); }

.lib-controls { margin-bottom: 20px; }
#q { width: 100%%; padding: 13px 16px; background: var(--panel); border: 1px solid var(--line);
  border-radius: 10px; color: var(--text); font-size: 1rem; }
#q:focus { outline: none; border-color: var(--accent); }
.tag-filters { display: flex; gap: 7px; flex-wrap: wrap; margin-top: 12px; }
.tag-filter { background: var(--panel); border: 1px solid var(--line); color: var(--muted);
  padding: 4px 11px; border-radius: 999px; font-size: .8rem; cursor: pointer; transition: .12s; }
.tag-filter:hover { color: var(--text); }
.tag-filter.on { background: var(--accent); color: #14161a; border-color: var(--accent); }

/* paper / post page */
.paper { padding-top: 28px; }
.paper-head { border-bottom: 1px solid var(--line); padding-bottom: 22px; margin-bottom: 28px; }
.paper-meta { color: var(--muted); font-size: .9rem; margin-bottom: 10px; }
.paper-meta a { color: var(--accent); }
.paper-head h1 { font-size: 2rem; line-height: 1.25; margin: 0 0 14px; letter-spacing: -.01em; }
.notes { font-family: var(--serif); font-size: 1.12rem; line-height: 1.75; }
.notes h2, .qa h2, .audio-block h2 { font-family: var(--sans); font-size: .82rem;
  text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin: 34px 0 10px; }
.notes ul, .notes ol { padding-left: 1.3em; }
.notes li { margin: .35em 0; }
.notes a, .qa a, .digest-body a { color: var(--accent); text-decoration: underline; text-underline-offset: 2px; }
.empty-notes p { color: var(--muted); font-family: var(--sans); font-size: 1rem; }
.qa { font-size: 1rem; }

.audio-block audio, .ep audio { width: 100%%; margin-top: 6px; }
details { border-top: 1px solid var(--line); padding: 16px 0; }
details summary { cursor: pointer; color: var(--muted); font-size: .82rem;
  text-transform: uppercase; letter-spacing: .08em; }
details[open] summary { margin-bottom: 12px; }
.abstract p { color: var(--text); }
.digest-body { color: var(--muted); line-height: 1.85; }
.back { margin-top: 40px; color: var(--muted); }
.back a { color: var(--accent); }

.radio-list { display: flex; flex-direction: column; gap: 4px; }
.ep { padding: 14px 0; border-bottom: 1px solid var(--line); }
.ep-meta { display: flex; gap: 12px; align-items: baseline; }
.ep-meta time { color: var(--accent); font-size: .82rem; min-width: 96px; }

.site-foot { max-width: 820px; margin: 0 auto; padding: 30px 20px 50px;
  border-top: 1px solid var(--line); color: var(--muted); font-size: .85rem;
  display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.site-foot a { color: var(--accent); }

@media (max-width: 600px) {
  .hero h1 { font-size: 2rem; }
  .read-row time, .ep-meta time { min-width: 74px; }
}
""" % {"accent": accent}


def app_js() -> str:
    return """
(function () {
  var box = document.getElementById('lib-results');
  var q = document.getElementById('q');
  if (!box) return;
  var active = new Set();
  function boot(papers) {
    function esc(s){var d=document.createElement('div');d.textContent=s||'';return d.innerHTML;}
    function fmt(d){var m=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      var p=(d||'').split('-'); if(p.length<3) return d; return m[+p[1]-1]+' '+(+p[2])+', '+p[0];}
    function render() {
      var term = (q.value || '').toLowerCase().trim();
      var rows = papers.filter(function (p) {
        for (var t of active) if ((p.tags || []).indexOf(t) < 0) return false;
        if (!term) return true;
        return (p.title + ' ' + (p.summary||'') + ' ' + (p.tags||[]).join(' ')).toLowerCase().indexOf(term) >= 0;
      });
      box.innerHTML = rows.slice(0, 300).map(function (p) {
        var badge = p.has_notes ? ' <span class="badge">notes</span>' : '';
        var au = p.audio ? ' <span class="badge audio">\\u266a</span>' : '';
        return '<a class="read-row" href="papers/' + esc(p.id) + '.html"><time>' + fmt(p.date) +
          '</time><span class="read-title">' + esc(p.title) + badge + au + '</span></a>';
      }).join('') || '<p class="empty">No matches.</p>';
    }
    document.querySelectorAll('.tag-filter').forEach(function (b) {
      b.addEventListener('click', function () {
        var t = b.getAttribute('data-tag');
        if (active.has(t)) { active.delete(t); b.classList.remove('on'); }
        else { active.add(t); b.classList.add('on'); }
        render();
      });
    });
    q.addEventListener('input', render);
    render();
  }
  if (window.__PAPERS__) boot(window.__PAPERS__);
  else fetch('papers.json').then(function (r) { return r.json(); }).then(boot);
})();
"""


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #
def load_site() -> dict:
    site = dict(DEFAULT_SITE)
    if SITE_JSON.exists():
        try:
            site.update(json.loads(SITE_JSON.read_text(encoding="utf-8")))
        except Exception as ex:  # keep building even if the config is malformed
            print(f"[site] WARN: bad {SITE_JSON.name}: {ex}")
    return site


def build_site() -> int:
    site = load_site()
    cards = load_cards()

    (PUBLIC / "assets").mkdir(parents=True, exist_ok=True)
    (PUBLIC / "papers").mkdir(parents=True, exist_ok=True)

    (PUBLIC / "assets" / "style.css").write_text(css(site), encoding="utf-8")
    (PUBLIC / "assets" / "app.js").write_text(app_js(), encoding="utf-8")

    (PUBLIC / "index.html").write_text(page_home(site, cards), encoding="utf-8")
    (PUBLIC / "writing.html").write_text(page_writing(site, cards), encoding="utf-8")
    (PUBLIC / "library.html").write_text(page_library(site, cards), encoding="utf-8")
    (PUBLIC / "radio.html").write_text(page_radio(site, cards), encoding="utf-8")

    for c in cards:
        (PUBLIC / "papers" / f"{c['id']}.html").write_text(page_paper(site, c), encoding="utf-8")

    search = [{
        "id": c["id"], "title": c["title"], "date": c["date"], "tags": c["tags"],
        "summary": c["summary"], "has_notes": c["has_notes"], "audio": bool(c["audio"]),
    } for c in cards]
    (PUBLIC / "papers.json").write_text(
        json.dumps(search, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    posts = sum(1 for c in cards if c["has_notes"])
    print(f"[site] {len(cards)} papers ({posts} posts) -> {PUBLIC}/  index.html, writing.html, library.html, radio.html")
    return len(cards)


if __name__ == "__main__":
    build_site()
