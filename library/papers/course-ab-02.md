---
id: "course-ab-02"
title: "Benchmark 设计课 第2讲:静态基准解剖——从 MMLU 到 SWE-bench"
date: "2026-07-07"
arxiv: ""
pdf: ""
upvotes: 0
audio: "public/audio/2026-07-07-benchmark-she-ji-ke-di-2jiang-jing-tai-ji-zhun-jie-pou-cong--d95869b9.mp3"
digest: "data/scripts/2026-07-07-benchmark-she-ji-ke-di-2jiang-jing-tai-ji-zhun-jie-pou-cong-.txt"
tags: ["agent-benchmark", "course"]
listened: false
read: false
---

# Benchmark 设计课 第2讲:静态基准解剖——从 MMLU 到 SWE-bench

> 同一个模型,同一个基准,三个评测框架跑出来的分数,最大能差多少?答案是十五个百分点。2023年,HuggingFace的开放大模型排行榜闹过一次著名的乌龙:社区发现LLaMA六百五十亿参数模型在榜上的MMLU分数,远低于Meta论文里自己报

**摘要 (EN):** 课程第2讲。解剖三代静态基准的设计演化:题库型 MMLU(三种实现同模型差15个百分点、格式波动5%、污染与标注错误四宗罪;BBQ 偏见得分为0实为模型没作答的警世故事)→ 执行验证型 HumanEval(pass@k 无偏估计器、从零手写抗污染;EvalPlus 测试扩充80倍分数集体跳水15分的弱 oracle 教训)→ 真实工件型 SWE-bench(fail-to-pass、时间切分;Verified 审核发现68.3%坏题、GPT-4o 分数翻倍)。收尾讲饱和与 headroom:WebArena 人78% vs GPT-4 14%。

**导读全文:** `data/scripts/2026-07-07-benchmark-she-ji-ke-di-2jiang-jing-tai-ji-zhun-jie-pou-cong-.txt`　**音频:** `public/audio/2026-07-07-benchmark-she-ji-ke-di-2jiang-jing-tai-ji-zhun-jie-pou-cong--d95869b9.mp3`　**arXiv:** 

---
## 笔记
- 来源: HuggingFace open-llm-leaderboard-mmlu 博客 / Anthropic Challenges in evaluating AI systems / HumanEval arXiv:2107.03374 / EvalPlus arXiv:2305.01210 / SWE-bench arXiv:2310.06770 / OpenAI Introducing SWE-bench Verified

## 问答记录

