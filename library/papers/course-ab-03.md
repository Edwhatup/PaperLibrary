---
id: "course-ab-03"
title: "Benchmark 设计课 第3讲:错误分析——一线团队的评测基本功"
date: "2026-07-08"
arxiv: ""
pdf: ""
upvotes: 0
audio: "public/audio/2026-07-08-benchmark-she-ji-ke-di-3jiang-cuo-wu-fen-xi-yi-xian-tuan-dui-244489f7.mp3"
digest: "data/scripts/2026-07-08-benchmark-she-ji-ke-di-3jiang-cuo-wu-fen-xi-yi-xian-tuan-dui.txt"
tags: ["agent-benchmark", "course"]
listened: false
read: false
---

# Benchmark 设计课 第3讲:错误分析——一线团队的评测基本功

> 这一讲我们暂时把公共基准放一放,去看工业界一线是怎么评测自己的AI产品的。你可能会问,我要设计的是公开的agent基准,为什么要学产品评测?原因很直接:公共基准的每一个组件,任务、打分器、失败分类,本质上都是产品评测方法论的规模化版本,而产

**摘要 (EN):** 课程第3讲。产品级 evals 教义如何服务公共基准设计:Hamel Husain 评测三层级(断言/人工+模型评审/A-B测试)、Rechat 打地鼠泥潭案例、错误分析三步法(开放式编码→主轴编码→量化,初始读100条trace、约20条无新类别即饱和、60-80%预算花在评测)、NurtureBoss 日期处理33%→95% 案例、二元 pass/fail 优于 Likert、仁慈独裁者标注模式、合理通过率约70%、合成数据只造输入不造输出,以及 Anthropic 数量优先与 Hamel 人肉精读的张力调和:先定性发现、再定量规模化。

**导读全文:** `data/scripts/2026-07-08-benchmark-she-ji-ke-di-3jiang-cuo-wu-fen-xi-yi-xian-tuan-dui.txt`　**音频:** `public/audio/2026-07-08-benchmark-she-ji-ke-di-3jiang-cuo-wu-fen-xi-yi-xian-tuan-dui-244489f7.mp3`　**arXiv:** 

---
## 笔记
- 来源: hamel.dev/blog/posts/evals / hamel.dev/blog/posts/field-guide / hamel.dev/blog/posts/evals-faq (Hamel & Shreya Shankar) / OpenAI Evaluation Best Practices / Anthropic docs Create strong empirical evaluations

## 问答记录

