# AI Musician Skills

> 让 AI 不只生成音乐，也能帮助音乐人理解音乐、学习音乐、演奏音乐。

AI Musician Skills 是一套面向音乐创作、扒谱、练习和编配场景的
Agent Skills。它的目标不是让 AI 替代音乐人写完一首歌，而是让 Codex、
Claude Code 等 Agent 获得一些具体、可执行的音乐工作能力：分析一个和弦
进行、选择更顺手的指法、根据风格调整 voicing、把想法整理成真正能上手
演奏的版本。

这个项目来自另一个音乐分析工具
[AI-ChordCraft](https://github.com/jassary08/AI-ChordCraft)。AI-ChordCraft
更偏向“听懂一首歌”：上传音频后自动划分 intro、verse、chorus、bridge
等段落，识别按时间轴对齐的和弦走向，并支持基于 LLM 的音乐问答。
而 AI-Musician-Skills 更偏向“下一步怎么弹”：当你已经知道这段是什么
和弦、什么结构之后，它进一步帮助你把这些信息转化成吉他、贝斯、钢琴、
鼓组等乐器上可练、可改、可编配的具体方案。

很多时候，音乐人需要的并不是 AI 替你生成一首完整歌曲，而是像一个懂音乐
的助手一样，在具体问题上帮你往前走一步：新手看到和弦知道名字却不知道
怎么按；进阶乐手想把普通进行改成 R&B、Funk、Blues 的味道，却需要设计
更合适的指法和声部；乐队伴奏吉他手只想在高音弦上弹几个干净的小型三和弦，
给人声和低频留出空间。

AI Musician Skills 尝试用 skill 的方式把这些经验拆成可复用的工具和规则，
让 AI 从“给建议”进一步走向“能执行”：既能保留 Agent 的理解和规划能力，
也能通过脚本、规则库和乐器知识，把复杂的编曲判断落到清晰、可验证的输出。
第一个开源方向是面向吉他手的和弦指法编配，后续会继续探索贝斯线、鼓组
节奏型、钢琴弹唱改编和乐队总谱编配等方向。

---

## 📢 News

**2026-06** — 开源第一个技能：[**`guitar-arrange-skill`**](#guitar-arrange-skill) 🎸

面向吉他手的智能指法安排技能，支持数字级数输入、风格化编配、中高把位、小型三和弦、R&B 色彩和弦等场景。

---

## guitar-arrange-skill

把一段和弦进行（或自然语言描述）变成一份**真正可弹奏**的吉他编配，包含指法选择、把位安排和和弦图输出。

### 能处理什么

- **数字级数 → 指法**：`E 大调 1-5-6-3-4-1-2-5` 直接转成具体和弦 + 常用指型
- **风格化编配**：R&B 进阶指法、Blues 12小节展开、流行三和弦等
- **把位限定**：指定不同把位时安排合适的吉他指法
- **小型三和弦**：乐队伴奏场景，生成高音1–3弦上的三和弦压缩指型


### 示例输出

**C 大调 R&B 进阶 `4-5-3-6-2-5-1`**（Fmaj7 G9 Em7 Am7 Dm7 G9 Cmaj7）

![C大调 RnB 进阶编配](assets/02-Cmajor-rnb-4536251.png)

**E 大调 `1-5-6-4` 中间把位**（E B C#m A，5–9 品区间）

![E大调中间把位编配](assets/04-Emajor-1564-middle.png)

**G 大调 `1-6-4-5` 小型三和弦**（G Em C D，高音1–3弦乐队伴奏指型）

![G大调小型三和弦编配](assets/05-Gmajor-1645-smalltriad.png)

### 安装

AI Musician Skills 是一组围绕 `SKILL.md` 组织的可复用技能包。每个包含
`SKILL.md` 的目录都是一个可安装单元；当前仓库提供的技能是
`guitar-arrange-skill`。安装时请保留完整目录结构，不要只复制 `SKILL.md`，
因为技能依赖 `references/`、`resources/`、`scripts/` 和 `agents/` 中的内容。

#### Codex 推荐安装方式

最简单的方式是把仓库链接交给 Codex，并让它安装完整技能目录：

<https://github.com/jassary08/AI-Musician-Skills.git>

推荐提示词：

```text
请从这个仓库安装 Codex skills：
https://github.com/jassary08/AI-Musician-Skills.git

请把仓库中包含 SKILL.md 的完整技能文件夹安装到我的 Codex skills 目录中。
不要只复制 SKILL.md。
```

如果只安装单个技能，请明确说明技能名：

```text
只安装这个仓库里的 guitar-arrange-skill：
https://github.com/jassary08/AI-Musician-Skills.git

请保留完整目录结构，不要只复制 SKILL.md。
```

安装后，请开启一个新的 Codex 会话，然后自然描述任务，例如：

```text
把 E 大调 1-5-6-3-4-1-2-5 编配成吉他版。
给我 C 大调 R&B 进阶 4-5-3-6-2-5-1 的可弹指法和和弦图。
```

#### 使用安装脚本

```bash
git clone https://github.com/jassary08/AI-Musician-Skills.git
cd AI-Musician-Skills
./install.sh          # 同时安装到 Claude Code 和 Codex CLI（软链接）
```

```bash
./install.sh --target claude   # 只装 Claude Code
./install.sh --target codex    # 只装 Codex CLI
./install.sh --uninstall       # 卸载
```

装完后重启 Agent 会话，技能即生效。

#### 手动安装

复制完整技能目录到 Codex skills 目录：

```bash
git clone https://github.com/jassary08/AI-Musician-Skills.git
cd AI-Musician-Skills
mkdir -p ~/.codex/skills
cp -R guitar-arrange-skill ~/.codex/skills/
```

或者手动软链接完整技能目录：

```bash
mkdir -p ~/.codex/skills
ln -s "$PWD/guitar-arrange-skill" ~/.codex/skills/guitar-arrange-skill
```

### 使用方式

Agent 会根据 `SKILL.md` 自动识别并调用（触发词如"帮我安排吉他指法"、"编配成吉他版"、"推荐变调夹"、"给我中间把位"、"小型三和弦"）。也可以直接跑脚本：

```bash
# Agent 传入具体和弦（推荐方式）
python guitar-arrange-skill/scripts/compose_guitar.py \
  --chords "E B C#m G#m A E F#m B" \
  --key "E major" --style pop --user-level intermediate --pretty

# 中间把位
python guitar-arrange-skill/scripts/compose_guitar.py \
  --chords "E B C#m A" --key "E major" --position-range "5-9" --pretty

# 小型三和弦（高音三根弦）
python guitar-arrange-skill/scripts/compose_guitar.py \
  --chords "G Em C D" --key "G major" --small-triad-strings "3,4,5" --pretty

# 导出和弦图 PNG
python guitar-arrange-skill/scripts/compose_guitar.py \
  --chords "Fmaj7 G9 Em7 Am7 Dm7 G9 Cmaj7" --key "C major" --style rnb \
  --diagram-png-output /tmp/chords.png --pretty
```

支持风格：`pop` `rock` `rnb` `blues` `funk`

---

## 路线图

| # | 技能 | 状态 |
|---|---|---|
| 1 | `guitar-arrange-skill` — 变调夹、把位、指法、和弦图 | ✅ 已发布 |
| 2 | 和声分析 — 罗马数字级数、和声功能、终止式 | 🔜 计划中 |
| 3 | 钢琴把位 — shell voicing、开放排列、重配和声 | 🔜 计划中 |
| 4 | 贝斯线 — 根据和弦谱生成 walking bass、律动型 | 🔜 计划中 |
| 5 | 鼓组律动 — 根据段落风格给出律动建议 | 🔜 计划中 |

---

## 目录结构

```
AI-Musician-Skills/
  README.md
  install.sh                     ← 安装脚本
  assets/                       ← 示例输出图
  guitar-arrange-skill/
    SKILL.md                     ← Agent 指令文档
    agents/openai.yaml           ← Agent 注册元数据
    resources/                   ← 风格卡、规则文件、和弦数据库
    scripts/                     ← Python 入口脚本
```

## 相关项目

- **AI-ChordCraft** — <https://github.com/jassary08/AI-ChordCraft>
