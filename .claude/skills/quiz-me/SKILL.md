---
name: quiz-me
description: Quiz the user on a paper to test whether they REALLY understood it. Use when the user says things like "考考我"/"quiz me"/"测验一下 <paper>"/"test my understanding" about a paper in this library. Reads the paper's card + Chinese 导读, asks 3–5 probing questions one at a time, grades each answer and explains gaps. Ephemeral — does NOT write anything to the repo.
---

# Quiz the user on a paper (no records kept)

Goal: find out if the user *actually understood* a paper — not recall trivia.
This is deliberately **stateless**: do not run `lib.py quiz`, do not edit cards,
do not persist a score. When the session ends, the quiz is gone.

## Steps

1. **Pick the paper.**
   - If the user named one: `python scripts/lib.py search "<terms>"` → get the id.
   - Otherwise offer to quiz something they've consumed:
     `python scripts/lib.py list --read` (or `--listened`), let them choose.
   - Read `library/papers/<id>.md`, then read the full digest at the path in its
     `digest:` frontmatter field (that's the substance to quiz on). If the paper
     has no digest, read the abstract + fetch the arXiv page if needed.

2. **Ask 3–5 questions, ONE AT A TIME.** Probe understanding, not memory:
   - the core problem and *why existing approaches fail*,
   - the key mechanism and the *intuition / why it's designed that way*,
   - what the main result actually shows (and what it doesn't),
   - a limitation or a "what would break this" edge case.
   Wait for the user's answer before revealing anything or moving on.

3. **Grade each answer out loud**: 对 / 部分对 / 没答到, then give the correct
   answer concisely and point to the relevant part of the paper. Be a fair but
   honest grader — don't rubber-stamp vague answers.

4. **Wrap up** with a short verdict (掌握得怎么样) and 1–2 things to review. Then
   stop. Nothing is written to disk.

## Notes
- Keep questions in Chinese unless the user prefers English.
- If the user explicitly asks you to record a takeaway ("记一下"), you may use
  `python scripts/lib.py note <id> "..."` — but the default is to persist nothing.
