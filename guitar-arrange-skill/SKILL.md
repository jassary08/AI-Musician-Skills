---
name: guitar-arrange-skill
description: "Turn natural-language music requests into playable guitar arrangements. Use when the user asks to arrange a chord progression (including numeric degree notation like 1-5-6-4), pick voicings/fingerings, target a fret position (middle/high/low), comp small triads on specific strings, adapt to skill level or style, recommend a capo, render chord-diagram PNGs, or produce ChordPro."
---

# Guitar Arrange Skill

## Purpose

Turn a natural-language music request into a playable guitar voicing/fingering arrangement.

The core design is a three-step pipeline where **you (the agent) own the
musical decisions** and the script owns the mechanical arrangement:

1. **Intent understanding (agent).** Read the request and resolve it into a
   concrete, ordered chord list. This is where degree notation, style coloring,
   12-bar templates, and borrowed chords are decided — by you, using music
   theory and the style cards, not by brittle regex in the script.
2. **Mechanical arrangement (script).** Hand the concrete chords plus explicit
   parameters to `scripts/compose_guitar.py` via `--chords`. The script does
   only deterministic work: voicing selection, position filtering, small-triad
   computation, capo transposition, voice-leading path search, and exports.
3. **Review (agent).** Inspect the arranged voicings for commonness,
   playability, and whether every user requirement was met. Fix or re-run if
   not. See "Agent Review".

Do not generate right-hand accompaniment, drum/bass parts, full tablature, or
exact original-song restoration in this skill.

## Step 1 — Resolve Intent To Concrete Chords

Before calling the script, convert the request into an explicit chord list.
You decide the chords; the script never guesses them.

- **Numeric degrees → chords.** `E 大调的 1-5-6-3-4-1-2-5` →
  `E B C#m G#m A E F#m B`. Use the key's diatonic triads; spell chords the way
  the key implies (`G#m` in E major, not `Abm`).
- **Style coloring.** For rnb/funk/jazz-leaning requests, add the colors the
  user asked for (maj7, m7, 9, 13, sus, slash) by consulting
  `resources/style_cards/{style}.json`. `C 大调 RnB 进阶 4-5-3-6-2-5-1` might
  become `Fmaj7 G9 Em7 Am7 Dm7 G9 Cmaj7`. Preserve the degree count and order
  unless the user asked to add or substitute chords.
- **Templates.** `A 小调 blues 经典 12 小节` → the 12-bar form spelled out as
  12 ordered chords, e.g. `Am7 Am7 Am7 Am7 Dm7 Dm7 Am7 Am7 E7 Dm7 Am7 E7`.
- Keep the chords exactly as you intend them — the script arranges what it is
  given, one voicing per chord, in order.

Read `resources/style_cards/{style}.json` for harmony vocabulary and coloring
guidance. Read `references/arrangement-rules.md` for capo/voicing/validation
rules.

## Step 2 — Call The Script With Explicit Chords

Pass the resolved chords and explicit parameters. The script applies no degree
parsing, no template generation, and no genre coloring — it arranges exactly
what you give it.

```bash
python scripts/compose_guitar.py \
  --chords "E B C#m G#m A E F#m B" \
  --key "E major" --style pop --user-level intermediate --pretty
```

Flags:

- `--chords` (required): the concrete progression, e.g. `"G Em C D"` or
  `"Cmaj7 Am7 Dm7 G7"`. Repeat chords to spell a full bar count (12-bar blues).
- `--key`: e.g. `"G major"`, `"A minor"`. Used for degree labels and accidentals.
- `--style`: `pop | rock | rnb | blues | funk`.
- `--user-level`: `beginner | intermediate`.
- `--capo N` / `--capo-policy`: **set a capo only when the user is an explicit
  beginner or explicitly asks for one.** Omit both to keep `capo == 0`.
- `--position-range "5-9"`: hard-restrict voicings to a fret window
  (middle ≈ 5-9, high ≈ 10-15, low/open ≈ 0-3).
