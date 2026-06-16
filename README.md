# AI Musician Skills

This directory is a standalone Codex skill package for harmony-centered music work. It can be published or installed independently from the AI-ChordCraft web application.

本目录是一个可独立发布的 Codex skill 项目，聚焦和声分析、吉他和弦编配、指法选择与可视化。它可以作为独立 skill 包安装，也可以继续被 AI-ChordCraft 作为内置能力调用。

## Skills

### `guitar-arrange-skill`

Create playable guitar harmony arrangements from natural-language requests, chord progressions, or analyzed song sections.

适用场景：

- 将 `1645`、`C Am F G` 等进行改写为可弹的吉他伴奏。
- 根据风格、难度、调性、capo 偏好选择 play-as 调与指法。
- 输出 lead sheet、ChordPro、练习文本和吉他和弦图 PNG。

Entry points:

- `guitar-arrange-skill/SKILL.md`
- `guitar-arrange-skill/scripts/compose_guitar.py`
- `guitar-arrange-skill/scripts/arrange_guitar.py`
- `guitar-arrange-skill/scripts/render_chord_diagrams.py`

Example:

```bash
cd AI-Musician-Skills/guitar-arrange-skill
python scripts/compose_guitar.py \
  --input-json '{"request":"写一段温暖的 C 大调流行副歌，适合初学者吉他弹唱，不要横按"}' \
  --diagram-png-output /tmp/chordcraft-diagrams.png \
  --pretty
```

### `harmony-chart-skill`

Analyze chord progressions and render compact measure charts with Roman numerals, harmonic functions, cadence notes, and optional HTML output.

适用场景：

- `key + chords`，例如 `C major + C Am F G`
- `key + bars`，例如每小节一个和弦
- `key + progression/degrees`，例如 `C major + 1645`
- 可选音频模式：需要额外配置 AI-ChordCraft 项目根目录与本地和弦识别运行时

Entry points:

- `harmony-chart-skill/SKILL.md`
- `harmony-chart-skill/scripts/analyze_harmony.py`

Example:

```bash
cd AI-Musician-Skills/harmony-chart-skill
python scripts/analyze_harmony.py \
  --input-json '{"key":"C major","progression":"1645","output_html":true}' \
  --html-output /tmp/harmony-chart.html \
  --pretty
```

## Package Layout

```text
AI-Musician-Skills/
  README.md
  guitar-arrange-skill/
    SKILL.md
    agents/openai.yaml
    references/
    resources/
    scripts/
  harmony-chart-skill/
    SKILL.md
    agents/openai.yaml
    references/
    scripts/
```

## Installation

For local Codex use, install either skill directory directly or copy the entire package into your personal skills location, depending on the target installer.

Each skill is self-contained around its own `SKILL.md`. The guitar arranger ships its voicing database and rule resources. The harmony chart skill works standalone for text/chord inputs; audio mode requires an AI-ChordCraft checkout.

## Audio Mode Boundary

`harmony-chart-skill` does not bundle structure recognition, lyrics ASR, or ACR model weights. For audio input, set:

```env
CHORDCRAFT_PROJECT_ROOT=/path/to/ChordCraft-Demo
CHORDCRAFT_ACR_MODEL_DIR=/path/to/pseudo-label-kd-acr-runtime
```

When these are not configured, use `key`, `chords`, `bars`, or `progression` inputs instead.

## Release Notes

- Do not publish Python `__pycache__` files.
- Do not remove `resources/voicing_db/source/chords_db_voicings.json`; it is required by the guitar arranger.
- Check third-party data and model licenses before redistributing this package.
