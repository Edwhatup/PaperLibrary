---
id: "smith-whitehead-fdg-2010"
title: "Analyzing the Expressive Range of a Level Generator"
date: "2010-06-19"
arxiv: "https://dl.acm.org/doi/10.1145/1822348.1822369"
pdf: ""
upvotes: 0
audio: "public/audio/2010-06-19-analyzing-the-expressive-range-of-a-level-generator-9b4d8dbe.mp3"
digest: "data/scripts/2010-06-19-analyzing-the-expressive-range-of-a-level-generator.txt"
tags: ["levelbench", "reading-list", "t2"]
listened: false
read: false
---

# Analyzing the Expressive Range of a Level Generator

> 我们通常评价一个游戏关卡生成器好坏，往往是看它单独生成的某个关卡能不能玩、玩起来怎么样。这种评价方式虽然直观，但它有一个很大的局限性：就像我们不能只凭一幅画就判断一位画家的整体风格和能力一样，仅仅看一两个生成的关卡，我们也很难真正了解这个关

**摘要 (EN):** Smith & Whitehead (FDG 2010) introduce 'expressive range' analysis: instead of judging a procedural level generator only by whether individual outputs are playable, characterize the generator by the distribution of its outputs over structural metrics — for platformers, linearity, leniency, and density — visualized as 2-D heatmaps. This reveals a generator's biases, coverage, and the effect of its parameters, giving a principled way to compare generators by what regions of design space they actually reach.

**导读全文:** `data/scripts/2010-06-19-analyzing-the-expressive-range-of-a-level-generator.txt`　**音频:** `public/audio/2010-06-19-analyzing-the-expressive-range-of-a-level-generator-9b4d8dbe.mp3`　**arXiv:** https://dl.acm.org/doi/10.1145/1822348.1822369

---
## 笔记
- PCG 圈'用输出的结构属性来衡量一个生成器'的奠基作（linearity/leniency/density）。你 oracle 吐的 cyclomatic / sphere 数 / 临界路径就是这套思路的后代。你的结构指标该怎么定，从这篇找根。

## 问答记录

