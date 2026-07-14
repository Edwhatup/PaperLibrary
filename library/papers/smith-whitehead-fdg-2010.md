---
id: "smith-whitehead-fdg-2010"
title: "Analyzing the Expressive Range of a Level Generator"
date: "2010-06-19"
arxiv: "https://dl.acm.org/doi/10.1145/1822348.1822369"
pdf: ""
upvotes: 0
audio: "public/audio/2010-06-19-analyzing-the-expressive-range-of-a-level-generator-17c32bdb.mp3"
digest: "data/scripts/2010-06-19-analyzing-the-expressive-range-of-a-level-generator.txt"
tags: ["levelbench", "reading-list", "t2"]
listened: false
read: false
---

# Analyzing the Expressive Range of a Level Generator

> 做游戏关卡的程序化生成，最让人头疼的问题从来不是"能不能生成"，而是"生成出来的东西到底好不好、够不够多样"。过去大家评价一个关卡生成器，通常就是拿几张图看看，或者跑一遍游戏确认没有穿模、没有死路，能玩就算过关。但这个标准太粗糙了——一个生

**摘要 (EN):** Smith & Whitehead (FDG 2010) introduce 'expressive range' analysis: instead of judging a procedural level generator only by whether individual outputs are playable, characterize the generator by the distribution of its outputs over structural metrics — for platformers, linearity, leniency, and density — visualized as 2-D heatmaps. This reveals a generator's biases, coverage, and the effect of its parameters, giving a principled way to compare generators by what regions of design space they actually reach.

**导读全文:** `data/scripts/2010-06-19-analyzing-the-expressive-range-of-a-level-generator.txt`　**音频:** `public/audio/2010-06-19-analyzing-the-expressive-range-of-a-level-generator-17c32bdb.mp3`　**arXiv:** https://dl.acm.org/doi/10.1145/1822348.1822369

---
## 笔记
- PCG 圈'用输出的结构属性来衡量一个生成器'的奠基作（linearity/leniency/density）。你 oracle 吐的 cyclomatic / sphere 数 / 临界路径就是这套思路的后代。你的结构指标该怎么定，从这篇找根。

## 问答记录

