---
name: harmony-chart-skill
description: "Analyze chord progressions and render compact bar-chart lead sheets. Use when the user asks to analyze harmony, roman numerals, chord functions, cadence, key-centered progression, or create a visual measure chart from chords."
---

# Harmony Chart Skill

## Purpose

Use this skill to analyze a chord progression from either a supplied progression or an audio file.

For standalone use, prefer text inputs (`key`, `chords`, `bars`, `progression`, or `degrees`). This skill does not run SongFormer or perform lyrics ASR. In audio mode it calls AI-ChordCraft's chord-recognition helper, estimates key/tempo, maps chords onto measures, then returns:

- normalized chord progression
- Roman numeral analysis
- harmonic function labels
- cadence / loop notes
- compact measure chart data
- optional HTML visualization

## Inputs

Minimal input:

```json
{
  "key": "C major",
  "chords": ["C", "Am", "F", "G"]
}
```

Bar input:

```json
{
  "key": "E minor",
  "bars": [
    {"bar": 1, "chord": "Em7"},
    {"bar": 2, "chord": "Am7"},
    {"bar": 3, "chord": "B7"},
    {"bar": 4, "chord": "Em7"}
  ]
}
```

Audio input:

```json
{
  "audio_path": "/path/to/song.mp3",
  "chord_engine": "plkd-btc",
  "fallback_chord_engine": "essentia",
  "output_html": true
}
```

Supported optional fields:

- `title`
- `section`
- `columns`
- `time_signature`
- `style_hint`
- `output_html`
- `progression` / `degrees`, such as `1645` or `1-6-4-5`

Read `references/schema.md` before changing the input or output shape.

## Workflow

1. Normalize chord symbols and key spelling.
2. If an audio path is provided, run chord recognition and estimate key/tempo.
3. Map chord events to measures using BPM and meter. Use 4/4 when no reliable meter is available.
4. If the user provides degree notation such as `1645`, convert it to diatonic chords in the given key.
5. Convert each chord root to a scale-degree interval relative to the key.
6. Infer Roman numerals from key mode and chord quality.
7. Add harmonic function labels: tonic, predominant, dominant, modal color, passing/borrowed.
8. Detect simple cadences and common loops.
9. Build a bar grid using 4 columns by default.
10. Return JSON for programmatic use and HTML when requested.

## Script

```bash
python scripts/analyze_harmony.py --input-json '{"key":"C major","chords":["C","Am","F","G"],"output_html":true}' --pretty
```

Degree progression:

```bash
python scripts/analyze_harmony.py --input-json '{"key":"G major","progression":"1645","output_html":true}' --pretty
```

Write HTML:

```bash
python scripts/analyze_harmony.py --input-json '{"key":"E minor","chords":["Em7","Am7","B7","Em7"],"output_html":true}' --html-output /tmp/harmony-chart.html --pretty
```

Audio to measure chart:

```bash
CHORDCRAFT_PROJECT_ROOT=/path/to/ChordCraft-Demo \
python scripts/analyze_harmony.py --audio /path/to/song.mp3 --html-output /tmp/harmony-chart.html --pretty
```

## Output

The script returns:

- `summary`
- `bars`
- `progression_text`
- `roman_text`
- `functions_text`
- `cadences`
- `html`

## Constraints

- Standalone text mode has no AI-ChordCraft runtime dependency.
- Audio mode depends on an AI-ChordCraft checkout and its local pseudo-labeling + selective knowledge-distillation ACR runtime. Set `CHORDCRAFT_PROJECT_ROOT` when the skill is installed outside the AI-ChordCraft repository. Prefer `plkd-btc`; use Essentia only as fallback.
- If the key is missing, state that Roman analysis is approximate or use `C major` only as a fallback.
- Prefer compact, readable analysis over exhaustive jazz theory.
- Keep visualization measure-based, not timeline-based.
