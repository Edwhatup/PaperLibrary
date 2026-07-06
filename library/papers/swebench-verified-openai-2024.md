---
id: "swebench-verified-openai-2024"
title: "SWE-bench Verified"
date: "2024-08-13"
arxiv: "https://openai.com/index/introducing-swe-bench-verified/"
pdf: ""
upvotes: 0
audio: "public/audio/2024-08-13-swe-bench-verified-f772e2fa.mp3"
digest: "data/scripts/2024-08-13-swe-bench-verified.txt"
tags: ["levelbench", "reading-list", "t1"]
listened: false
read: false
---

# SWE-bench Verified

> 我们今天来聊聊一个在人工智能领域，尤其是在大型语言模型（LLM）评估中，常常被忽视但又极其关键的问题：我们用来衡量模型能力的那些基准测试，它们本身真的可靠吗？具体来说，我们今天要深入探讨的是一篇来自OpenAI的研究，它聚焦于SWE-ben

**摘要 (EN):** OpenAI's human-validated subset of SWE-bench: 500 task instances screened by 93 professional software engineers to remove unsolvable or under-specified problems and broken/insufficient test oracles. It fixes the finding that ~8% of nominal 'passes' on the original SWE-bench were false positives, so measured resolve rates reflect real capability rather than test-suite artifacts. The 93-reviewer screening protocol is a template for pre-launch benchmark auditing.

**导读全文:** `data/scripts/2024-08-13-swe-bench-verified.txt`　**音频:** `public/audio/2024-08-13-swe-bench-verified-f772e2fa.mp3`　**arXiv:** https://openai.com/index/introducing-swe-bench-verified/

---
## 笔记
- 8% 的'通过'其实是假阳性，这个教训 = 你 oracle 可信度的生死线。93 人审核流程就是你公开前要照抄的 pre-launch audit。

## 问答记录

