# Harmony Chart Schema

## Input

```json
{
  "title": "string optional",
  "key": "C major",
  "section": "chorus optional",
  "time_signature": "4/4 optional",
  "columns": 4,
  "chords": ["C", "Am", "F", "G"],
  "progression": "1645 optional",
  "degrees": "1-6-4-5 optional",
  "bars": [
    {
      "bar": 1,
      "chord": "C",
      "time": "00:12 optional",
      "end": "00:16 optional"
    }
  ],
  "style_hint": "pop optional",
  "output_html": true
}
```

Use `bars`, `chords`, or `progression/degrees`. Priority is `bars` > `chords` > `progression/degrees`.

Audio mode input:

```json
{
  "audio_path": "/path/to/song.mp3",
  "chord_engine": "plkd-btc",
  "fallback_chord_engine": "essentia",
  "key": "E major optional",
  "tempo_bpm": 76,
  "time_signature": "4/4",
  "max_bars": 32,
  "output_html": true
}
```

Audio mode requires an AI-ChordCraft checkout on `CHORDCRAFT_PROJECT_ROOT` when this skill is installed as a standalone package.

`progression/degrees` supports compact or separated Nashville-style degrees:

- `1645`
- `1-6-4-5`
- `6 4 1 5`

## Output

```json
{
  "summary": {
    "key": "C major",
    "mode": "major",
    "bar_count": 4,
    "main_loop": "I - vi - IV - V"
  },
  "bars": [
    {
      "bar": 1,
      "chord": "C",
      "chords": [
        {
          "chord": "C",
          "start": "00:00.00",
          "end": "00:04.00",
          "roman": "I",
          "function": "tonic"
        }
      ],
      "roman": "I",
      "function": "tonic",
      "quality": "major"
    }
  ],
  "progression_text": "| C | Am | F | G |",
  "roman_text": "| I | vi | IV | V |",
  "functions_text": "| tonic | tonic | predominant | dominant |",
  "cadences": ["V -> I authentic cadence"],
  "audio_analysis": "object optional",
  "html": "string optional"
}
```
