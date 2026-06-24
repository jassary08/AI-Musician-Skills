# Contributing to AI Musician Skills

Thanks for your interest. This project is a collection of agent skills for
musicians, and contributions are welcome — especially from people who actually
play.

## Ways to contribute

- **Curate voicings.** Most voicings in the database are tagged
  `external_import_needs_review`. If you play guitar, promoting good voicings to
  `preferred`/`approved` (and flagging bad ones) is the single most valuable
  contribution. Edit
  `guitar-arrange-skill/resources/voicing_db/overlays/commonness_annotations.json`.
- **Improve style cards.** The harmony/arrangement guidance lives in
  `guitar-arrange-skill/resources/style_cards/*.json`.
- **Add a new skill.** See the roadmap in the README (piano voicing, bassline,
  drum groove are planned).
- **Report issues.** Wrong Roman numerals, unplayable voicings, bad capo
  choices — open an issue with the exact `--input-json` you used.

## Development setup

Text mode needs only Python 3.10+ and the standard library. No pip install is
required to run the scripts.

```bash
git clone https://github.com/jassary08/AI-Musician-Skills
cd AI-Musician-Skills
python guitar-arrange-skill/scripts/validate_rules.py   # validate resource files
```

After editing voicing data, rebuild the index:

```bash
python guitar-arrange-skill/scripts/build_voicing_layers.py --pretty
```

## Conventions

- Keep scripts dependency-free for text mode (standard library only).
- Do not hand-edit `resources/voicing_db/source/chords_db_voicings.json`; it is
  imported source data. Put curation in the overlay file instead.
- Run `validate_rules.py` before opening a PR that touches resource files.
- New skills follow the existing layout: `SKILL.md`, `agents/openai.yaml`,
  `references/`, `scripts/`, and (if needed) `resources/`.

## Licensing

By contributing you agree your contributions are licensed under this
repository's MIT License. Imported third-party data must be compatible and
documented in `THIRD_PARTY_LICENSES.md`.
