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
        "这篇和听众的研究方向相关，要讲得很深入、很完整：研究背景和它真正想解决的痛点、"
        "方法的动机与直觉、每一个关键设计选择以及为什么这么设计、和已有工作/基线的区别、"
        "实验设置与最重要的几个结果数字和它们说明了什么、消融或诊断实验的发现、"
        "以及局限性和对听众工作的具体可借鉴之处，都要展开讲透。"
        if relevant
        else "这篇虽然和听众方向不完全对口，但也要讲得清楚扎实、有信息量：研究背景与问题、"
        "核心方法和它的直觉、关键设计、主要实验结论、以及它的意义和局限，都要覆盖，不要只停在一句话概括。"
    )
    lo, hi = int(chars * 0.9), int(chars * 1.2)
    return f"""请把下面这篇论文写成一段约 {minutes} 分钟、用{lang}讲解、适合开车时收听的连续口播稿。
总字数 {lo} 到 {hi} 字之间：不少于 {lo}（要讲得扎实有料），但**也不要超过 {hi}**——
讲到位就收尾，不要为了凑长度而注水或重复。**最重要：必须把话讲完、用完整的句子自然结束，绝不能停在半句话。**

要求：
- 第一句话就直接切入这篇论文要解决的问题，禁止任何开场白、问候语、自我介绍、报播客名/栏目名，
  绝对不要出现"各位""大家好""欢迎收听""我是主播""通勤路上""本期节目"这类套话。
- 全程是可以直接朗读的连续口语，不要小标题、不要分点编号、不要"第一部分"这种字样，段落之间自然过渡。
- 输出必须是纯文本，严禁任何 Markdown 记号：不要星号加粗、不要井号标题、不要反引号、不要列表符号。
  这些符号会被语音合成逐字念出来（语音里不存在"加粗"），想强调就用语气词和句式来强调。
- {depth}
- 适当解释专业术语，用类比帮助理解；宁可多讲清楚一个机制，也不要泛泛而谈，但点到为止、不要无限展开。
- 结尾直接给一句结论和启发收住，不要"以上就是""感谢收听"这类结束语。
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
    # Generous headroom so the model can FINISH its closing sentence well within
    # budget (target is bounded in the prompt). gemini-2.5-flash supports large
    # output; ~1.6 tokens/Chinese-char with buffer, capped high.
    max_tokens = min(16000, int(minutes * config.CHARS_PER_MIN * 2.0))
    last = None
    for name in _gemini_models():
        for attempt in range(2):  # one retry on transient rate limits
            try:
                model = genai.GenerativeModel(name)
                resp = model.generate_content(
                    prompt,
                    generation_config={"max_output_tokens": max_tokens, "temperature": 0.7},
                )
                fr = ""
                try:
                    fr = str(resp.candidates[0].finish_reason)
                except Exception:
                    pass
                truncated = "MAX_TOKENS" in fr
                if truncated:
                    print(f"[script] WARNING: {name} hit MAX_TOKENS ({max_tokens})")
                print(f"[script] gemini ok via {name}")
                return resp.text.strip(), truncated
            except Exception as e:
                last, msg = e, str(e)
                transient = any(s in msg for s in
                                ("429", "503", "rate", "quota", "overloaded", "ResourceExhausted"))
                print(f"[script] gemini {name} attempt {attempt+1} failed: {msg[:120]}")
                if transient and attempt == 0:
                    import time
                    time.sleep(25)  # wait out a per-minute rate limit, then retry
                    continue
                break  # non-transient, or already retried -> next model
    raise last


def _via_anthropic(paper, full_text, minutes):
    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    # Match the Gemini headroom: a 20-min zh digest is ~6800 chars (~10-13k
    # tokens), so 8192 truncated mid-sentence. Cap at 16000 like _via_gemini.
    max_tokens = min(16000, int(minutes * config.CHARS_PER_MIN * 2.0))
    msg = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": _prompt(paper, full_text, minutes)}],
    )
    truncated = msg.stop_reason == "max_tokens"
    if truncated:
        print(f"[script] WARNING: anthropic hit max_tokens ({max_tokens})")
    return "".join(b.text for b in msg.content if b.type == "text").strip(), truncated


def _fallback(paper: dict) -> str:
    print("[script] WARNING: no LLM configured — short abstract reading only "
          "(can't reach the target length; set LLM_BACKEND + key).")
    if config.DIGEST_LANG == "zh":
        return (f"下面这篇论文标题是：{paper['title']}。以下是它的英文摘要。 {paper['abstract']}")
    return f"{paper['title']}. {paper['abstract']}"


def clean_for_tts(text: str) -> str:
    """Strip Markdown the LLM sneaks in despite the prompt. TTS reads the
    symbols literally ("星号星号…") — there is no such thing as bold in audio."""
    t = text.replace("\r\n", "\n")
    t = re.sub(r"```[^\n]*", "", t)                              # code fences
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)               # [text](url)
    t = re.sub(r"^\s{0,3}#{1,6}\s*", "", t, flags=re.M)          # # headings
    t = re.sub(r"^\s*[-*•·]\s+", "", t, flags=re.M)              # bullets
    t = re.sub(r"^\s*>\s?", "", t, flags=re.M)                   # blockquotes
    t = re.sub(r"^\s*\|.*\|\s*$", "", t, flags=re.M)             # table rows
    t = re.sub(r"(?<![A-Za-z0-9])_([^_\n]+)_(?![A-Za-z0-9])", r"\1", t)  # _em_
    t = t.replace("**", "").replace("__", "")
    for ch in ("*", "＊", "`", "#"):                              # leftovers
        t = t.replace(ch, "")
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


_SENT_END = "。！？.!?”\"’'）)"


def trim_to_sentence(text: str) -> str:
    """Drop any dangling half-sentence so TTS never ends mid-word.

    Cut everything after the last sentence-ending punctuation. Only applied
    when there's a real tail to drop (avoids nibbling clean endings)."""
    text = text.rstrip()
    if not text or text[-1] in _SENT_END:
        return text
    cut = max(text.rfind(p) for p in _SENT_END)
    if cut > len(text) * 0.5:  # keep most of the script; only trim a true tail
        trimmed = text[: cut + 1].rstrip()
        print(f"[script] trimmed dangling tail: …{text[cut+1:cut+30]!r}")
        return trimmed
    return text  # no sane boundary found — leave as-is rather than gut it


