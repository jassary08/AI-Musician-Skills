# Guitar Harmony Arrangement Schema

The skill has one user-facing input style: a natural-language request. The implementation may still return structured JSON for downstream systems, but users should not be asked to prepare a full structured payload.

Use `scripts/compose_guitar.py` for all arrangement requests.

## Minimal Input

```json
{
  "request": "写一段温暖的 C 大调流行副歌，适合初学者吉他弹唱，不要横按"
}
```

The CLI can also receive the request as a positional argument:

```bash
python scripts/compose_guitar.py '写一段温暖的 C 大调流行副歌，适合初学者吉他弹唱，不要横按' --pretty
```

## Natural-Language Information The Skill Can Infer

The request can mention:

- key, such as `C 大调`, `E minor`, `Bb major`
- style: `pop`, `rock`, `rnb`, `blues`, `funk`
- section: verse, chorus, bridge, intro, outro, 12-bar blues
- difficulty: beginner or intermediate
- capo policy: no capo, prefer capo, fixed capo
- source chords, such as `A E F#m D`
- harmony color, such as plain triads, seventh chords, maj7, 9, sus, add9
- output goals, such as chord diagrams or practice material

Automation may pass optional JSON fields such as `music_context`, `harmony_goal`, `guitar_constraints`, or `source_chords`, but these are convenience fields, not required user input.

## Output

`compose_guitar.py` returns a complete arrangement result:

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

## Exports

`exports` contains several output forms for different consumers:

- `progression_grid`: bar-level rows for compact display, including chord text and degree text.
- `lead_sheet`: frontend-friendly lead-sheet data, including key, style, section, capo, bars, and unique voicings.
- `practice_text`: plain-text sheet suitable for terminal preview, notes, or quick sharing.
- `chordpro_full`: ChordPro text that preserves the full planned bar progression.
- `voicing_summary`: compact list of selected shapes, frets, barres, difficulty, commonness, and annotation status.
- `chord_diagrams`: selected voicing objects used by the PNG renderer.
- `chord_diagrams_png`: optional PNG path when `--diagram-png-output` is provided.
- `files`: written export paths when `--export-dir` is provided.

## PNG Chord Diagram Export

```bash
python scripts/compose_guitar.py '写一段 E 小调经典 blues 十二小节，常用吉他弹法，不用变调夹' --diagram-png-output /tmp/blues.png --pretty
```

## File Export

Use `--export-dir` when the caller wants multiple artifacts instead of only stdout JSON:

```bash
python scripts/compose_guitar.py '把 C Am F G 这组和弦改成 R&B / Neo-soul 色彩，想要 maj7、m7 和 9 的感觉，难度中等' --export-dir /tmp/chordcraft-export --pretty
```

Generated files:

- `arrangement.json`: complete result, including `exports.files`.
- `lead_sheet.json`: frontend-friendly lead sheet.
- `practice_sheet.txt`: readable progression and voicing summary.
- `arrangement.cho`: ChordPro text.
- `voicing_summary.json`: compact selected-shape list.
