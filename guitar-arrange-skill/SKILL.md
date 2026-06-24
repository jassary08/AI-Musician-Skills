---
name: guitar-arrange-skill
description: "Create playable guitar harmony arrangements from natural-language music requests. Use when the user asks to write guitar chords, reharmonize for guitar, recommend capo, convert to play-as chords, choose guitar voicings/fingerings, render guitar chord diagram PNGs, or produce ChordPro chord material."
---

# Guitar Arrange Skill

## Purpose

Use this skill to turn a natural-language music request into a playable guitar harmony arrangement.

This skill now has one user-facing arrangement entrypoint: `scripts/compose_guitar.py`. Users are expected to describe what they want in natural language; the script infers style, key, section, difficulty, capo policy, harmony color, and optional supplied chord progressions from that request.

This release scope is deliberately narrow:

- natural-language intent parsing
- harmony planning from style, mood, key, section, and difficulty
- harmony/style guidance
- capo and play-as chord conversion
- left-hand voicing/fingering selection
- ChordPro export
- lead-sheet/grid/text export
- PNG guitar chord diagram export

Do not generate right-hand accompaniment, drum/bass parts, full tablature, or exact original-song restoration in this skill.

## Input Style

Prefer plain natural language. Examples:

- `写一段温暖的 C 大调流行副歌，适合初学者吉他弹唱，不要横按`
- `把 A E F#m D 这组和弦改成更适合新手弹唱的吉他版本，可以用变调夹`
- `写一段 E 小调经典 blues 十二小节，常用吉他弹法，不用变调夹`
- `把 C Am F G 这组和弦改成 R&B / Neo-soul 色彩，想要 maj7、m7 和 9 的感觉，难度中等`

The CLI also accepts JSON for automation, but the JSON should normally contain a `request` string rather than forcing users to fill a full structured schema.

Supported release styles are exactly `pop`, `rock`, `rnb`, `blues`, and `funk`.

## Scenario Routing

Use these routes to decide which files to read and which constraints must be enforced for common user requests.

### New Guitar Progression

Use when the user asks to write or generate a new guitar chord progression without supplying a fixed progression.

Read:

- `resources/style_cards/{style}.json`
- `resources/rules/capo_rules.json`
- `resources/rules/voicing_scoring_rules.json`
- `resources/rules/playability_rules.json`
- `resources/rules/simplification_rules.json`
- `resources/rules/validation_rules.json`
- `resources/rules/practice_note_rules.json`
- `resources/voicing_db/source/chords_db_voicings.json`
- `resources/voicing_db/overlays/commonness_annotations.json`

Do:

- infer key, style, section, bar count, user level, capo policy, and color level from the request
- generate a progression from the deterministic style templates in `scripts/compose_guitar.py`
- choose capo and play-as chords according to the capo rules
- choose selected voicings from the voicing database plus overlay annotations
- return practice notes and exports requested by the user

### Given Progression, Make It More Guitar-Friendly

Use when the user supplies a progression such as `A E F#m D` and asks for easier guitar shapes, beginner playability, or capo conversion.

Read:

- `resources/rules/capo_rules.json`
- `resources/rules/playability_rules.json`
- `resources/rules/voicing_scoring_rules.json`
- `resources/voicing_db/source/chords_db_voicings.json`
- `resources/voicing_db/overlays/commonness_annotations.json`
- the inferred or requested `resources/style_cards/{style}.json`

Do:

- extract the user-supplied chord progression from natural language
- preserve the progression length and harmonic order unless the user explicitly asks to add passing chords or reharmonize with extra chords
- search capo positions unless the user asks for no capo or a fixed capo
- prefer open/common shapes for beginner users
- output both original sounding intent and selected play-as/display chords

### Given Progression, Add R&B / Neo-Soul Color

Use when the user supplies a progression and asks to make it more R&B, neo-soul, jazzy, colorful, maj7, m7, 9, 11, or 13.

Read:

- `resources/style_cards/rnb.json`
- `resources/rules/simplification_rules.json`
- `resources/rules/voicing_scoring_rules.json`
- `resources/rules/playability_rules.json`
- `resources/voicing_db/source/chords_db_voicings.json`
- `resources/voicing_db/overlays/commonness_annotations.json`

