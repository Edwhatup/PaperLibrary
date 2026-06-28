"""Turn a paper into a long-form spoken 导读 script (Chinese by default).

Length adapts to relevance:
  - matches your INTERESTS  -> LONG_MINUTES  (deep dive)
  - otherwise               -> SHORT_MINUTES (overview)

Needs an LLM (config.LLM_BACKEND = gemini / anthropic) plus the paper's full
text to sustain 10-20 minutes. With no LLM it falls back to a short
abstract-only reading and prints a warning — that path can't reach the target
length.

Output is clean narration text (no markdown / bullets / stage directions) so
it feeds straight into edge-tts.
"""
from __future__ import annotations

import re

import config


def is_relevant(paper: dict) -> bool:
    """Keyword match of the user's INTERESTS against title + abstract."""
    interests = [k.strip().lower() for k in re.split(r"[,，;；、]", config.INTERESTS) if k.strip()]
    if not interests:
        return False
    hay = f"{paper.get('title','')} {paper.get('abstract','')}".lower()
    return any(kw in hay for kw in interests)


def target_minutes(paper: dict) -> int:
    return config.LONG_MINUTES if is_relevant(paper) else config.SHORT_MINUTES


def _prompt(paper: dict, full_text: str, minutes: int) -> str:
    chars = minutes * config.CHARS_PER_MIN
    lang = "中文" if config.DIGEST_LANG == "zh" else "English"
    body = full_text.strip() or paper.get("abstract", "")
    source_note = "以下是论文全文（可能含公式/排版噪声，请抓主干）：" if full_text else "（只有摘要可用，请基于摘要尽量展开）："
    relevant = is_relevant(paper)
    depth = (
        "这篇和听众的研究方向相关，请讲得深入：方法的动机与直觉、关键设计选择和为什么这么设计、"
        "和已有工作的区别、实验设置与最重要的几个结果数字、以及局限和可借鉴之处都要覆盖。"
        if relevant
        else "这篇和听众方向关系不大，做一个清晰的科普式概览即可，重点讲清它解决什么问题、核心思路、和主要结论。"
    )
    lo, hi = int(chars * 0.85), int(chars * 1.1)
    return f"""你是一档面向通勤者的 AI 论文导读播客主播，用{lang}口播。请把下面这篇论文讲成一段约 {minutes} 分钟、
适合开车时收听的连续口播稿。总字数控制在 {lo} 到 {hi} 字之间（务必不要少于 {lo}，也不要明显超过 {hi}），讲完自然收尾。

要求：
- 全程是可以直接朗读的连续口语，不要小标题、不要分点编号、不要"第一部分"这种字样，段落之间自然过渡。
- 开头用一两句话点出这篇解决什么问题、为什么值得听。
- {depth}
- 适当解释专业术语，用类比帮助理解，但不要啰嗦注水；宁可多讲清楚一个机制，也不要重复空话。
- 结尾给一句总结和"对听众有什么启发 / 谁该关注"。
- 只输出口播正文本身。

论文标题：{paper['title']}
{source_note}
{body}
"""


def _gemini_models() -> list[str]:
    """Configured model first, then fallbacks with free-tier availability."""
    chain = [config.GEMINI_MODEL, "gemini-2.0-flash", "gemini-2.5-flash",
             "gemini-2.0-flash-lite", "gemini-1.5-flash"]
    seen, out = set(), []
    for m in chain:
        if m and m not in seen:
            seen.add(m)
            out.append(m)
    return out


def _via_gemini(paper, full_text, minutes):
    import google.generativeai as genai

    genai.configure(api_key=config.GEMINI_API_KEY)
    prompt = _prompt(paper, full_text, minutes)
    # ~0.86 output tokens per Chinese char observed; cap near the target length
    # (with headroom) so off-topic papers stay ~10 min and relevant ~20 min.
    max_tokens = min(8192, int(minutes * config.CHARS_PER_MIN))
    last = None
    for name in _gemini_models():
        try:
            model = genai.GenerativeModel(name)
            resp = model.generate_content(
                prompt,
                generation_config={"max_output_tokens": max_tokens, "temperature": 0.7},
            )
            print(f"[script] gemini ok via {name}")
            return resp.text.strip()
        except Exception as e:
            last = e
            print(f"[script] gemini {name} failed: {str(e)[:140]}")
    raise last


def _via_anthropic(paper, full_text, minutes):
    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=8192,
        messages=[{"role": "user", "content": _prompt(paper, full_text, minutes)}],
    )
    return "".join(b.text for b in msg.content if b.type == "text").strip()


def _fallback(paper: dict) -> str:
    print("[script] WARNING: no LLM configured — short abstract reading only "
          "(can't reach the target length; set LLM_BACKEND + key).")
    if config.DIGEST_LANG == "zh":
        return (f"下面这篇论文标题是：{paper['title']}。以下是它的英文摘要。 {paper['abstract']}")
    return f"{paper['title']}. {paper['abstract']}"


def make_script(paper: dict, full_text: str = "") -> str:
    minutes = target_minutes(paper)
    backend = config.LLM_BACKEND
    try:
        if backend == "gemini" and config.GEMINI_API_KEY:
            return _via_gemini(paper, full_text, minutes)
        if backend == "anthropic" and config.ANTHROPIC_API_KEY:
            return _via_anthropic(paper, full_text, minutes)
    except Exception as e:
        print(f"[script] LLM '{backend}' failed ({e}); falling back to abstract")
    return _fallback(paper)


if __name__ == "__main__":
    demo = {"title": "Attention Is All You Need",
            "abstract": "We propose the Transformer ...", "upvotes": 1}
    print(make_script(demo))