def _backend_chain() -> list[tuple[str, callable]]:
    """Primary backend first, then the other one as fallback if its key is
    set — a Gemini quota failure falls through to Claude instead of skipping."""
    chain = []
    if config.LLM_BACKEND == "anthropic":
        order = [("anthropic", _via_anthropic), ("gemini", _via_gemini)]
    else:
        order = [("gemini", _via_gemini), ("anthropic", _via_anthropic)]
    for name, fn in order:
        key = config.GEMINI_API_KEY if name == "gemini" else config.ANTHROPIC_API_KEY
        if key:
            chain.append((name, fn))
    return chain


def make_script(paper: dict, full_text: str = ""):
    """Return the spoken script, or None when every configured LLM FAILS
    (e.g. quota/429) or returns a cut-off script — the caller then skips this
    paper instead of publishing a broken episode. With LLM_BACKEND=none,
    returns the abstract reading, which is the intended degraded mode."""
    minutes = target_minutes(paper)
    if config.LLM_BACKEND == "none":
        return trim_to_sentence(clean_for_tts(_fallback(paper)))
    # Completeness gate. Two different "short" cases:
    #   - TRUNCATED (hit max_tokens): never publish; try the next backend.
    #   - finished naturally but short: the source is too thin to sustain the
    #     target — accept above a relaxed floor rather than skip forever.
    min_chars = int(minutes * config.CHARS_PER_MIN * 0.75)
    floor_chars = int(minutes * config.CHARS_PER_MIN * 0.45)
    chain = _backend_chain()
    if not chain:
        print(f"[script] backend '{config.LLM_BACKEND}' has no usable key — skipping")
        return None
    best = None
    for name, fn in chain:
        try:
            raw, truncated = fn(paper, full_text, minutes)
        except Exception as e:
            print(f"[script] {name} FAILED ({str(e)[:160]}) — trying next backend")
            continue
        script = trim_to_sentence(clean_for_tts(raw))
        if truncated:
            print(f"[script] {name} TRUNCATED at {len(script)} chars — "
                  "trying next backend")
            continue
        if len(script) >= min_chars:
            return script
        print(f"[script] {name} finished short ({len(script)} < {min_chars} chars)"
              " — source may be too thin for the target length")
        if len(script) >= floor_chars and (best is None or len(script) > len(best)):
            best = script
    if best is not None:
        print(f"[script] accepting best complete-but-short script ({len(best)} chars)")
        return best
    print("[script] all backends failed — skipping this paper")
    return None


if __name__ == "__main__":
    demo = {"title": "Attention Is All You Need",
            "abstract": "We propose the Transformer ...", "upvotes": 1}
    print(make_script(demo))
