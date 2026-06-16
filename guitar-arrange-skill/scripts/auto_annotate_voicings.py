#!/usr/bin/env python3
"""Create a common-sense annotation overlay for imported guitar voicings.

The output is intentionally separate from the source database. It provides a
first-pass commonness/status/style label that can be manually corrected in the
annotation UI and later used by the arranger as a scoring overlay.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VOICING_DIR = ROOT / "resources" / "voicing_db"
SOURCE_PATH = VOICING_DIR / "source" / "chords_db_voicings.json"
DEFAULT_OUTPUT = VOICING_DIR / "overlays" / "commonness_annotations.json"

COMMON_SHAPES: dict[str, list[str]] = {
    "C": ["x32010", "x35553"],
    "Cm": ["x35543"],
    "C7": ["x32310", "x35353"],
    "Cmaj7": ["x32000", "x35453"],
    "Cm7": ["x35343"],
    "Cadd9": ["x32033"],
    "D": ["xx0232"],
    "Dm": ["xx0231"],
    "D7": ["xx0212"],
    "Dm7": ["xx0211"],
    "Dmaj7": ["xx0222"],
    "Dsus4": ["xx0233"],
    "Dsus2": ["xx0230"],
    "E": ["022100"],
    "Em": ["022000"],
    "E7": ["020100", "022130"],
    "Em7": ["022030", "020000"],
    "Emaj7": ["021100"],
    "Esus4": ["022200"],
    "F": ["133211", "xx3211"],
    "Fm": ["133111"],
    "F7": ["131211"],
    "Fm7": ["131111"],
    "Fmaj7": ["xx3210", "132211"],
    "F#": ["244322"],
    "F#m": ["244222"],
    "F#7": ["242322"],
    "F#m7": ["242222"],
    "G": ["320003", "320033", "355433"],
    "Gm": ["355333"],
    "G7": ["320001", "353433"],
    "Gm7": ["353333"],
    "Gmaj7": ["320002", "354433"],
    "Gsus4": ["330013"],
    "A": ["x02220", "577655"],
    "Am": ["x02210", "577555"],
    "A7": ["x02020", "575655"],
    "Am7": ["x02010", "575555"],
    "Amaj7": ["x02120", "576655"],
    "Asus2": ["x02200"],
    "Asus4": ["x02230"],
    "Bb": ["x13331", "688766"],
    "Bbm": ["x13321", "688666"],
    "Bb7": ["x13131", "686766"],
    "Bbm7": ["x13121", "686666"],
    "B": ["x24442", "799877"],
    "Bm": ["x24432", "799777"],
    "B7": ["x21202", "797877"],
    "Bm7": ["x20202", "797777"],
    "Bmaj7": ["x24342", "798877"],
}

STYLE_QUALITY_HINTS = {
    "pop": {"major", "minor", "sus2", "sus4", "add9", "major7", "minor7"},
    "rock": {"major", "minor", "power", "sus2", "sus4", "dominant7"},
    "blues": {"dominant7", "dominant9", "dominant13", "sixth", "minor7"},
    "rnb": {"major7", "minor7", "major9", "minor9", "dominant9", "dominant13"},
    "funk": {"dominant9", "dominant13", "minor7", "sus4", "dominant7"},
}

PITCH_CLASS = {
    "C": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_symbol(symbol: Any) -> str:
    text = str(symbol or "").strip().replace("♯", "#").replace("♭", "b")
    if not text:
        return ""
    return text[0].upper() + text[1:]


def split_chord(symbol: str) -> tuple[str, str]:
    text = normalize_symbol(symbol)
    if len(text) >= 2 and text[:2] in PITCH_CLASS:
        return text[:2], text[2:]
    return text[:1], text[1:]


def classify_quality(symbol: str) -> str:
    _root, suffix = split_chord(symbol)
    low = suffix.lower()
    if low.startswith("5"):
        return "power"
    if "m7b5" in low or "ø" in low:
        return "half_diminished"
    if "dim" in low:
        return "diminished"
    if "aug" in low or "+" in low:
        return "augmented"
    if "maj9" in low:
        return "major9"
    if "maj7" in low or "ma7" in low:
        return "major7"
    if "m9" in low and not low.startswith("maj"):
        return "minor9"
    if "m7" in low and not low.startswith("maj"):
        return "minor7"
    if low.startswith("m") and not low.startswith("maj"):
        return "minor"
    if "13" in low:
        return "dominant13"
    if "11" in low:
        return "dominant11"
    if "9" in low:
        return "add9" if "add" in low else "dominant9"
    if "7" in low:
        return "dominant7"
    if "sus2" in low:
        return "sus2"
    if "sus4" in low or "sus" in low:
        return "sus4"
    if "add" in low:
        return "add9"
    if "6" in low:
        return "sixth"
    if "/" in low:
        return "slash"
    return "major"


def frets_to_shape(frets: list[int]) -> str:
    return "".join("x" if fret < 0 else str(fret) for fret in frets[:6])


def annotation_key(symbol: str, frets: list[int]) -> str:
    return f"{normalize_symbol(symbol)}|{','.join(str(fret) for fret in frets[:6])}"


def fret_span(frets: list[int]) -> int:
    positive = [fret for fret in frets if fret > 0]
    return max(positive) - min(positive) if positive else 0


def played_string_count(frets: list[int]) -> int:
    return sum(1 for fret in frets if fret >= 0)


def shape_family(item: dict[str, Any], frets: list[int]) -> set[str]:
    tags = set(item.get("tags") or [])
    position = int(item.get("position") or 1)
    families = set()
    if any(fret == 0 for fret in frets):
        families.add("open")
    if item.get("barres"):
        families.add("barre")
    if "movable" in tags or (position >= 3 and not any(fret == 0 for fret in frets)):
        families.add("movable")
    if played_string_count(frets) <= 4:
        families.add("partial")
    if position >= 7:
        families.add("high_position")
    elif position >= 3:
        families.add("mid_position")
    else:
        families.add("low_position")
    return families


def status_from_commonness(commonness: int) -> str:
    if commonness >= 5:
        return "preferred"
    if commonness == 4:
        return "common"
    if commonness == 3:
        return "usable"
    if commonness == 2:
        return "rare"
    return "rejected"


def canonical_rank(symbol: str, shape: str) -> int | None:
    shapes = COMMON_SHAPES.get(symbol) or []
    if shape not in shapes:
        return None
    return shapes.index(shape) + 1


def infer_styles(symbol: str, quality: str, families: set[str], rank: int | None) -> list[str]:
    styles = []
    for style, qualities in STYLE_QUALITY_HINTS.items():
        if quality in qualities:
            styles.append(style)
    if rank is not None and {"open", "barre"} & families:
        for style in ["pop", "rock"]:
            if style not in styles:
                styles.append(style)
    if quality in {"dominant7", "dominant9", "dominant13"}:
        for style in ["blues", "funk"]:
            if style not in styles:
                styles.append(style)
    if quality in {"major7", "minor7", "major9", "minor9"}:
        for style in ["rnb", "pop"]:
            if style not in styles:
                styles.append(style)
    if symbol in {"E7", "A7", "B7", "Em7", "Am7"} and "blues" not in styles:
        styles.append("blues")
    if "partial" in families and "movable" in families:
        for style in ["funk", "rnb"]:
            if style not in styles:
                styles.append(style)
    return styles


def infer_contexts(
    item: dict[str, Any],
    frets: list[int],
    families: set[str],
    commonness: int,
) -> list[str]:
    contexts = sorted(families)
    difficulty = int(item.get("difficulty") or 3)
    if difficulty <= 1 and "barre" not in families and commonness >= 3:
        contexts.append("beginner")
    if commonness >= 4 and ("open" in families or "barre" in families):
        contexts.append("campfire")
    if fret_span(frets) <= 3:
        contexts.append("compact")
    if played_string_count(frets) <= 4:
        contexts.append("small_voicing")
    return sorted(set(contexts))


def infer_commonness(item: dict[str, Any]) -> tuple[int, str]:
    symbol = normalize_symbol(item.get("symbol"))
    frets = [int(fret) for fret in item.get("frets", [])[:6]]
    shape = frets_to_shape(frets)
    rank = canonical_rank(symbol, shape)
    tags = set(item.get("tags") or [])
    difficulty = int(item.get("difficulty") or 3)
    position = int(item.get("position") or 1)
    families = shape_family(item, frets)
    span = fret_span(frets)
    strings = played_string_count(frets)

    if rank == 1:
        return 5, "canonical first-choice guitar shape."
    if rank is not None:
        return 4, "recognized common alternate guitar shape."

    score = 2.5
    if "common" in tags:
        score += 1.2
    if "beginner" in tags:
        score += 0.9
    if "open" in families and position <= 2:
        score += 0.7
    if "barre" in families and position <= 5:
        score += 0.35
    if "movable" in families and position <= 5:
        score += 0.25
    if strings <= 3:
        score -= 0.6
    if span > 4:
        score -= 0.7
    if position >= 7:
        score -= 0.9
    score -= max(0, difficulty - 2) * 0.55

    if score >= 4.25:
        return 4, "high-scoring open/common imported shape."
    if score >= 3.1:
        return 3, "usable imported shape, but not a canonical default."
    if score >= 1.8:
        return 2, "rare or context-specific imported shape."
    return 1, "low-priority shape for release defaults."


def annotate_item(item: dict[str, Any], now: str) -> dict[str, Any]:
    symbol = normalize_symbol(item.get("symbol"))
    frets = [int(fret) for fret in item.get("frets", [])[:6]]
    shape = frets_to_shape(frets)
    quality = classify_quality(symbol)
    rank = canonical_rank(symbol, shape)
    commonness, reason = infer_commonness(item)
    families = shape_family(item, frets)
    return {
        "symbol": symbol,
        "shape": shape,
        "frets": frets,
        "commonness": commonness,
        "status": status_from_commonness(commonness),
        "styles": infer_styles(symbol, quality, families, rank),
        "contexts": infer_contexts(item, frets, families, commonness),
        "canonical_rank": rank,
        "quality": quality,
        "notes": reason,
        "source": "auto_common_sense_v1",
        "updated_at": now,
    }


def load_voicings(path: Path) -> list[dict[str, Any]]:
    payload = load_json(path)
    voicings = payload.get("voicings", []) if isinstance(payload, dict) else payload
    return [item for item in voicings if isinstance(item, dict)]


def build_annotations(source_path: Path) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    annotations = {}
    status_counter: Counter[str] = Counter()
    commonness_counter: Counter[str] = Counter()
    for item in load_voicings(source_path):
        frets = item.get("frets")
        symbol = normalize_symbol(item.get("symbol"))
        if not symbol or not isinstance(frets, list) or len(frets) != 6:
            continue
        annotation = annotate_item(item, now)
        key = annotation_key(symbol, annotation["frets"])
        annotations[key] = annotation
        status_counter[annotation["status"]] += 1
        commonness_counter[str(annotation["commonness"])] += 1
    return {
        "version": "0.1.0",
        "description": "Auto-generated common-sense overlay for AI-ChordCraft guitar voicing commonness and style labels.",
        "source_file": str(source_path.relative_to(ROOT)),
        "generated_by": "scripts/auto_annotate_voicings.py",
        "updated_at": now,
        "policy": {
            "commonness": {
                "5": "first-choice canonical shape",
                "4": "common alternate",
                "3": "usable but not default",
                "2": "rare or context-specific",
                "1": "avoid as release default",
            },
            "status": ["preferred", "common", "usable", "rare", "rejected"],
            "note": "This file is a first-pass heuristic overlay, not a substitute for human review.",
        },
        "stats": {
            "annotation_count": len(annotations),
            "status": dict(status_counter.most_common()),
            "commonness": dict(sorted(commonness_counter.items(), reverse=True)),
        },
        "annotations": annotations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-label guitar voicings with commonness/style metadata.")
    parser.add_argument("--source", default=str(SOURCE_PATH), help="Source voicing database JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output annotation overlay JSON.")
    args = parser.parse_args()

    source = Path(args.source)
    output = Path(args.output)
    payload = build_annotations(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output), **payload["stats"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
