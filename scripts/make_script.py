"""Turn a paper (title + abstract) into a spoken 导读 script.

Pluggable LLM backend (config.LLM_BACKEND):
  - "gemini"    -> Google Gemini (free tier available)
  - "anthropic" -> Claude
  - "none"      -> no LLM; just read title + abstract verbatim (English),
                   or a minimal Chinese frame if DIGEST_LANG=zh.

The output is plain narration text (no markdown, no stage directions) so it
feeds straight into edge-tts.
"""
from __future__ import annotations

import config

_ZH_PROMPT = """你是一档面向通勤者的 AI 论文导读播客主播。请把下面这篇论文讲成一段 90~150 秒、
适合开车时收听的中文口播稿。要求：
- 开头一句话点出这篇论文解决什么问题、为什么值得关注；
- 用大白话讲清核心方法和最关键的结果，避免堆术语，必要术语顺带解释；
- 结尾给一句「谁该关注 / 有什么启发」。
- 只输出可以直接朗读的纯文本，不要标题、不要分点符号、不要旁白提示。

论文标题：{title}
摘要：{abstract}
"""

_EN_PROMPT = """You are the host of a commuter-friendly AI paper digest podcast.
Turn the paper below into a 90-150s spoken script for listening while driving:
- open with the problem it solves and why it matters;
- explain the core method and key result in plain language;
- close with who should care / the takeaway.
Output only clean narration text — no title, no bullets, no stage directions.

Title: {title}
Abstract: {abstract}
"""


def _prompt(paper: dict) -> str:
    tmpl = _ZH_PROMPT if config.DIGEST_LANG == "zh" else _EN_PROMPT
    return tmpl.format(title=paper["title"], abstract=paper["abstract"])


def _via_gemini(paper: dict) -> str:
    import google.generativeai as genai

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel(config.GEMINI_MODEL)
    resp = model.generate_content(_prompt(paper))
    return resp.text.strip()


def _via_anthropic(paper: dict) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": _prompt(paper)}],
    )
    return "".join(b.text for b in msg.content if b.type == "text").strip()


def _fallback(paper: dict) -> str:
    if config.DIGEST_LANG == "zh":
        # No LLM means no translation; frame in Chinese, read abstract as-is.
        return (
            f"下面这篇论文标题是：{paper['title']}。以下是它的英文摘要。"
            f" {paper['abstract']}"
        )
    return f"{paper['title']}. {paper['abstract']}"


def make_script(paper: dict) -> str:
    backend = config.LLM_BACKEND
    try:
        if backend == "gemini" and config.GEMINI_API_KEY:
            return _via_gemini(paper)
        if backend == "anthropic" and config.ANTHROPIC_API_KEY:
            return _via_anthropic(paper)
    except Exception as e:  # never let one paper kill the run
        print(f"[script] LLM '{backend}' failed ({e}); falling back to abstract")
    return _fallback(paper)


if __name__ == "__main__":
    demo = {
        "title": "Attention Is All You Need",
        "abstract": "We propose the Transformer, a model architecture relying "
        "entirely on attention mechanisms.",
    }
    print(make_script(demo))