Do:

- preserve the input chord count and order by default
- colorize one-to-one unless the user explicitly asks for inserted passing chords, substitutions, or a longer reharmonization
- do not add an extra chord to a fixed progression without explicit permission
- examples of one-to-one colorization: `C Am F G` can become `Cmaj7 Am7 Fmaj7 G9`, `Cmaj9 Am9 Fmaj9 G13`, or a simpler playable variant depending on database coverage
- keep `style=rnb` and `user_level=intermediate` when the user asks for advanced or intermediate playing
- if a requested extension has no playable voicing, simplify conservatively and report the simplification in `validation.warnings`

### No Capo Or Fixed Capo

Use when the request says no capo, 不要变调夹, 不用变调夹, fixed capo, capo 2, or similar.

Read:

- `resources/rules/capo_rules.json`
- `resources/rules/validation_rules.json`

Do:

- for no-capo requests, set `capo_policy=no_capo` and force `preferred_capo=0`
- validate that the final result has `capo == 0`
- for fixed capo requests, only search the requested capo position
- do not override the user's capo constraint for convenience; if playability suffers, warn instead

### Beginner Versus Intermediate Playing

Use when the request mentions beginner, 新手, 初学者, easy, intermediate, 进阶, 中等, advanced, or similar.

Read:

- `resources/rules/playability_rules.json`
- `resources/rules/voicing_scoring_rules.json`
- `resources/voicing_db/overlays/commonness_annotations.json`

Do:

- beginner: strongly prefer open/common shapes, low difficulty, low position, no barre unless unavoidable
- intermediate: allow selected barre, movable, extended, and color voicings when style-appropriate
- always use database voicings; never invent frets or fingerings
- report unavoidable hard shapes or simplifications in `validation.warnings`

### Chord Diagram PNG Requested

Use when the user asks for 和弦图, 指法图, chord diagrams, PNG, or visual fingering output.

Read:

- selected voicing objects from `scripts/compose_guitar.py` output
- `scripts/render_chord_diagrams.py`

Do:

- render only selected database-backed voicings from `exports.chord_diagrams`
- do not draw guessed or formula-generated diagrams
- pass `--diagram-png-output` when running `scripts/compose_guitar.py`
- the PNG is a practice sheet by default: a header strip (key/capo/bpm/time/style), the ordered bar-by-bar progression with roman-numeral degrees, then the deduplicated chord shapes
- pass `--show-all` (or `--layout grid`) to `scripts/render_chord_diagrams.py` if the user wants every voicing in progression order or a plain diagram grid
- return the PNG path to the user

### ChordPro Or Practice Material Requested

Use when the user asks for ChordPro, lead sheet, practice sheet, 练习材料, or export files.

Read:

- `resources/rules/practice_note_rules.json`
- selected arrangement output from `scripts/compose_guitar.py`

Do:

- include `exports.chordpro_full` for full bar-level ChordPro
- include `exports.practice_text` for readable practice material
- use `--export-dir` when the user asks for files rather than only JSON

### Existing Arrangement JSON To Diagram

Use when the user already has an arrangement JSON and only wants diagrams rendered.

Read:

- the provided arrangement JSON
- `scripts/render_chord_diagrams.py`

Do:

- do not rerun harmony planning unless the user asks for a new arrangement
- render the existing selected voicings to PNG

## Workflow

1. Parse the natural-language request into key, style, section, bar count, difficulty, capo policy, known chords, and color level.
2. Preserve or lightly recolor user-mentioned chord progressions when they are present in the request.
3. If no chords are supplied, generate a progression from deterministic style templates.
4. Load the selected style card from `resources/style_cards/{style}.json`.
5. Search capo `0-5`; choose the play-as progression with the best guitar playability unless the user asks for no capo or a fixed capo.
6. Build a top-K voicing candidate pool from `resources/voicing_db/source/chords_db_voicings.json`.
7. Apply `resources/voicing_db/overlays/commonness_annotations.json` so canonical/common shapes beat rare imported shapes.
8. Run dynamic-programming path search across the progression to optimize adjacent chord transitions.
9. Export multiple output forms: JSON, bar grid, lead sheet, plain text, ChordPro, and selected voicing objects.
10. Render selected voicings to PNG when `--diagram-png-output` is provided.
11. Validate the result before returning it.

