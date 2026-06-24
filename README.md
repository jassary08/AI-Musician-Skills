# AI Musician Skills（AI 音乐人技能集）

> 一套面向 LLM Agent 的技能(skills),专门帮真正玩音乐的人搞定"扒谱"里最枯燥又最难的环节:
> 把一段和弦进行,变成你这个水平、这个风格实际弹得出来的东西。

市面上有不少付费工具能直接给你打印一张和弦谱——但**原调、原把位**的和弦谱,对业余爱好者来说往往根本按不动。真正有意思的问题不是"**拿到**和弦",而是"**把这些和弦变成我这个水平、我这个风格弹得出来的东西**"。这一步,正是这套技能要解决的。

这套技能设计成可以装进 LLM Agent 运行时(Claude / Codex 的 agent skills)。Agent 读取技能的 `SKILL.md`,然后把附带的 Python 脚本当工具调用。你也可以直接在终端里运行这些脚本。

> **当前版本聚焦一个技能:`guitar-arrange-skill`(吉他和弦指法 / 编配)。**
> 这是整套构想里最先打磨成熟的一块。更多编曲辅助技能(钢琴、贝斯、鼓组、和声分析)正在路上——见下方[路线图](#技能路线图)。


## 这个技能做什么

```
  一串和弦 / 一句自然语言请求
          │
          ▼
  ┌────────────────────┐    "把它变成我弹得出来的"
  │ guitar-arrange-skill│ ── 变调夹选择、实际弹奏调、
  └────────────────────┘    匹配你水平和风格的把位/指法、和弦图 PNG
          │
          ▼
   主旋律谱 · ChordPro · 练习用纯文本 · 和弦图
```

`guitar-arrange-skill` 解决的是吉他手真正的痛点:**变调夹怎么选、实际弹哪个把位、什么指法既好按又对味**。
它**完全基于文本输入**工作(一串和弦,或一句自然语言请求),不需要 GPU,不需要音频。


## 安装

技能目录是自包含的(`SKILL.md` + `scripts/` + `agents/openai.yaml`),
遵循 [Agent Skills](https://agentskills.io) 标准,所以同一个文件夹可以同时装进
Claude Code 和 Codex CLI。

### 一键安装(推荐)

```bash
git clone https://github.com/jassary08/AI-Musician-Skills.git
cd AI-Musician-Skills
./install.sh              # 把技能同时装进两个运行时(软链接方式)
```

软链接安装会让已安装的技能随着仓库 `git pull` 自动保持同步。常用参数:

```bash
./install.sh --target claude   # 只装 Claude Code (~/.claude/skills/)
./install.sh --target codex     # 只装 Codex CLI ($CODEX_HOME/skills/)
./install.sh --copy             # 复制一份快照,而不是软链接
./install.sh --uninstall        # 移除已安装的技能/链接
```

装完后重启你的 agent(或开一个新会话),它才会扫描到新目录。

### 手动安装

一个技能就是一个含 `SKILL.md` 的目录;把它丢进运行时的 skills 文件夹即可:

| 运行时 | 个人目录 | 显式调用 |
|---|---|---|
| **Claude Code** | `~/.claude/skills/guitar-arrange-skill/` | `/guitar-arrange-skill` |
| **Codex CLI** | `~/.codex/skills/guitar-arrange-skill/`(即 `$CODEX_HOME/skills/`) | `/use guitar-arrange-skill` |

对 Claude Code,你也可以按项目安装:把技能放到所在仓库的
`.claude/skills/guitar-arrange-skill/` 下即可。

```bash
# 示例:手动把技能软链接进 Claude Code
mkdir -p ~/.claude/skills
ln -s "$PWD/guitar-arrange-skill" ~/.claude/skills/guitar-arrange-skill
```

调用是隐式的——agent 会根据 `SKILL.md` 里的描述自动选用技能(触发语句如
"写吉他和弦"、"推荐变调夹"、"改编成吉他版"、"挑把位/指法"、"画和弦图")。
你也可以用技能名显式调用。

## 技能详情:`guitar-arrange-skill`

把一段和弦进行,或一句自然语言请求,变成一份**可弹奏**的吉他编配:

- 自动选择变调夹(0–5 品),落到容易按的开放和弦把位。
- 按水平过滤:初学者路径避开横按;进阶路径在合适处用更丰富的把位。
- 3,300+ 和弦指法, 并标注了常用度、风格契合度和可弹性。
- 支持风格:`pop`、`rock`、`rnb`、`blues`、`funk`。
- 导出:结构化 JSON、小节网格、主旋律谱、纯文本练习单、ChordPro(`.cho`),以及 PNG 吉他和弦图。

入口:`guitar-arrange-skill/scripts/compose_guitar.py`(自然语言请求),
`guitar-arrange-skill/scripts/arrange_guitar.py`(固定进行)。

## 把位数据:成熟度说明

吉他编配器内置的把位数据库源自
[tombatossals/chords-db](https://github.com/tombatossals/chords-db)(MIT 许可)。
数据已经过重新格式化、标注和建立索引,但大部分条目仍标记为
`review_status: external_import_needs_review`(待人工复核)。已人工确认的把位标记为
`status: preferred` 或 `status: approved`。你可以编辑
`resources/voicing_db/overlays/commonness_annotations.json`,把你信任的把位提升等级。

## 技能路线图

`guitar-arrange-skill` 是这套构想里最先成熟的一块。后续会陆续补上更多**编曲辅助**技能,
最终目标是一整套"把灵感变成各乐器可弹奏谱面"的 agent 工具链:

| # | 技能 | 状态 |
|---|-------|--------|
| 1 | `guitar-arrange-skill` —— 变调夹、把位、主旋律谱、ChordPro、PNG | ✅ 已发布 |
| 2 | 和声分析技能 —— 罗马数字级数、和声功能、终止式 | 🔜 计划中 |
| 3 | 钢琴把位技能 —— shell voicing、开放排列、重配和声 | 🔜 计划中 |
| 4 | 贝斯线技能 —— 根据和弦谱生成 walking bass、律动型 | 🔜 计划中 |
| 5 | 鼓组律动技能 —— 根据段落给出风格化的律动建议 | 🔜 计划中 |

## 目录结构

```
AI-Musician-Skills/
  README.md
  LICENSE
  THIRD_PARTY_LICENSES.md
  install.sh                     ← 把技能装进 Claude Code / Codex
  examples/                      ← 真实生成的输出,建议从这里开始看
  guitar-arrange-skill/
    SKILL.md                     ← agent 指令文档
    agents/openai.yaml           ← agent 注册元数据
    references/                  ← schema、编配规则
    resources/                   ← 风格卡、规则文件、把位数据库
    scripts/                     ← 可运行的 Python 入口
```

## 相关项目

- **AI-ChordCraft(demo)** —— 催生了这套技能集的、由 LLM 编排的音频扒谱流水线。
  需要 GPU;仅开源代码。
  <https://github.com/jassary08/AI-ChordCraft>