- `--small-triad-strings "3,4,5"`: compute compact triads on the given strings
  (`3,4,5` = G/B/e, `2,3,4` = D/G/B). Best for band comping on top strings.
- `--known-chords`, `--bpm`, `--time-signature`, `--title`, `--goal`: optional.

A legacy natural-language mode (`compose_guitar.py '...'`) still exists for
quick experiments, but the explicit `--chords` path is the supported flow
because it keeps musical judgment in your hands.

## Supported Styles

Supported release styles are exactly `pop`, `rock`, `rnb`, `blues`, and `funk`.

## Scenario Routing

Use these routes to decide which files to read and which constraints must be enforced for common user requests.

### Numeric Degree Progression

Use when the user describes a progression as scale-degree numbers such as
`1-5-6-3-4-1-2-5` or `4-5-3-6-2-5-1` together with a key.

Read:

- `resources/style_cards/{style}.json` (for any requested coloring)
- `resources/voicing_db/overlays/curated_additions.json`

Do:

- **you** convert each number to a diatonic chord in the stated key
  (e.g. in E major, `1-5-6-3` → `E B C#m G#m`), spelling chords as the key
  implies, then pass them via `--chords`
- preserve the degree count and order exactly
- the script's enharmonic fallback still finds a DB shape if you spell a chord
  (`G#m`) that the DB stored under its equivalent (`Abm`)
- if a chord spelled by the key (e.g. `G#m`) is stored under its enharmonic
  (`Abm`) in the DB, the enharmonic fallback finds it while keeping the
  requested spelling for display

### Target Position / Fret Region

Use when the user asks for a specific region of the neck: `中间把位`,
`高把位`, `低把位`, `middle/high/low position`.

Read:

- `resources/rules/voicing_scoring_rules.json`
- `resources/voicing_db/source/chords_db_voicings.json`

Do:

- map the request to a fret window and pass it as `--position-range`:
  middle → `5-9`, high → `10-15`, low/open → `0-3`
- candidates are **hard-filtered** to that window; only if no voicing exists in
  range does the script fall back to the nearest shape and warn
- a position request overrides the usual open-shape preference, so expect
  movable/barre voicings and a higher average difficulty in mid/high positions

### Small Triads On Specific Strings

Use when the user wants compact triads on a string set, e.g.
`1,2,3弦上的小型三和弦`, `高音三根弦`, or band-comping triads.

Read:

- `scripts/compose_guitar.py` (`compute_small_triads`)

Do:

- pass the target strings as `--small-triad-strings`: `1,2,3弦` → `"3,4,5"`
  (G/B/e), `2,3,4弦` → `"2,3,4"` (D/G/B)
- triads are **computed algorithmically** from chord tones, not looked up: each
  string is assigned one chord tone, the fret span is kept ≤ 4, and fingers are
  assigned in ascending-fret order
- this is the right route for band guitarists who want to stay out of the
  bass/vocal range and comp on the top strings

### Capo Policy

Read:

- `resources/rules/capo_rules.json`
- `resources/rules/validation_rules.json`

Do:

- **only arrange a capo when the user is explicitly a beginner** (新手, 初学者,
  beginner, easy) **or explicitly asks for a capo** (变调夹, capo)
- intermediate/advanced requests default to `capo == 0` and use real fretted
  shapes; do not transpose to easier open keys for convenience
- for no-capo requests (不用变调夹, no capo) force `preferred_capo=0` and verify
  `capo == 0`
- for a fixed capo (capo 2, etc.) search only that position
- never override an explicit capo constraint; if playability suffers, warn

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
- `resources/voicing_db/overlays/curated_additions.json`

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

1. **Resolve intent (you).** Parse the request into key, style, section, user
   level, capo policy, target position, small-triad string set, and the
   **concrete chord list** (expand degree notation, apply style coloring, spell
   out 12-bar forms). Consult `resources/style_cards/{style}.json` for coloring.
