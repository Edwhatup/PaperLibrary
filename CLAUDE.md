# Paper Library — guide for Claude Code

This repo is a personal paper library + daily audio digest ("电台"). Papers come
from HuggingFace Daily Papers; the pipeline writes a Chinese 导读 + MP3 and a
per-paper **card**. You (Claude Code) are the query/notes/quiz interface.

## Read this before touching the library

**Always go index-first — do NOT scan `data/` or read every card.**

- `library/index.jsonl` — ONE compact line per paper. Read this first to find
  things. Fields: `id, title, date, tags, listened, read, understood, audio, summary`.
- `library/papers/<arxiv_id>.md` — the full card for one paper. Open ONLY the
  specific card(s) you need, by id.
- A card's `digest:` frontmatter points to the full Chinese 导读 text; `audio:`
  to the MP3. The card body keeps the EN abstract + the user's
  `## 笔记 / ## 问答记录 / ## 测验` sections.

This layout exists to save tokens: the index is tiny, ids are stable filenames,
so you can jump straight to a paper instead of grepping the whole repo.

## Operate via the CLI (keeps the index in sync) — `python scripts/lib.py`

Prefer these over hand-editing cards; status changes auto-rebuild the index.

```
lib.py search QUERY              # grep index by id/title/summary/tags
lib.py list --unread             # filter: --unread --unlistened --unquizzed --tag X
lib.py show ID                   # print the card path, then open it to read
lib.py read ID / unread ID       # mark read
lib.py listened ID / unlistened  # mark listened (听完)
lib.py tag ID t1 t2              # add tags   (untag ID t1 to remove)
lib.py note ID "..."             # append a dated note to ## 笔记
lib.py qa ID -q "..." -a "..."   # append a Q&A to ## 问答记录
lib.py quiz ID --score N --detail "..."   # record a quiz attempt, set understood
lib.py build                     # regenerate cards+index from data/ (safe: never
                                 # overwrites tags/status/notes/Q&A/quiz)
```

`understood`: `null` = 未测验, otherwise the last quiz score 0–100.

## When the user asks about a paper

1. Find it: `lib.py search ...` (or read `index.jsonl`).
2. Read the card; if they want depth, read the file at its `digest:` path.
3. **Record the exchange**: `lib.py qa <id> -q "<their question>" -a "<answer>"`
   so the Q&A is persisted in the card.

## When the user wants to be quizzed (测验/quiz me)

Goal: test whether they *actually understood* a paper, not just listened.

1. Pick a target: a paper that is `read` or `listened` but `understood == null`
   (`lib.py list --unquizzed`), or one the user names. For spaced review, you may
   re-quiz papers whose last quiz was long ago / low score.
2. Read that card + its `digest` text. Ask 3–5 questions probing the core
   mechanism, the why-behind-design, results, and limitations — not trivia.
3. Ask one at a time, let the user answer, then grade and explain gaps.
4. Record it: `lib.py quiz <id> --score <0-100> --detail "<what they nailed / missed>"`.
   This sets `understood` and logs the attempt in `## 测验`.

## Pipeline (audio side — usually runs itself; don't touch unless asked)

`scripts/run_daily.py` orchestrates: fetch → 导读 (Gemini) → edge-tts → feed →
`lib.build_library()`. Runs daily via `.github/workflows/daily.yml`, deploys
`public/` to GitHub Pages. Details in `README.md`.
