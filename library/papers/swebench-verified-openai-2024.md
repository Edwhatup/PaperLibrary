---
id: "swebench-verified-openai-2024"
title: "SWE-bench Verified"
date: "2024-08-13"
arxiv: "https://openai.com/index/introducing-swe-bench-verified/"
pdf: ""
upvotes: 0
audio: "public/audio/2024-08-13-swe-bench-verified-9d0659b0.mp3"
digest: "data/scripts/2024-08-13-swe-bench-verified.txt"
tags: ["levelbench", "reading-list", "t1"]
listened: false
read: false
---

# SWE-bench Verified

> 软件工程领域有一个非常经典的痛点：我们想用基准测试来衡量AI系统真正解决代码问题的能力，但如果基准测试本身就有缺陷，那么测出来的数字根本不能信。SWE-bench Verified这篇工作，核心就是在解决这个问题——原始SWE-bench里

**摘要 (EN):** OpenAI's human-validated subset of SWE-bench: 500 task instances screened by 93 professional software engineers to remove unsolvable or under-specified problems and broken/insufficient test oracles. It fixes the finding that ~8% of nominal 'passes' on the original SWE-bench were false positives, so measured resolve rates reflect real capability rather than test-suite artifacts. The 93-reviewer screening protocol is a template for pre-launch benchmark auditing.

**导读全文:** `data/scripts/2024-08-13-swe-bench-verified.txt`　**音频:** `public/audio/2024-08-13-swe-bench-verified-9d0659b0.mp3`　**arXiv:** https://openai.com/index/introducing-swe-bench-verified/

---
## 笔记
- 8% 的'通过'其实是假阳性，这个教训 = 你 oracle 可信度的生死线。93 人审核流程就是你公开前要照抄的 pre-launch audit。

## 问答记录

