# Guitar Harmony Arrangement Schema

The skill now has two input levels:

1. Broad composition input: natural-language request plus optional constraints.
2. Deterministic realization input: explicit chord progression for capo and voicing selection.

Use `scripts/compose_guitar.py` for broad requests. Use `scripts/arrange_guitar.py` only when the chord progression is already fixed.

## Broad Input

Minimal input:

```json
{
  "request": "写一段温暖的 C 大调流行副歌，适合初学者吉他弹唱，不要横按"
}
```

Full input:

```json
{
  "request": "我有 C - Am - F - G，帮我改得更 R&B 一点，但不要太难",
  "source_chords": ["C", "Am", "F", "G"],
  "music_context": {
    "key": "C major",
    "style": "rnb",
    "section": "chorus",
    "bar_count": 4,
    "time_signature": "4/4",
    "tempo": 88
  },
  "harmony_goal": {
    "mood": "warm",
    "energy": "medium",
    "color_level": "colorful",
    "tension": "medium"
  },
  "guitar_constraints": {
    "user_level": "intermediate",
    "capo_policy": "no_capo",
    "preferred_capo": null,
    "allow_barre": true,
    "prefer_common_voicings": true,
    "known_chords": []
  },
  "output": {
    "include_diagrams": true,
    "include_degrees": true,
    "include_chordpro": true,
    "language": "zh-CN"
  }
}
```

## Broad Input Fields

- `request`: Natural-language user intent. This is the only required field for broad composition.
- `source_chords`: Optional fixed or seed progression. If present, the planner may preserve or lightly recolor it.
- `music_context.key`: Optional key, such as `C major`, `E minor`, `Bb major`.
- `music_context.style`: `pop`, `rock`, `rnb`, `blues`, `funk`, or omitted for inference.
- `music_context.section`: `intro`, `verse`, `pre_chorus`, `chorus`, `bridge`, `interlude`, `outro`, `12bar`, or omitted.
- `music_context.bar_count`: Optional target length.
- `harmony_goal.color_level`: `plain`, `light`, or `colorful`.
- `guitar_constraints.user_level`: `beginner` or `intermediate`.
- `guitar_constraints.capo_policy`: `auto`, `no_capo`, `prefer_capo`, or `fixed`.
- `guitar_constraints.preferred_capo`: Integer capo position when fixed.

Top-level aliases are accepted for backward compatibility:

- `key`, `style`, `section`, `bar_count`, `time_signature`, `tempo`, `bpm`
- `chords` as an alias of `source_chords`
- `user_level`, `preferred_capo`, `capo_policy`, `known_chords`

## Broad Output

`compose_guitar.py` returns the normal arranger output plus a `composition` block:

```json
{
  "composition": {
    "request": "写一段 E 小调经典 blues 十二小节，常用吉他弹法，不用变调夹",
    "source": "template",
    "template": "minor_12_bar_blues",
    "planned_chords": ["Em7", "Em7", "Em7", "Em7", "Am7", "Am7", "Em7", "Em7", "B7", "Am7", "Em7", "B7"],
    "arranger_chords": ["Em7", "Am7", "B7"],
    "music_context": {
      "key": "E minor",
      "style": "blues",
      "section": "chorus",
      "bar_count": 12,
      "color_level": "light",
      "capo_policy": "no_capo"
    }
  },
  "capo": 0,
  "key": "E minor",
  "bpm": 92,
  "time_signature": "4/4",
  "section": "chorus",
  "style": "blues",
  "play_as_key": "E minor",
  "display_chords": ["Em7", "Am7", "B7"],
  "voicings": [],
  "exports": {
    "progression_grid": {},
    "lead_sheet": {},
    "practice_text": "",
    "chordpro_full": "",
    "voicing_summary": []
  }
}
```

`planned_chords` preserves the full bar-level progression. `arranger_chords` is the compact progression used for unique voicing selection when repeated bars would only duplicate chord diagrams.

## Diverse Exports

`exports` intentionally contains several output forms for different consumers:

- `progression_grid`: bar-level rows for compact display, including chord text and degree text.
- `lead_sheet`: structured lead-sheet data for frontend rendering, including key, style, section, capo, bars, and unique voicings.
- `practice_text`: plain-text sheet suitable for terminal preview, notes, or quick sharing.
- `chordpro_full`: ChordPro text that preserves the full planned bar progression.
- `voicing_summary`: compact list of selected shapes, frets, barres, difficulty, commonness, and annotation status.
- `chord_diagrams`: selected voicing objects used by the PNG renderer.
- `chord_diagrams_png`: optional PNG path when `--diagram-png-output` is provided.
- `files`: written export paths when `--export-dir` is provided.

Example `progression_grid`:

```json
{
  "columns": 4,
  "text": "| Em7 | Em7 | Em7 | Em7 |\n| Am7 | Am7 | Em7 | Em7 |\n| B7 | Am7 | Em7 | B7 |",
  "degrees_text": "| i7 | i7 | i7 | i7 |\n| iv7 | iv7 | i7 | i7 |\n| V7 | iv7 | i7 | V7 |"
}
```

Example `lead_sheet.bars` item:

```json
{
  "bar": 1,
  "section": "chorus",
  "chord": "Em7",
  "degree": "i7"
}
```

## Deterministic Realization Input

Use this only when the chord progression is already decided:

```json
{
  "task": "guitar_arrange",
  "key": "A major",
  "bpm": 92,
  "time_signature": "4/4",
  "section": "chorus",
  "style": "pop",
  "user_level": "beginner",
  "goal": "适合弹唱，避免横按",
  "chords": ["A", "E", "F#m", "D"],
  "preferred_capo": null,
  "known_chords": []
}
```

## PNG Chord Diagram Export

Broad request:

```bash
python scripts/compose_guitar.py --input-json '{"request":"写一段 E 小调经典 blues 十二小节，常用吉他弹法，不用变调夹"}' --diagram-png-output /tmp/blues.png --pretty
```

Fixed progression:

```bash
python scripts/arrange_guitar.py --input-json '{"key":"C major","style":"pop","section":"chorus","user_level":"intermediate","preferred_capo":0,"time_signature":"4/4","chords":["C","Am","F","G"]}' --diagram-png-output /tmp/1645.png --pretty
```

## File Export

Use `--export-dir` when the caller wants multiple artifacts instead of only stdout JSON:

```bash
python scripts/compose_guitar.py --input-json '{"request":"写一段 E 小调经典 blues 十二小节，常用吉他弹法，不用变调夹"}' --export-dir /tmp/chordcraft-export --pretty
```

Generated files:

- `arrangement.json`: complete result, including `exports.files`.
- `lead_sheet.json`: frontend-friendly lead sheet.
- `practice_sheet.txt`: readable progression and voicing summary.
- `arrangement.cho`: ChordPro text.
- `voicing_summary.json`: compact selected-shape list.
