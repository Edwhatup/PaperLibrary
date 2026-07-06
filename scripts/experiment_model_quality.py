"""One-off experiment: generate the SAME 导读 with several Anthropic models,
using the exact production prompt/length logic, for a blind quality
comparison against the existing Gemini scripts.

Writes data/experiments/<arxiv_id>__<model>.txt. Touches nothing else
(no manifest, no cards, no audio). Resumable; failures are per-model.

Usage:  ANTHROPIC_API_KEY=... python scripts/experiment_model_quality.py
"""
from __future__ import annotations

import config
import fetch_arxiv
import fetch_fulltext
import make_script

PAPERS = ["2310.06770", "2306.00107"]  # SWE-bench (levelbench), MERT (metro)
MODELS = [
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-6",
    "claude-sonnet-5",
]


def main() -> None:
    out = config.DATA / "experiments"
    out.mkdir(parents=True, exist_ok=True)
    meta = fetch_arxiv.fetch_many(PAPERS)
    for pid in PAPERS:
        paper = meta.get(pid)
        if not paper:
            print(f"[exp] no metadata for {pid}, skipping")
            continue
        full_text = fetch_fulltext.fetch_fulltext(pid)
        minutes = make_script.target_minutes(paper)
        print(f"\n=== {pid} ({minutes}min): {paper['title'][:70]} ===")
        for model in MODELS:
            dest = out / f"{pid}__{model}.txt"
            if dest.exists():
                print(f"[exp] reuse {dest.name}")
                continue
            config.ANTHROPIC_MODEL = model  # _via_anthropic reads this at call time
            try:
                raw, _truncated = make_script._via_anthropic(paper, full_text, minutes)
                script = make_script.trim_to_sentence(make_script.clean_for_tts(raw))
                dest.write_text(script, encoding="utf-8")
                print(f"[exp] {dest.name}: {len(script)} chars")
            except Exception as e:
                print(f"[exp] {model} on {pid} FAILED: {str(e)[:200]}")


if __name__ == "__main__":
    main()
