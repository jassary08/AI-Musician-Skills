#!/usr/bin/env python3
"""Build layered indexes for guitar voicing databases.

This script does not modify the source voicing databases. It creates a compact
release index that lets agents inspect the library by chord quality, shape
family, difficulty, voice-leading traits, style fit, and review status.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VOICING_DIR = ROOT / "resources" / "voicing_db"
SOURCE_DIR = VOICING_DIR / "source"
INDEX_DIR = VOICING_DIR / "indexes"
EXTERNAL_PATH = SOURCE_DIR / "chords_db_voicings.json"
DEFAULT_OUTPUT = INDEX_DIR / "voicing_layers.json"
DEFAULT_SIDECAR_DIR = INDEX_DIR / "layer_indexes"

PITCHES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
PC = {
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
OPEN_STRING_PCS = [4, 9, 2, 7, 11, 4]
SUPPORTED_STYLES = ["pop", "rock", "rnb", "blues", "funk"]
FOUNDATION_QUALITIES = {"major", "minor", "power"}
CORE_COLOR_QUALITIES = {"dominant7", "minor7", "major7", "sus2", "sus4", "sixth", "add9"}
EXTENDED_COLOR_QUALITIES = {
    "dominant9",
    "dominant11",
    "dominant13",
    "minor9",
    "major9",
    "slash",
}
SPECIAL_QUALITIES = {"diminished", "half_diminished", "augmented"}
HARMONY_TIER_DESCRIPTIONS = {
    "foundation": "Major, minor, and power chords for first-pass song accompaniment.",
    "core_color": "Common seventh, suspended, add9, and sixth colors used in everyday guitar arranging.",
    "extended_color": "Ninth, eleventh, thirteenth, slash, and other richer colors for style-aware arranging.",
    "special_altered": "Diminished, half-diminished, and augmented colors that need stronger musical intent.",
    "other": "Imported chord qualities that do not fit the release tier taxonomy yet.",
}
PLAYABILITY_TIER_DESCRIPTIONS = {
    "open_basic": "Low-position open shapes suitable for beginner-friendly release curation.",
    "practical_low_mid": "Low/mid-position shapes with manageable fret span.",
    "movable_closed": "Movable or barre shapes useful for transposition and style control.",
    "upper_position": "Higher-position shapes that need clear arrangement purpose.",
    "special_shape": "Shapes that do not fit the main playability buckets.",
}
REVIEW_PRIORITY_DESCRIPTIONS = {
    "p0_curated_release": "Manually curated release defaults.",
    "p1_core_audit": "Core triad and power-chord audit pool.",
    "p2_color_audit": "Common color-chord audit pool.",
    "p3_style_extension_audit": "Style-specific extended-color audit pool.",
    "p4_backlog": "Advanced, hard, high-position, or lower-priority imported shapes.",
}
RELEASE_LAYER_DESCRIPTIONS = {
    "release_core": "Already approved release voicings.",
    "core_candidate": "Foundation shapes that should be reviewed next.",
    "color_candidate": "Common color shapes for the second review pass.",
    "style_extension_candidate": "Richer style-specific shapes for selective review.",
    "advanced_backlog": "Long-tail material kept for future curation.",
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
    if len(text) >= 2 and text[:2] in PC:
        return text[:2], text[2:]
    return text[:1], text[1:]


def classify_quality(symbol: str) -> dict[str, Any]:
    root, suffix = split_chord(symbol)
    low = suffix.lower()
    if low.startswith("5"):
        quality = "power"
        family = "power"
    elif "m7b5" in low or "ø" in low:
        quality = "half_diminished"
        family = "diminished"
    elif "dim" in low:
        quality = "diminished"
        family = "diminished"
    elif "aug" in low or "+" in low:
        quality = "augmented"
        family = "augmented"
    elif "maj9" in low:
        quality = "major9"
        family = "major"
    elif "maj7" in low or "ma7" in low:
        quality = "major7"
        family = "major"
    elif "m9" in low and not low.startswith("maj"):
        quality = "minor9"
        family = "minor"
    elif "m7" in low and not low.startswith("maj"):
        quality = "minor7"
        family = "minor"
    elif low.startswith("m") and not low.startswith("maj"):
        quality = "minor"
        family = "minor"
    elif "13" in low:
        quality = "dominant13"
        family = "dominant"
    elif "11" in low:
        quality = "dominant11"
        family = "dominant"
    elif "9" in low:
        quality = "dominant9" if "add" not in low else "add9"
        family = "dominant" if "add" not in low else "major"
    elif "7" in low:
        quality = "dominant7"
        family = "dominant"
    elif "sus2" in low:
        quality = "sus2"
        family = "suspended"
    elif "sus4" in low or "sus" in low:
        quality = "sus4"
        family = "suspended"
    elif "add" in low:
        quality = "add"
        family = "major"
    elif "6" in low:
        quality = "sixth"
        family = "major"
    elif "/" in low:
        quality = "slash"
        family = "slash"
    else:
        quality = "major"
        family = "major"
    extensions = [token for token in ["6", "7", "9", "11", "13"] if token in low]
    return {"root": root, "quality": quality, "family": family, "extensions": extensions}


def pitch_name(pc: int | None) -> str | None:
    return PITCHES[pc % 12] if pc is not None else None


def string_pitch(string: int, fret: int) -> int:
    return (OPEN_STRING_PCS[string] + fret) % 12


def played_notes(frets: list[int]) -> list[str]:
    result = []
    for string, fret in enumerate(frets[:6]):
        if isinstance(fret, int) and fret >= 0:
            result.append(PITCHES[string_pitch(string, fret)])
    return result


def bass_note(frets: list[int]) -> str | None:
    for string, fret in enumerate(frets[:6]):
        if isinstance(fret, int) and fret >= 0:
            return PITCHES[string_pitch(string, fret)]
    return None


def top_note(frets: list[int]) -> str | None:
    for string in range(5, -1, -1):
        if string < len(frets):
            fret = frets[string]
            if isinstance(fret, int) and fret >= 0:
                return PITCHES[string_pitch(string, fret)]
    return None


def fret_center(frets: list[int]) -> float | None:
    positive = [fret for fret in frets if isinstance(fret, int) and fret > 0]
    if not positive:
        return None
    return round(sum(positive) / len(positive), 2)


def fret_span(frets: list[int]) -> int:
    positive = [fret for fret in frets if isinstance(fret, int) and fret > 0]
    return max(positive) - min(positive) if positive else 0


def classify_shape(item: dict[str, Any]) -> list[str]:
    frets = item.get("frets") or []
    tags = set(item.get("tags") or [])
    positive = [fret for fret in frets if isinstance(fret, int) and fret > 0]
    muted = sum(1 for fret in frets if fret == -1)
    open_count = sum(1 for fret in frets if fret == 0)
    shape_tags = set()
    if open_count:
        shape_tags.add("open")
    if item.get("barres"):
        shape_tags.add("barre")
    if int(item.get("position") or 1) >= 5:
        shape_tags.add("high_position")
    elif int(item.get("position") or 1) >= 2:
        shape_tags.add("mid_position")
    else:
        shape_tags.add("low_position")
    if muted >= 2 or len(positive) <= 3:
        shape_tags.add("partial")
    if "power_chord" in tags:
        shape_tags.add("power_chord")
    if "ringing" in tags or "modern_acoustic" in tags:
        shape_tags.add("modern_open")
    if "movable" in tags or (positive and min(positive) >= 3 and not open_count):
        shape_tags.add("movable")
    if "jazz" in tags:
        shape_tags.add("jazz")
    if "common" in tags:
        shape_tags.add("common")
    return sorted(shape_tags)


def difficulty_band(item: dict[str, Any]) -> str:
    difficulty = int(item.get("difficulty") or 3)
    if difficulty <= 1:
        return "easy"
    if difficulty <= 3:
        return "medium"
    return "hard"


def review_status(item: dict[str, Any], source_name: str) -> str:
    if item.get("review_status"):
        return str(item["review_status"])
    if source_name == "curated":
        return "release_default"
    return "external_import_needs_review"


def style_fit(item: dict[str, Any], shape_tags: list[str], quality: str, family: str) -> dict[str, float]:
    tags = set(item.get("tags") or []) | set(shape_tags)
    best_for = set(item.get("best_for") or [])
    avoid_for = set(item.get("avoid_for") or [])
    result = {}
    for style in SUPPORTED_STYLES:
        score = 0.3
        if style in best_for:
            score += 0.45
        if style in avoid_for:
            score -= 0.35
        if style == "pop":
            if tags & {"open", "modern_open", "ringing", "common"}:
                score += 0.25
            if quality in {"add9", "sus2", "sus4", "minor7", "major7"}:
                score += 0.1
        elif style == "rock":
            if tags & {"power_chord", "movable", "barre", "common"}:
                score += 0.25
            if family in {"power", "major", "minor", "dominant", "suspended"}:
                score += 0.1
        elif style == "rnb":
            if tags & {"partial", "jazz", "movable"}:
                score += 0.25
            if quality in {"minor7", "major7", "minor9", "major9", "dominant9", "dominant13"}:
                score += 0.2
        elif style == "blues":
            if quality in {"dominant7", "dominant9", "dominant13", "sixth"}:
                score += 0.35
            if tags & {"movable", "partial", "barre"}:
                score += 0.1
        elif style == "funk":
            if tags & {"partial", "movable", "jazz"}:
                score += 0.3
            if quality in {"dominant9", "dominant13", "minor7", "sus4"}:
                score += 0.25
            if "open" in tags:
                score -= 0.1
        result[style] = round(max(0.0, min(1.0, score)), 2)
    return result


def harmony_tier(quality: str) -> str:
    if quality in FOUNDATION_QUALITIES:
        return "foundation"
    if quality in CORE_COLOR_QUALITIES:
        return "core_color"
    if quality in EXTENDED_COLOR_QUALITIES:
        return "extended_color"
    if quality in SPECIAL_QUALITIES:
        return "special_altered"
    return "other"


def playability_tier(item: dict[str, Any], shape_tags: list[str], band: str) -> str:
    position = int(item.get("position") or 1)
    span = fret_span(item.get("frets") or [])
    has_barre = bool(item.get("barres"))
    tags = set(item.get("tags") or []) | set(shape_tags)

    if (
        band == "easy"
        and "open" in tags
        and position <= 2
        and not has_barre
    ):
        return "open_basic"
    if band in {"easy", "medium"} and position <= 4 and span <= 4:
        return "practical_low_mid"
    if "movable" in tags or has_barre:
        return "movable_closed"
    if position >= 5:
        return "upper_position"
    return "special_shape"


def review_priority(
    status: str,
    harmony: str,
    playability: str,
    band: str,
    fit: dict[str, float],
) -> str:
    if status == "release_default":
        return "p0_curated_release"
    best_style_fit = max(fit.values()) if fit else 0.0
    if harmony == "foundation" and playability in {"open_basic", "practical_low_mid"} and band != "hard":
        return "p1_core_audit"
    if harmony == "core_color" and playability in {"open_basic", "practical_low_mid", "movable_closed"} and band != "hard":
        return "p2_color_audit"
    if harmony == "extended_color" and best_style_fit >= 0.7 and band != "hard":
        return "p3_style_extension_audit"
    return "p4_backlog"


def release_layer(priority: str) -> str:
    return {
        "p0_curated_release": "release_core",
        "p1_core_audit": "core_candidate",
        "p2_color_audit": "color_candidate",
        "p3_style_extension_audit": "style_extension_candidate",
        "p4_backlog": "advanced_backlog",
    }[priority]


def load_voicing_records() -> list[dict[str, Any]]:
    records = []
    external = load_json(EXTERNAL_PATH) if EXTERNAL_PATH.exists() else {}
    external_items = external.get("voicings", []) if isinstance(external, dict) else external
    for index, item in enumerate(external_items):
        records.append({"source_name": "external", "source_index": index, "item": item})
    return records


def add_index(index: dict[str, list[str]], key: str, voicing_id: str) -> None:
    index.setdefault(key, []).append(voicing_id)


def build_layers() -> dict[str, Any]:
    records = load_voicing_records()
    voicings = []
    by_family: dict[str, list[str]] = {}
    by_quality: dict[str, list[str]] = {}
    by_shape_type: dict[str, list[str]] = {}
    by_difficulty: dict[str, list[str]] = {}
    by_position: dict[str, list[str]] = {}
    by_top_note: dict[str, list[str]] = {}
    by_bass_note: dict[str, list[str]] = {}
    by_review_status: dict[str, list[str]] = {}
    by_style_fit: dict[str, list[str]] = {}
    by_harmony_tier: dict[str, list[str]] = {}
    by_playability_tier: dict[str, list[str]] = {}
    by_review_priority: dict[str, list[str]] = {}
    by_release_layer: dict[str, list[str]] = {}
    summary = {
        "family": Counter(),
        "quality": Counter(),
        "harmony_tier": Counter(),
        "shape_type": Counter(),
        "difficulty_band": Counter(),
        "playability_tier": Counter(),
        "review_status": Counter(),
        "review_priority": Counter(),
        "release_layer": Counter(),
    }
    seen = set()
    for record in records:
        item = record["item"]
        symbol = normalize_symbol(item.get("symbol"))
        frets = item.get("frets") or []
        key = (symbol, tuple(frets))
        if key in seen:
            continue
        seen.add(key)
        chord_info = classify_quality(symbol)
        shapes = classify_shape(item)
        band = difficulty_band(item)
        status = review_status(item, record["source_name"])
        notes = played_notes(frets)
        bass = bass_note(frets)
        top = top_note(frets)
        fit = style_fit(item, shapes, chord_info["quality"], chord_info["family"])
        harmony = harmony_tier(chord_info["quality"])
        playable = playability_tier(item, shapes, band)
        priority = review_priority(status, harmony, playable, band, fit)
        layer = release_layer(priority)
        voicing_id = f"v{len(voicings):05d}"
        layer_item = {
            "id": voicing_id,
            "symbol": symbol,
            "root": chord_info["root"],
            "family": chord_info["family"],
            "quality": chord_info["quality"],
            "extensions": chord_info["extensions"],
            "harmony_tier": harmony,
            "shape": "".join("x" if fret < 0 else str(fret) for fret in frets),
            "frets": frets,
            "fingers": item.get("fingers"),
            "position": item.get("position"),
            "barres": item.get("barres", []),
            "shape_types": shapes,
            "difficulty": item.get("difficulty"),
            "difficulty_band": band,
            "playability_tier": playable,
            "voice_leading": {
                "bass_note": bass,
                "top_note": top,
                "played_notes": sorted(set(notes)),
                "open_strings": [idx for idx, fret in enumerate(frets[:6]) if fret == 0],
                "muted_strings": [idx for idx, fret in enumerate(frets[:6]) if fret == -1],
                "fret_center": fret_center(frets),
                "fret_span": fret_span(frets),
            },
            "style_fit": fit,
            "tags": item.get("tags", []),
            "best_for": item.get("best_for", []),
            "avoid_for": item.get("avoid_for", []),
            "review_status": status,
            "review_priority": priority,
            "release_layer": layer,
            "source": item.get("source") or record["source_name"],
            "source_license": item.get("source_license"),
            "source_id": item.get("source_id"),
        }
        voicings.append(layer_item)

        add_index(by_family, chord_info["family"], voicing_id)
        add_index(by_quality, chord_info["quality"], voicing_id)
        add_index(by_difficulty, band, voicing_id)
        add_index(by_position, str(item.get("position") or 1), voicing_id)
        add_index(by_review_status, status, voicing_id)
        add_index(by_harmony_tier, harmony, voicing_id)
        add_index(by_playability_tier, playable, voicing_id)
        add_index(by_review_priority, priority, voicing_id)
        add_index(by_release_layer, layer, voicing_id)
        if top:
            add_index(by_top_note, top, voicing_id)
        if bass:
            add_index(by_bass_note, bass, voicing_id)
        for shape in shapes:
            add_index(by_shape_type, shape, voicing_id)
        for style, score in fit.items():
            if score >= 0.7:
                add_index(by_style_fit, style, voicing_id)
        summary["family"][chord_info["family"]] += 1
        summary["quality"][chord_info["quality"]] += 1
        summary["harmony_tier"][harmony] += 1
        summary["difficulty_band"][band] += 1
        summary["playability_tier"][playable] += 1
        summary["review_status"][status] += 1
        summary["review_priority"][priority] += 1
        summary["release_layer"][layer] += 1
        for shape in shapes:
            summary["shape_type"][shape] += 1

    return {
        "version": "0.1.0",
        "description": "Algorithmic layered index for AI-ChordCraft guitar voicing databases.",
        "standard_tuning": "EADGBE",
        "source_files": [
            str(EXTERNAL_PATH.relative_to(ROOT)),
        ],
        "stats": {
            "voicing_count": len(voicings),
            "summary": {key: dict(counter.most_common()) for key, counter in summary.items()},
        },
        "layers": {
            "by_family": by_family,
            "by_quality": by_quality,
            "by_shape_type": by_shape_type,
            "by_difficulty": by_difficulty,
            "by_position": by_position,
            "by_top_note": by_top_note,
            "by_bass_note": by_bass_note,
            "by_review_status": by_review_status,
            "by_style_fit": by_style_fit,
            "by_harmony_tier": by_harmony_tier,
            "by_playability_tier": by_playability_tier,
            "by_review_priority": by_review_priority,
            "by_release_layer": by_release_layer,
        },
        "voicings": voicings,
    }


def sidecar_payload(
    payload: dict[str, Any],
    description: str,
    indexes: dict[str, tuple[str | None, str]],
    definitions: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    layers = payload["layers"]
    summary = payload["stats"]["summary"]
    return {
        "version": payload["version"],
        "description": description,
        "standard_tuning": payload["standard_tuning"],
        "voicing_count": payload["stats"]["voicing_count"],
        "definitions": definitions or {},
        "summary": {
            name: summary[summary_key]
            for name, (summary_key, _layer_key) in indexes.items()
            if summary_key and summary_key in summary
        },
        "indexes": {
            name: layers[layer_key]
            for name, (_summary_key, layer_key) in indexes.items()
            if layer_key in layers
        },
    }


def build_sidecars(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        "manifest.json": {
            "version": payload["version"],
            "description": "Sidecar index manifest for AI-ChordCraft guitar voicing layers.",
            "source": "../voicing_layers.json",
            "files": {
                "musical_taxonomy.json": "Chord family, quality, and harmony-tier indexes.",
                "guitar_playability.json": "Difficulty, position, shape, and playability-tier indexes.",
                "release_review_pools.json": "Release layer and review-priority indexes for curation.",
                "style_fit.json": "Style fit indexes for pop, rock, rnb, blues, and funk.",
                "voice_leading.json": "Bass-note and top-note indexes for transition planning.",
            },
        },
        "musical_taxonomy.json": sidecar_payload(
            payload,
            "Musical chord taxonomy indexes for selecting chord vocabulary layers.",
            {
                "family": ("family", "by_family"),
                "quality": ("quality", "by_quality"),
                "harmony_tier": ("harmony_tier", "by_harmony_tier"),
            },
            {"harmony_tier": HARMONY_TIER_DESCRIPTIONS},
        ),
        "guitar_playability.json": sidecar_payload(
            payload,
            "Guitar-specific playability indexes for filtering usable shapes.",
            {
                "shape_type": ("shape_type", "by_shape_type"),
                "difficulty_band": ("difficulty_band", "by_difficulty"),
                "position": (None, "by_position"),
                "playability_tier": ("playability_tier", "by_playability_tier"),
            },
            {"playability_tier": PLAYABILITY_TIER_DESCRIPTIONS},
        ),
        "release_review_pools.json": sidecar_payload(
            payload,
            "Review and release curation pools derived from harmony and playability tiers.",
            {
                "review_status": ("review_status", "by_review_status"),
                "review_priority": ("review_priority", "by_review_priority"),
                "release_layer": ("release_layer", "by_release_layer"),
            },
            {
                "review_priority": REVIEW_PRIORITY_DESCRIPTIONS,
                "release_layer": RELEASE_LAYER_DESCRIPTIONS,
            },
        ),
        "style_fit.json": {
            "version": payload["version"],
            "description": "Style-fit indexes for the five supported release styles.",
            "supported_styles": SUPPORTED_STYLES,
            "summary": {
                style: len(payload["layers"]["by_style_fit"].get(style, []))
                for style in SUPPORTED_STYLES
            },
            "indexes": payload["layers"]["by_style_fit"],
        },
        "voice_leading.json": {
            "version": payload["version"],
            "description": "Voice-leading indexes for choosing smoother adjacent chord transitions.",
            "indexes": {
                "top_note": payload["layers"]["by_top_note"],
                "bass_note": payload["layers"]["by_bass_note"],
            },
        },
    }


def write_sidecars(payload: dict[str, Any], sidecar_dir: Path) -> None:
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    for filename, data in build_sidecars(payload).items():
        (sidecar_dir / filename).write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build layered index for guitar voicing databases.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output JSON path.")
    parser.add_argument("--sidecar-dir", default=str(DEFAULT_SIDECAR_DIR), help="Directory for split layer index JSON files.")
    parser.add_argument("--no-sidecars", action="store_true", help="Only write the main voicing_layers.json file.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print output JSON.")
    args = parser.parse_args()

    output = Path(args.output)
    payload = build_layers()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None) + "\n", encoding="utf-8")
    sidecar_dir = None
    if not args.no_sidecars:
        sidecar_dir = Path(args.sidecar_dir)
        write_sidecars(payload, sidecar_dir)
    print(json.dumps({
        "ok": True,
        "output": str(output),
        "sidecar_dir": str(sidecar_dir) if sidecar_dir else None,
        "voicing_count": payload["stats"]["voicing_count"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