## Script

Use `scripts/compose_guitar.py` for all user-facing arrangement requests:

```bash
python scripts/compose_guitar.py '写一段温暖的 C 大调流行副歌，适合初学者吉他弹唱，不要横按' --pretty
```

Render selected chord shapes:

```bash
python scripts/compose_guitar.py '写一段 E 小调经典 blues 十二小节，常用吉他弹法，不用变调夹' --diagram-png-output /tmp/chordcraft-diagrams.png --pretty
```

Write all user-facing export files:

```bash
python scripts/compose_guitar.py '把 C Am F G 这组和弦改成 R&B / Neo-soul 色彩，想要 maj7、m7 和 9 的感觉，难度中等' --export-dir /tmp/chordcraft-export --pretty
```

Render from an existing arrangement JSON:

```bash
python scripts/render_chord_diagrams.py --input-file /tmp/arrange-result.json --output /tmp/chordcraft-diagrams.png
```

Render a plain diagram grid (no header/progression strip) or include every repeated voicing:

```bash
python scripts/render_chord_diagrams.py --input-file /tmp/arrange-result.json --output /tmp/grid.png --layout grid
python scripts/render_chord_diagrams.py --input-file /tmp/arrange-result.json --output /tmp/all.png --show-all
```

Validate rule files after editing resources:

```bash
python scripts/validate_rules.py
```

The arranger reads `resources/voicing_db/overlays/commonness_annotations.json` when present and uses `commonness`, `status`, `styles`, and `contexts` as scoring hints.

## Output

The composer returns:

- `composition`
- `exports.progression_grid`
- `exports.lead_sheet`
- `exports.practice_text`
- `exports.chordpro_full`
- `exports.voicing_summary`
- `title`
- `key`
- `bpm`
- `time_signature`
- `section`
- `style`
- `user_level`
- `capo`
- `play_as_key`
- `display_chords`
- `voicings`
- `style_guidance`
- `practice_notes`
- `validation`

`exports.chord_diagrams` contains the selected voicing objects. `exports.chord_diagrams_png` is populated only when a PNG output path is requested.

When `--export-dir` is provided, the composer writes:

- `arrangement.json`: complete machine-readable result
- `lead_sheet.json`: compact bar-level lead sheet for frontend rendering
- `practice_sheet.txt`: readable plain-text progression and voicing summary
- `arrangement.cho`: ChordPro material
- `voicing_summary.json`: selected voicing/fingering summary

## Constraints

- Do not invent fingerings. Use imported or curated voicings only.
- For beginner users, avoid barre chords unless no reasonable alternative exists.
- Preserve useful seventh/ninth/sus/slash colors for `rnb`, `blues`, and `funk` when the user's level allows it.
- Simplify extensions conservatively and report simplification in `validation.warnings`.
- Render diagrams only from selected database voicings; do not draw guessed shapes.
- Keep explanations concise and focused on chord playability.

## Release Resources

- `README.md`: User-facing overview and typical usage scenarios.
- `references/schema.md`: Input/output shape notes and example payloads.
- `references/arrangement-rules.md`: Capo, voicing, validation, and fallback rules.
- `resources/style_cards/*.json`: Five supported style cards, each containing harmony guidance, chord/voicing guidance, and scoring preferences.
- `resources/rules/*.json`: Machine-readable scoring, simplification, validation, and practice-note rules.
- `resources/voicing_db/source/chords_db_voicings.json`: Imported MIT source voicing database. Do not edit this by hand.
- `resources/voicing_db/overlays/commonness_annotations.json`: Editable commonness/style overlay used by the arranger.
- `resources/voicing_db/indexes/*.json`: Optional inspection indexes kept as release resources, not generated by runtime scripts.
- `scripts/compose_guitar.py`: Single natural-language harmony planner and voicing arranger.
- `scripts/render_chord_diagrams.py`: Dependency-free PNG renderer.
- `scripts/validate_rules.py`: Release resource validator.