2. **Call the script** with `--chords`, explicit parameters, and
   **always** `--diagram-png-output <path>`. The script:
   - selects voicings from `resources/voicing_db/source/chords_db_voicings.json`
     plus `overlays/curated_additions.json`, scored by
     `overlays/commonness_annotations.json` so common shapes beat rare ones;
   - hard-filters to `--position-range` when given;
   - computes triads algorithmically when `--small-triad-strings` is given;
   - transposes for a capo only when `--capo`/`--capo-policy` ask for one;
   - runs a dynamic-programming path search to smooth adjacent transitions;
   - exports JSON, bar grid, lead sheet, plain text, ChordPro, voicing objects,
     **and a PNG chord-sheet** (always rendered via `--diagram-png-output`).
3. **Review (you).** Check commonness, playability, and requirement
   satisfaction (see "Agent Review"). Re-run with tighter flags or swap a
   voicing if needed.
4. **Return the PNG to the user.** Present the chord-sheet image alongside a
   brief text summary (key, capo, chord names with shapes). The PNG is the
   primary deliverable — always include it at the end of the response.

## Agent Review

The script is deterministic and can produce arrangements that pass mechanical
validation but are still musically or ergonomically weak. After
`compose_guitar.py` returns and before presenting the result, review the output
and either approve it or correct it. Do not skip this step.

Read the script JSON (`voicings`, `display_chords`, `capo`, `play_as_key`,
`key`, `validation`) and the original request, then check three dimensions:

1. Fingering reasonableness
   - Every `frets`/`fingers` pair must be physically playable: no more than four
     fretting fingers, no impossible stretches across non-adjacent frets, barre
     marked only when one finger truly covers multiple strings.
   - Muted/open strings (`x`/`0`) must be consistent with the chord tones; a voicing
     should not mute a string that carries the root or essential color tone unless a
     deliberate rootless/slash choice is reported.
   - Beginner level: flag any avoidable barre or position above fret 3.
   - Confirm `position`/base fret matches the actual fret numbers in `shape`.

   - **Barre shape family (critical).** For any movable barre chord, only two shapes
     are idiomatic and widely played by real guitarists:
     - **E-shape**: root on string 6 (low E), barre across all six strings.
       Examples: Bm at 2fr = `224432`, F#m at 2fr = `244222`, G#m at 4fr = `466444`,
       C#m at 9fr = `9-11-11-9-9-9`.
     - **A-shape**: root on string 5 (A), barre across strings 5–1 (low E muted).
       Examples: C#m at 4fr = `x46654`, B at 2fr = `x24442`, F# at 2fr = `x24322`.
     - **G/C/D-shape barres are not used in practice** — they are physically awkward
       and almost never appear in real guitar playing. If the script outputs a barre
       whose root is on string 4 or higher (D/G/B/e), that is an awkward shape;
       reject it and re-run with `--position-range` adjusted or add a correct
       E/A-shape entry to `curated_additions.json`.

   - **Voicing idiomaticity**: For common chords (major, minor, dom7, maj7, m7) in
     open position (frets 0-3), verify the selected voicing is widely used. If a
     voicing has `commonness < 4` and no advanced-specific reason, check whether a
     more standard alternative (commonness ≥ 4, `status: preferred`) exists. Flag
     voicings that would surprise a typical guitarist. Reference points:
     - `Em` → `022000`, `E` → `022100`, `Am` → `x02210`, `A` → `x02220`
     - `C` → `x32010`, `Cmaj7` → `x32000` (not `332000` which is Cmaj7/G)
     - `G` → `320003`, `D` → `xx0232`, `Bm` → `x24432` or `x24442`
     - If a common shape is genuinely missing from the DB, add it to
       `resources/voicing_db/overlays/curated_additions.json` rather than inventing
       frets inline. All curated barre entries must be E-shape or A-shape.

2. User-requirement satisfaction
   - Key, style, section, difficulty, capo policy, bar count, target position,
     and small-triad string set match what the user asked. If the user fixed a
     capo or said no capo, verify `capo` obeys it. If the user asked for a fret
     region, verify the `position` values fall in it.
   - Confirm the chord count and harmonic order you resolved are preserved
     one-to-one in the output.
   - If the user asked for specific colors (maj7, m7, 9, 13, sus, slash), verify they
     are present; if a requested extension was simplified away, it must appear in
     `validation.warnings` with a reason.

