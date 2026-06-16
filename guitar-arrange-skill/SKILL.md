---
name: guitar-arrange-skill
description: "Create playable guitar harmony arrangements from natural-language music requests, chord progressions, or AI-ChordCraft song sections. Use when the user asks to write guitar chords, reharmonize for guitar, recommend capo, convert to play-as chords, choose guitar voicings/fingerings, render guitar chord diagram PNGs, or produce ChordPro chord material."
---

# Guitar Arrange Skill

## Purpose

Use this skill to turn a natural-language music idea, chord progression, or song section into a playable guitar harmony arrangement.

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

## Inputs

Broad input requires only:

- `request`

Optional broad fields:

- `source_chords`
- `music_context`
- `harmony_goal`
- `guitar_constraints`
- `output`

Fixed-progression input is still supported for deterministic realization:

- `key`
- `chords`
- `bpm`
- `time_signature`
- `section`
- `style`
- `user_level`
- `goal`
- `preferred_capo`
- `known_chords`

Supported release styles are exactly `pop`, `rock`, `rnb`, `blues`, and `funk`.

Read `references/schema.md` before changing input/output shape.

## Workflow

1. Parse the user request into key, style, section, bar count, difficulty, capo policy, and color level.
2. If `source_chords` or `chords` exist, preserve or lightly recolor them according to the style and color level.
3. If no chords are supplied, generate a progression from deterministic style templates.
4. Load the selected style card from `resources/style_cards/{style}.json`.
5. Search capo `0-5`; choose the play-as progression with the best guitar playability unless the user fixes/no-capo.
6. Build a top-K voicing candidate pool from `resources/voicing_db/source/chords_db_voicings.json`.
7. Apply `resources/voicing_db/overlays/commonness_annotations.json` so canonical/common shapes beat rare imported shapes.
8. Run dynamic-programming path search across the progression to optimize adjacent chord transitions.
9. Export multiple output forms: structured JSON, bar grid, lead sheet, plain text, ChordPro, and selected voicing objects.
10. Render selected voicings to PNG when `--diagram-png-output` is provided.
11. Validate the result before returning it.

## Scripts

Use `scripts/compose_guitar.py` for broad natural-language guitar harmony planning:

```bash
python scripts/compose_guitar.py --input-json '{"request":"写一段 E 小调经典 blues 十二小节，常用吉他弹法，不用变调夹"}' --pretty
```

Use `scripts/arrange_guitar.py` only when the progression is already fixed:

```bash
python scripts/arrange_guitar.py --input-json '{"task":"guitar_arrange","key":"A major","bpm":92,"time_signature":"4/4","section":"chorus","style":"pop","user_level":"beginner","goal":"适合弹唱，避免横按","chords":["A","E","F#m","D"]}' --pretty
```

Render selected chord shapes during broad composition:

```bash
python scripts/compose_guitar.py --input-json '{"request":"写一段温暖的 C 大调流行副歌，适合初学者吉他弹唱，不要横按"}' --diagram-png-output /tmp/chordcraft-diagrams.png --pretty
```

Write all user-facing export files during broad composition:

```bash
python scripts/compose_guitar.py --input-json '{"request":"写一段 E 小调经典 blues 十二小节，常用吉他弹法，不用变调夹"}' --export-dir /tmp/chordcraft-export --pretty
```

Render selected chord shapes during fixed arrangement:

```bash
python scripts/arrange_guitar.py --input-json '{"task":"guitar_arrange","key":"A major","bpm":92,"time_signature":"4/4","section":"chorus","style":"pop","user_level":"beginner","chords":["A","E","F#m","D"]}' --diagram-png-output /tmp/chordcraft-diagrams.png --pretty
```

Render from an existing arrangement JSON:

```bash
python scripts/render_chord_diagrams.py --input-file /tmp/arrange-result.json --output /tmp/chordcraft-diagrams.png
```

Validate rule files after editing resources:

```bash
python scripts/validate_rules.py
```

Build the layered voicing index after changing voicing databases:

```bash
python scripts/build_voicing_layers.py --pretty
```

Create or refresh the common-sense voicing annotation overlay:

```bash
python scripts/auto_annotate_voicings.py
```

The arranger reads `resources/voicing_db/overlays/commonness_annotations.json` when present and uses `commonness`, `status`, `styles`, and `contexts` as scoring hints.

## Output

The broad composer returns:

- `composition`
- `exports.progression_grid`
- `exports.lead_sheet`
- `exports.practice_text`
- `exports.chordpro_full`
- `exports.voicing_summary`
- all arranger fields below

The arranger returns:

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
- `exports`
- `validation`

`exports.chord_diagrams` contains the selected voicing objects. `exports.chord_diagrams_png` is populated only when a PNG output path is requested.

When `--export-dir` is provided, the broad composer writes:

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

- `references/schema.md`: Input/output schema and example payloads.
- `references/arrangement-rules.md`: Capo, voicing, validation, and fallback rules.
- `resources/style_cards/*.json`: Five supported style cards, each containing harmony guidance, chord/voicing guidance, and scoring preferences.
- `resources/rules/*.json`: Machine-readable scoring, simplification, validation, and practice-note rules.
- `resources/voicing_db/source/chords_db_voicings.json`: Imported MIT source voicing database. Do not edit this by hand.
- `resources/voicing_db/overlays/commonness_annotations.json`: Editable commonness/style overlay generated by `auto_annotate_voicings.py` and refined by the annotation UI.
- `resources/voicing_db/indexes/voicing_layers.json`: Complete generated index by chord family, quality, harmony tier, playability tier, release layer, voice-leading traits, style fit, and review priority.
- `resources/voicing_db/indexes/layer_indexes/*.json`: Split sidecar indexes for musical taxonomy, guitar playability, review pools, style fit, and voice-leading lookup.
- `resources/voicing_db/review/`: Optional human-review exports and inspection batches.
- `scripts/compose_guitar.py`: Broad natural-language harmony planner and main user-facing entrypoint.
- `scripts/arrange_guitar.py`: Deterministic capo/voicing arranger for fixed progressions.
- `scripts/auto_annotate_voicings.py`: Generates the first-pass commonness/style annotation overlay.
- `scripts/build_voicing_layers.py`: Builds the layered voicing index from the release voicing databases.
- `scripts/render_chord_diagrams.py`: Dependency-free PNG renderer.
- `scripts/validate_rules.py`: Release resource validator.
