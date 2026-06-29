"""Build the podcast RSS feed and the markdown library index from the
episode manifest (data/episodes.json).

Run after new episodes are added by run_daily.py. Idempotent: it always
rebuilds rss.xml and library/README.md from the full manifest.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

import config

MANIFEST = config.DATA / "episodes.json"


def load_manifest() -> list[dict]:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return []


def save_manifest(episodes: list[dict]) -> None:
    MANIFEST.write_text(
        json.dumps(episodes, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def add_episode(ep: dict) -> None:
    """Append an episode, de-duplicating by the stable per-paper `key` (so a
    regenerated episode REPLACES the old one rather than adding a duplicate)."""
    episodes = load_manifest()
    eps = {e.get("key") or e["audio"]: e for e in episodes}
    eps[ep.get("key") or ep["audio"]] = ep
    save_manifest(sorted(eps.values(), key=lambda e: e["published"], reverse=True))


def _audio_url(filename: str) -> str:
    if config.FEED_BASE_URL:
        return f"{config.FEED_BASE_URL}/audio/{filename}"
    return f"audio/{filename}"


def _rfc2822(iso: str) -> str:
    pub = datetime.fromisoformat(iso)
    if pub.tzinfo is None:
        pub = pub.replace(tzinfo=timezone.utc)
    return format_datetime(pub)


def build_rss() -> None:
    episodes = load_manifest()
    lang = "zh-cn" if config.DIGEST_LANG == "zh" else "en"
    site = config.FEED_BASE_URL or "https://example.com"
    itns = "http://www.itunes.com/dtds/podcast-1.0.dtd"

    items = []
    for ep in episodes:  # already newest-first in the manifest
        path = config.AUDIO_DIR / ep["audio"]
        size = path.stat().st_size if path.exists() else ep.get("size", 0)
        # edge-tts output is ~48 kbps CBR -> duration ≈ bytes*8/48000 seconds.
        dur = int(size * 8 / 48000)
        link = ep.get("url") or _audio_url(ep["audio"])
        items.append(
            "    <item>\n"
            f"      <title>{escape(ep['title'])}</title>\n"
            f"      <description>{escape(ep.get('notes') or ep.get('abstract', ''))}</description>\n"
            f"      <link>{escape(link)}</link>\n"
            f"      <guid isPermaLink=\"false\">{escape(ep['audio'])}</guid>\n"
            f"      <pubDate>{_rfc2822(ep['published'])}</pubDate>\n"
            f"      <itunes:duration>{dur}</itunes:duration>\n"
            f"      <enclosure url=\"{escape(_audio_url(ep['audio']))}\" "
            f"length=\"{size}\" type=\"audio/mpeg\"/>\n"
            "    </item>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<rss version="2.0" xmlns:itunes="{itns}">\n'
        "  <channel>\n"
        f"    <title>{escape(config.FEED_TITLE)}</title>\n"
        f"    <link>{escape(site)}</link>\n"
        f"    <description>{escape(config.FEED_DESC)}</description>\n"
        f"    <language>{lang}</language>\n"
        f"    <itunes:author>{escape(config.FEED_AUTHOR)}</itunes:author>\n"
        '    <itunes:category text="Technology"/>\n'
        f"{chr(10).join(items)}\n"
        "  </channel>\n"
        "</rss>\n"
    )

    out = config.PUBLIC / "rss.xml"
    out.write_text(xml, encoding="utf-8")
    print(f"[feed] {len(episodes)} episodes -> {out}")


def build_library_index() -> None:
    episodes = load_manifest()
    lines = ["# 论文图书馆 · Paper Library\n"]
    if config.FEED_BASE_URL:
        lines.append(f"📻 播客订阅源（RSS）：`{config.FEED_BASE_URL}/rss.xml`\n")
    by_date: dict[str, list[dict]] = {}
    for ep in episodes:
        by_date.setdefault(ep["date"], []).append(ep)
    for d in sorted(by_date, reverse=True):
        lines.append(f"\n## {d}\n")
        for ep in by_date[d]:
            star = f" · {ep['upvotes']}★" if ep.get("upvotes") else ""
            audio = _audio_url(ep["audio"])
            paper_link = f"[arXiv]({ep['url']})" if ep.get("url") else ""
            lines.append(f"- **{ep['title']}**{star} — [🔊 音频]({audio}) {paper_link}")
    (config.LIBRARY / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[index] library/README.md ({len(episodes)} episodes)")


def build_playlist() -> None:
    """Emit an M3U8 playlist for VLC (iOS/desktop).

    If FEED_BASE_URL is set, entries are absolute URLs (works with VLC's
    "Open Network Stream"). Otherwise entries are bare filenames, which VLC
    resolves relative to the playlist's own location — drop playlist.m3u8 next
    to the mp3s in the same cloud folder (iCloud/Dropbox) and it just works.
    """
    episodes = load_manifest()  # newest first
    lines = ["#EXTM3U"]
    # Manifest is newest-first; reverse so the playlist plays oldest -> newest.
    for ep in reversed(episodes):
        secs = ep.get("duration", -1)
        title = f"{ep['date']} · {ep['title']}"
        lines.append(f"#EXTINF:{secs},{title}")
        lines.append(_audio_url(ep["audio"]))
    out = config.PUBLIC / "playlist.m3u8"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[playlist] {len(episodes)} tracks -> {out}")


def build_all() -> None:
    build_rss()
    build_playlist()
    build_library_index()


if __name__ == "__main__":
    build_all()
