# Guitar Chord Arrangement Rules

These rules define how the release arranger chooses capo, play-as chords, left-hand voicings, fallbacks, and validation. The machine-readable configuration is under `resources/rules/*.json`.

## Rule Layers

1. `capo_rules.json`: Searches capo positions and scores play-as progressions.
2. `voicing_scoring_rules.json`: Scores candidate left-hand voicings.
3. `playability_rules.json`: Defines beginner/intermediate constraints.
4. `simplification_rules.json`: Controls chord simplification and enharmonic choices.
5. `validation_rules.json`: Defines release checks and warning/failure thresholds.
6. `practice_note_rules.json`: Generates concise explanations.

## Capo Planner

Search capo `0-5` unless a valid `preferred_capo` is supplied. For each capo, transpose original sounding chords down by the capo interval to produce play-as chords.

Score each candidate with these priorities:

- Maximize playable open chord shapes.
- Maximize beginner-common shapes for beginner users.
- Respect `known_chords` from the user.
- Penalize missing voicings, barre chords, excessive capo height, slash chords, and complex extensions.
- Prefer a slightly higher capo when it removes a hard beginner barre chord such as `F#m`, `Bm`, or `F`.
- Warn when the user forces a poor `preferred_capo`.

Example:

`A - E - F#m - D`, beginner, pop, chorus:

- Capo 0 keeps `F#m`, a barre chord.
- Capo 2 gives `G - D - Em - C`, all open beginner shapes.
- Choose Capo 2.

## Voicing Planner

The planner should select voicings that are playable in context, not just dictionary defaults. It uses a top-K candidate pool plus dynamic programming path search so adjacent chord connections influence the final choice.

Voicing candidates come from the release source database plus an editable overlay:

- Source voicings: `resources/voicing_db/source/chords_db_voicings.json`.
- Commonness/style overlay: `resources/voicing_db/overlays/commonness_annotations.json`.

The arranger treats the source database as immutable imported data, then applies the overlay before scoring. Candidate selection order is:

1. Load source voicings.
2. Attach overlay fields such as `commonness`, `status`, `styles`, and `contexts`.
3. Score local playability, style fit, and overlay commonness.
4. Run adjacent-chord voice-leading path search.

`resources/voicing_db/indexes/voicing_layers.json` is an algorithmic index built from the source database. It does not replace the source database or overlay; it groups voicings into decision layers:

- chord layer: `family`, `quality`, `extensions`
- harmony tier:
  - `foundation`: major, minor, and power chords.
  - `core_color`: dominant7, minor7, major7, sus, add9, and sixth chords.
  - `extended_color`: 9/11/13, minor9, major9, and slash chords.
  - `special_altered`: diminished, half-diminished, and augmented chords.
- shape layer: `open`, `barre`, `partial`, `movable`, `modern_open`, `high_position`
- difficulty layer: `easy`, `medium`, `hard`
- playability tier:
  - `open_basic`: low-position open shapes suitable for first-pass release curation.
  - `practical_low_mid`: low/mid-position shapes with manageable fret span.
  - `movable_closed`: movable or barre shapes useful for transposition and style control.
  - `upper_position`: high-position shapes that need stronger musical intent.
  - `special_shape`: shapes that do not fit the main playability buckets.
- voice-leading layer: `bass_note`, `top_note`, `open_strings`, `fret_center`, `fret_span`
- style layer: numeric `style_fit` for `pop`, `rock`, `rnb`, `blues`, and `funk`
- review layer: `release_default`, `external_import_needs_review`, or other curation states
- review priority:
  - `p0_curated_release`: manually curated release defaults.
  - `p1_core_audit`: algorithmically selected core triad/power chord audit pool.
  - `p2_color_audit`: common seventh/sus/add/sixth color audit pool.
  - `p3_style_extension_audit`: style-specific extended-color audit pool.
  - `p4_backlog`: advanced, high-position, hard, or lower-priority shapes.
- release layer:
  - `release_core`
  - `core_candidate`
  - `color_candidate`
  - `style_extension_candidate`
  - `advanced_backlog`

Regenerate this index after changing either voicing database:

```bash
python scripts/build_voicing_layers.py --pretty
```

The builder also writes split sidecar indexes under `resources/voicing_db/indexes/layer_indexes/`:

- `manifest.json`: lists the sidecar files and their purpose.
- `musical_taxonomy.json`: family, quality, and harmony-tier indexes.
- `guitar_playability.json`: shape, difficulty, position, and playability-tier indexes.
- `release_review_pools.json`: release layer and review-priority indexes for curation.
- `style_fit.json`: style-fit indexes for `pop`, `rock`, `rnb`, `blues`, and `funk`.
- `voice_leading.json`: top-note and bass-note indexes for smoother adjacent chord selection.

Do not generate new chord shapes from chord formulas in the release pipeline. If coverage is missing, import another licensed source or add a manually reviewed voicing with provenance.

Beginner:

- Prefer exact open voicings.
- Avoid barre chords.
- Prefer difficulty `1-2`.
- Avoid large position jumps.
- Use simplified extensions when needed.

Intermediate:

- Allow selected barre chords.
- Prefer modern ringing voicings when style and progression fit.
- For G-family pop progressions, consider `G 320033`, `Dadd11 xx0233`, `Em7 022033`, `Cadd9 x32033`.
- Use smoother transitions when multiple voicings are available.

Voicing quality should consider:

- user level match
- style match
- open string resonance
- clear root / usable bass
- common hand shape
- fret span
- position
- barre count

## Voicing Path Search

For each display chord, keep the top `candidate_pool.top_k_per_chord` voicing candidates after local scoring. Then run a Viterbi-style dynamic program over the progression:

```text
best_score[i][current] =
  local_score(current)
  + max(best_score[i-1][previous] + transition_score(previous, current))
```

The transition score rewards:

- same string/fret fretted notes that can keep fingers anchored
- shared open strings when the style prefers ringing continuity
- same or stepwise top-note motion
- stepwise bass motion
- repeated shape for repeated chords

The transition score penalizes:

- large position jumps
- large fret-center movement
- same-finger long-distance movement
- switching into or out of barre chords, especially for beginners

Style cards may tune transition behavior through `transition_preferences`. For example, `pop` prefers open-string and top-note continuity, while `funk` allows more position movement and cares less about open-string sustain.

## Simplification

Simplification is allowed when it improves playability and the output reports it in warnings.

Recommended beginner simplifications:

- `maj7` -> major triad when no easy voicing exists.
- `m7` -> minor triad when no easy voicing exists.
- `sus2`, `sus4`, `add9` -> triad when the color tone makes the part too hard.
- slash chords -> drop bass note unless an easy voicing exists.
- diminished/augmented chords -> approximate only when the exact chord is not playable and the result is explicitly warned.

Do not simplify core major/minor identity unless no alternative exists.

## Validation

Before returning:

1. All required output fields must exist.
2. `display_chords` must align with original chord count.
3. Every display chord should have a voicing or a warning.
4. Beginner output should not contain barre chords unless unavoidable and warned.
5. ChordPro should be generated even if only as a progression draft.
6. PNG export should render only selected voicing objects from the database.

## Fallbacks

- Missing exact voicing: try simplified chord.
- Barre-heavy beginner result: retry another capo.
- Unsupported style: warn and use fallback scoring.
- Unsupported section: warn and keep the requested section label.
- Unsupported meter: return validation failure.