3. Basic music-theory soundness
   - Each `display_chord` is a real, spellable chord and fits the stated key or a
     defensible borrowed/secondary function.
   - The chords you resolved from degree notation are coherent (e.g. a stated
     4-5-3-6-2-5-1 in C major maps to IV-V-iii-vi-ii-V-I → F-G-Em-Am-Dm-G-C).
   - Transposed `display_chords` under a capo sound the same as the original key:
     `play_as_key` + capo must equal the requested `key`.

If everything passes, state briefly that the arrangement was reviewed and approved.
If something fails, fix it conservatively: re-run `compose_guitar.py` with tighter
flags (explicit `--chords`/`--capo`/`--position-range`), or add a missing common
shape to `curated_additions.json`. Never hand-invent frets. Report every
correction and any residual compromise to the user.

## Script

The supported flow is explicit `--chords` mode. Always include
`--diagram-png-output <path>` — the PNG is the primary deliverable returned to
the user.

```bash
python scripts/compose_guitar.py \
  --chords "E B C#m G#m A E F#m B" \
  --key "E major" --style pop --user-level intermediate \
  --diagram-png-output /tmp/arrangement.png --pretty
```

Middle-position arrangement:

```bash
python scripts/compose_guitar.py \
  --chords "E B C#m A" --key "E major" --style pop \
  --user-level intermediate --position-range "5-9" \
  --diagram-png-output /tmp/arrangement.png --pretty
```

Small triads on the top three strings (G/B/e) for band comping:

```bash
python scripts/compose_guitar.py \
  --chords "G Em C D" --key "G major" --style pop \
  --user-level intermediate --small-triad-strings "3,4,5" --pretty
```

Beginner request that allows a capo:

```bash
python scripts/compose_guitar.py \
  --chords "C G Am F" --key "C major" --style pop \
  --user-level beginner --capo-policy auto --pretty
```

Render chord shapes to PNG, or write all export files:

```bash
python scripts/compose_guitar.py --chords "Am7 Dm7 E7" --key "A minor" \
  --style blues --diagram-png-output /tmp/chordcraft-diagrams.png --pretty
python scripts/compose_guitar.py --chords "Cmaj7 Am7 Fmaj7 G7" --key "C major" \
  --style rnb --export-dir /tmp/chordcraft-export --pretty
```

Render from an existing arrangement JSON, or a plain grid / all repeats:

```bash
python scripts/render_chord_diagrams.py --input-file /tmp/arrange-result.json --output /tmp/chordcraft-diagrams.png
python scripts/render_chord_diagrams.py --input-file /tmp/arrange-result.json --output /tmp/grid.png --layout grid
python scripts/render_chord_diagrams.py --input-file /tmp/arrange-result.json --output /tmp/all.png --show-all
```

Validate rule files after editing resources:

```bash
python scripts/validate_rules.py
```

A legacy natural-language mode (`compose_guitar.py '中文请求…'`) still works for
quick experiments and infers everything itself, but it relies on brittle
parsing; prefer the explicit `--chords` flow for real arrangements.

The arranger reads `resources/voicing_db/overlays/commonness_annotations.json`
and `curated_additions.json` and uses `commonness`, `status`, `styles`, and
`contexts` as scoring hints.

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
- `resources/voicing_db/overlays/curated_additions.json`: Hand-curated voicings that fill gaps in the source DB (e.g. the common partial-barre `B = x24442`). Add new shapes here, not in the source file.
- `resources/voicing_db/indexes/*.json`: Optional inspection indexes kept as release resources, not generated by runtime scripts.
- `scripts/compose_guitar.py`: Natural-language harmony planner and voicing arranger. Handles numeric degree notation, position targeting, algorithmic small triads, enharmonic voicing fallback, and level-gated capo policy.
- `scripts/render_chord_diagrams.py`: Dependency-free PNG renderer.
- `scripts/validate_rules.py`: Release resource validator.
