"""Fetch an arXiv paper's full text as clean plain text.

Tries arXiv's native HTML render first, then the ar5iv mirror. Falls back to
an empty string (caller then uses the abstract only). No heavy HTML deps — a
small stdlib HTMLParser strips tags and drops script/style/math noise.
"""
from __future__ import annotations

from html.parser import HTMLParser

import requests

import config

_SKIP_TAGS = {"script", "style", "math", "nav", "header", "footer", "figure"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self._chunks.append(text)

    def text(self) -> str:
        return "\n".join(self._chunks)


def _html_to_text(html: str) -> str:
    p = _TextExtractor()
    p.feed(html)
    return p.text()


def fetch_fulltext(arxiv_id: str) -> str:
    if not arxiv_id or not config.FETCH_FULLTEXT:
        return ""
    urls = [
        f"https://arxiv.org/html/{arxiv_id}",
        f"https://ar5iv.labs.arxiv.org/html/{arxiv_id}",
    ]
    # A real HTML render is many thousands of chars; arxiv.org/html returns a
    # short abstract/stub page when no render exists, so require a substantial
    # body before accepting and otherwise fall through to the next source.
    best = ""
    for url in urls:
        try:
            r = requests.get(url, timeout=45, headers={"User-Agent": "paper-library/1.0"})
            if r.status_code == 200 and len(r.text) > 2000:
                text = _html_to_text(r.text)
                if len(text) > len(best):
                    best = text
                if len(text) > config.FULLTEXT_MIN_CHARS:
                    return text[: config.FULLTEXT_MAX_CHARS]
        except Exception as e:
            print(f"[fulltext] {url} failed: {e}")
    # No usable HTML render — fall back to extracting text from the PDF.
    pdf_text = _fetch_pdf_text(arxiv_id)
    if len(pdf_text) > len(best):
        best = pdf_text
    if best:
        print(f"[fulltext] {arxiv_id}: using {len(best)} chars")
    else:
        print(f"[fulltext] no full text for {arxiv_id}; abstract only")
    return best[: config.FULLTEXT_MAX_CHARS]


def _fetch_pdf_text(arxiv_id: str) -> str:
    import io

    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    try:
        r = requests.get(
            f"https://arxiv.org/pdf/{arxiv_id}",
            timeout=60,
            headers={"User-Agent": "paper-library/1.0"},
        )
        if r.status_code != 200 or not r.content:
            return ""
        reader = PdfReader(io.BytesIO(r.content))
        return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    except Exception as e:
        print(f"[fulltext] PDF fallback failed for {arxiv_id}: {e}")
        return ""


if __name__ == "__main__":
    import sys

    t = fetch_fulltext(sys.argv[1] if len(sys.argv) > 1 else "1706.03762")
    print(f"{len(t)} chars\n---\n{t[:1500]}")
