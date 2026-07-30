# Paper Library 📚🎧

我自己的论文图书馆 + 论文导读电台。每天自动抓 [HuggingFace Daily Papers](https://huggingface.co/papers)，
生成中文/英文导读音频，输出成一个**播客 RSS 订阅源**——用任何播客 App 订阅，开车时就能听。

```
HF Daily Papers API
   └─> 抓取当天热门论文 (fetch_papers.py)
        └─> LLM 生成导读口播稿 (make_script.py，可插拔；不配也能跑)
             └─> edge-tts 合成 MP3 (synth_audio.py，免费免 key，中英都支持)
                  └─> 生成 RSS + markdown 图书馆 (build_feed.py)
                       └─> GitHub Actions 每天定时跑并提交回仓库
```

## 快速开始

```bash
pip install -r requirements.txt

# 跑一次（默认中文导读、免费 edge-tts、无 LLM 时直接读摘要）
python scripts/run_daily.py            # 今天
python scripts/run_daily.py 2026-06-27 # 指定日期
```

产物：
- `public/audio/*.mp3` —— 每篇论文一集音频
- `public/playlist.m3u8` —— **VLC 播放列表（私人收听首选，见下）**
- `public/rss.xml` —— 播客订阅源（要公开托管才有意义）
- `library/README.md` —— 可读的图书馆索引
- `data/` —— 原始论文元数据、导读脚本、节目清单

## 让导读更好听（可选）

不配 LLM 时，中文模式会用中文开场再读英文摘要。想要**真正的中文导读**，配一个 LLM：

```bash
# Gemini（有免费额度，推荐）
export LLM_BACKEND=gemini GEMINI_API_KEY=xxx
# 或 Claude
export LLM_BACKEND=anthropic ANTHROPIC_API_KEY=xxx
pip install google-generativeai   # 或 anthropic
```

## 常用配置（环境变量）

| 变量 | 默认 | 说明 |
|------|------|------|
| `DIGEST_LANG` | `zh` | 导读语言：`zh` / `en` |
| `MAX_PAPERS` | `5` | 每天取前 N 篇（按点赞数） |
| `LLM_BACKEND` | `none` | `none` / `gemini` / `anthropic`（**长稿必须配**） |
| `INTERESTS` | 见 config | 你的方向关键词，命中则按长档处理 |
| `LONG_MINUTES` | `20` | 命中方向的论文，目标时长（分钟） |
| `SHORT_MINUTES` | `10` | 不相关论文的目标时长（分钟） |
| `FETCH_FULLTEXT` | `1` | 抓 arXiv 全文（HTML→PDF 兜底）喂给 LLM；`0` 只用摘要 |
| `TTS_VOICE_ZH` | `zh-CN-YunxiNeural` | 中文音色（`edge-tts --list-voices` 看全部） |
| `TTS_VOICE_EN` | `en-US-AndrewNeural` | 英文音色 |
| `TTS_RATE` | `+8%` | 语速 |
| `FEED_BASE_URL` | 空 | `public/` 的公开地址（如 GitHub Pages），**RSS 里音频链接靠它** |

### 长稿导读（10–20 分钟）

每篇会按是否命中 `INTERESTS` 自动决定长度：**命中 → 深讲 20 分钟**（动机、方法细节、实验数字、局限与借鉴），**不相关 → 科普式概览 10 分钟**。这一档**必须配 LLM**（`LLM_BACKEND=gemini` + key），因为要读全文再展开；不配则退回「读摘要」的短兜底，到不了目标长度。手写的稿子放进 `data/scripts/` 会被原样复用、不覆盖。

## 博客网站（笔记优先，英文为主）

`public/` 现在还是一个静态个人博客（暗色极简），由 `scripts/build_site.py`
从 `library/index.jsonl` + 卡片生成，跟音频/RSS 一起部署到同一个 GitHub Pages：

- **首页** `index.html`：个人简介 + 精选写作 + 最新阅读。
- **Writing** `writing.html`：所有**有笔记**的论文——你写了 `## 笔记` 的卡片
  就会自动变成一篇博客文章（用 `lib.py note <id> "..."` 添加即可）。
- **Library** `library.html`：全部论文，前端搜索 + 标签过滤。
- **电台 Radio** `radio.html`：每篇的中文导读音频（附属）。

站点信息（标题、简介、链接、主题色）在 **`data/site.json`** 里改。
`run_daily.py` 每天自动重建站点；本地单独重建：`python scripts/build_site.py`。

## 订阅（VLC 网络串流 / 播客 App）

仓库公开后用 GitHub Pages 托管 `public/`（`pages.yml` 自动部署）。一次性设置：
仓库设为 Public → Settings → Pages → Source 选 **GitHub Actions**。之后：

- **VLC**：网络串流打开 `https://edwhatup.github.io/PaperLibrary/playlist.m3u8`，
  VLC 会记住这个地址，以后一点就是最新列表。
- **播客 App**（小宇宙/Apple Podcasts/Pocket Casts）：订阅
  `https://edwhatup.github.io/PaperLibrary/rss.xml`，新集自动推送。

## 私人收听：iPhone + VLC（云盘同步，可选）

不想公开成博客？不需要。仓库保持 **private**，用 VLC 放云盘里的 `playlist.m3u8` 即可：

1. 把 `public/`（含 `audio/` 和 `playlist.m3u8`）同步进 Dropbox / Google Drive 的一个文件夹。
   - 手动：下载仓库 `public/` 拖进云盘
   - 全自动：配好 rclone，Action 跑完自动推（见下「全自动同步到云盘」）
2. iPhone 上打开 **VLC → Network / 云服务**，登录同一个云盘，打开那个文件夹里的 `playlist.m3u8`。
3. 上车连 CarPlay/蓝牙，VLC 从头放到尾，就是你的私人论文电台。

> `playlist.m3u8` 用的是相对文件名，所以它和 mp3 放在**同一个云盘文件夹**里就能直接播，无需任何公开 URL。
> 想用「打开网络串流」直接贴一个 m3u 链接，就把仓库变量 `FEED_BASE_URL` 设成那个（私有/不可猜的）托管地址，playlist 里会变成绝对 URL。

## 自动化（GitHub Actions）

`.github/workflows/daily.yml` 每天北京时间 07:00 自动跑并把音频/feed 提交回仓库。
在仓库 **Settings → Secrets and variables → Actions** 里：
- Variables：`DIGEST_LANG`、`LLM_BACKEND`、`MAX_PAPERS`、`FEED_BASE_URL`
- Secrets：`GEMINI_API_KEY` 或 `ANTHROPIC_API_KEY`（用 LLM 时）

> 私有仓库的 Actions 每月有免费分钟额度，这个任务很小，基本用不完。

### 全自动同步到云盘（VLC 自动出新集）

配好后，Action 每天生成音频并自动推到你的私有云盘文件夹，VLC 第二天就能看到新集。
**推荐 Dropbox 或 Google Drive**（rclone 的 iCloud 后端是实验性的，别用）。

一次性配置（约 10 分钟，在你自己电脑上）：

```bash
rclone config        # 新建 remote，名字如 dropbox，浏览器点同意授权
rclone config show   # 复制整段输出
```

然后在 **Settings → Secrets and variables → Actions**：
- Secret `RCLONE_CONF` = `rclone config show` 的整段输出
- Variable `RCLONE_REMOTE` = `dropbox:PaperRadio`（文件夹名随你起）

没设 `RCLONE_REMOTE` 时这步自动跳过，不会报错。设好后 iPhone 上用 VLC 登录
同一个云盘，打开 `PaperRadio/playlist.m3u8` 即可。

把 `public/` 用 GitHub Pages 发布后，`FEED_BASE_URL` 设成 Pages 地址，
然后在播客 App 里订阅 `<FEED_BASE_URL>/rss.xml` 即可。

---

## 附：开源方案调研

围绕「论文导读朗读 / 一站式 TTS」调研到的现成轮子，按用途分：

### 核心引擎（论文 → 对话式音频）
- **[Podcastfy](https://github.com/souzatharsis/podcastfy)** ⭐ — NotebookLM 音频概览的开源平替，最成熟。
  多语言（中英可）、多 TTS 后端（OpenAI / Google / ElevenLabs / **Edge 免费**）、吃 PDF/URL。
  本仓库目前用更轻的自研流水线 + edge-tts；想要双人对话式高质量音频可切到 Podcastfy。
- [Azzedde/paper_to_podcast](https://github.com/Azzedde/paper_to_podcast) — 三人讨论式，OpenAI TTS
- [lamm-mit/PDF2Audio](https://github.com/lamm-mit/PDF2Audio) — Gradio 界面，PDF→播客/讲座/摘要
- [Mozilla Blueprint](https://blog.mozilla.ai/blueprint-deep-dive-turn-documents-into-podcasts-locally-with-open-source-ai/) — 纯本地（OuteTTS），隐私优先

### 直接对接 HF Daily Papers
- [gabrielchua/daily-ai-papers](https://github.com/gabrielchua/daily-ai-papers) — 抓 HF Daily Papers 生成音频摘要，GitHub Actions 全自动（推 Telegram）
- [deep-diver/paper-reviewer](https://github.com/deep-diver/paper-reviewer) — HF Daily Papers 自动深度 review + 语音合成（[在线站](https://deep-diver.github.io/ai-paper-reviewer/)）
- [fabiogiglietto/research-radio](https://github.com/fabiogiglietto/research-radio) — 论文→多人对话播客全流水线（Claude + Gemini + TTS）

### 中文 TTS 引擎（想换更自然的中文音色）
[edge-tts](https://github.com/rany2/edge-tts)（免费首选，本仓库默认）、
[ChatTTS](https://github.com/2noise/ChatTTS)、
[IndexTTS](https://github.com/index-tts/index-tts)、
[EmotiVoice](https://github.com/netease-youdao/EmotiVoice)。
