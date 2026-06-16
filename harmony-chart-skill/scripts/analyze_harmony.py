#!/usr/bin/env python3
"""Analyze chord progressions and render compact measure charts."""

from __future__ import annotations

import argparse
import contextlib
import html
import io
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any


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

MAJOR_ROMANS = {
    0: "I",
    2: "ii",
    4: "iii",
    5: "IV",
    7: "V",
    9: "vi",
    11: "vii°",
}
MINOR_ROMANS = {
    0: "i",
    2: "ii°",
    3: "III",
    5: "iv",
    7: "v",
    8: "VI",
    10: "VII",
}
MAJOR_DEGREE_CHORDS = {
    "1": ("", ""),
    "2": ("D", "m"),
    "3": ("E", "m"),
    "4": ("F", ""),
    "5": ("G", ""),
    "6": ("A", "m"),
    "7": ("B", "dim"),
}
MINOR_DEGREE_CHORDS = {
    "1": ("", "m"),
    "2": ("D", "dim"),
    "3": ("Eb", ""),
    "4": ("F", "m"),
    "5": ("G", "m"),
    "6": ("Ab", ""),
    "7": ("Bb", ""),
}
SEMITONE_TO_SHARP = {
    0: "C",
    1: "C#",
    2: "D",
    3: "D#",
    4: "E",
    5: "F",
    6: "F#",
    7: "G",
    8: "G#",
    9: "A",
    10: "A#",
    11: "B",
}
FUNCTIONS_MAJOR = {
    0: "tonic",
    2: "predominant",
    4: "tonic",
    5: "predominant",
    7: "dominant",
    9: "tonic",
    11: "dominant",
}
FUNCTIONS_MINOR = {
    0: "tonic",
    2: "predominant",
    3: "tonic",
    5: "predominant",
    7: "dominant",
    8: "tonic",
    10: "dominant",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_chord(value: Any) -> str:
    text = str(value or "").strip().replace("♯", "#").replace("♭", "b")
    if not text:
        return ""
    return text[0].upper() + text[1:]


def split_chord(symbol: str) -> tuple[str, str]:
    text = normalize_chord(symbol)
    if len(text) >= 2 and text[:2] in PC:
        return text[:2], text[2:]
    return text[:1], text[1:]


def parse_key(value: Any) -> tuple[str, str]:
    text = str(value or "C major").strip().replace("♯", "#").replace("♭", "b")
    parts = text.split()
    root = normalize_chord(parts[0] if parts else "C")
    mode_text = " ".join(parts[1:]).lower()
    mode = "minor" if mode_text in {"minor", "min", "m", "小调", "小"} or "minor" in mode_text else "major"
    if root not in PC:
        return "C", "major"
    return root, mode


def quality(symbol: str) -> str:
    _root, suffix = split_chord(symbol)
    low = suffix.lower()
    if "dim" in low or "°" in low:
        return "diminished"
    if "aug" in low or "+" in low:
        return "augmented"
    if low.startswith("m") and not low.startswith("maj"):
        return "minor"
    return "major"


def roman_for_chord(symbol: str, key: str) -> tuple[str, str]:
    key_root, mode = parse_key(key)
    root, suffix = split_chord(symbol)
    if root not in PC:
        return "?", "unknown"
    interval = (PC[root] - PC[key_root]) % 12
    romans = MINOR_ROMANS if mode == "minor" else MAJOR_ROMANS
    functions = FUNCTIONS_MINOR if mode == "minor" else FUNCTIONS_MAJOR
    roman = romans.get(interval)
    function = functions.get(interval, "borrowed/modal")
    chord_quality = quality(symbol)

    if roman is None:
        roman = f"b{_nearest_degree(interval)}" if interval in {1, 3, 6, 8, 10} else "chromatic"
    if chord_quality == "minor" and roman.isupper() and "°" not in roman:
        roman = roman.lower()
    if chord_quality == "major" and roman.islower() and "°" not in roman:
        roman = roman.upper()
    if "maj7" in suffix.lower():
        roman += "maj7"
    elif "7" in suffix:
        roman += "7"
    elif "sus" in suffix.lower():
        roman += "sus"
    elif "add9" in suffix.lower():
        roman += "add9"
    return roman, function


def _nearest_degree(interval: int) -> str:
    names = {1: "II", 3: "III", 6: "V", 8: "VI", 10: "VII"}
    return names.get(interval, "?")


def chord_from_degree(token: str, key: str) -> str:
    key_root, mode = parse_key(key)
    text = str(token or "").strip()
    match = re.fullmatch(r"([b#]?)([1-7])([A-Za-z0-9+#°]*)", text)
    if not match:
        return normalize_chord(text)
    accidental, degree, suffix_override = match.groups()
    table = MINOR_DEGREE_CHORDS if mode == "minor" else MAJOR_DEGREE_CHORDS
    relative_root, default_suffix = table[degree]
    if relative_root:
        root_pc = PC[relative_root]
    else:
        root_pc = PC[key_root]
    transposed_pc = (root_pc + PC[key_root]) % 12
    if mode == "major":
        transposed_pc = (PC[key_root] + {"1": 0, "2": 2, "3": 4, "4": 5, "5": 7, "6": 9, "7": 11}[degree]) % 12
    elif degree == "1":
        transposed_pc = PC[key_root]
    if accidental == "b":
        transposed_pc = (transposed_pc - 1) % 12
    elif accidental == "#":
        transposed_pc = (transposed_pc + 1) % 12
    suffix = suffix_override if suffix_override else default_suffix
    return f"{SEMITONE_TO_SHARP[transposed_pc]}{suffix}"


def parse_degree_progression(value: Any, key: str) -> list[str]:
    if not value:
        return []
    text = str(value).strip()
    if not text:
        return []
    if re.fullmatch(r"[b#]?[1-7](?:\s*[-|, ]\s*[b#]?[1-7][A-Za-z0-9+#°]*)+", text):
        tokens = [part for part in re.split(r"\s*[-|, ]\s*", text) if part]
    elif re.fullmatch(r"[1-7]+", text):
        tokens = list(text)
    else:
        tokens = [part for part in re.split(r"\s*[-|,]\s*|\s+", text) if part]
    degree_like = [token for token in tokens if re.fullmatch(r"[b#]?[1-7][A-Za-z0-9+#°]*", token)]
    if len(degree_like) != len(tokens):
        return []
    return [chord_from_degree(token, key) for token in tokens]


def coerce_bars(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload.get("bars"), list) and payload["bars"]:
        bars = []
        for index, item in enumerate(payload["bars"], start=1):
            if not isinstance(item, dict):
                continue
            segments = item.get("chords")
            if isinstance(segments, list) and segments:
                segment_chords = [normalize_chord(segment.get("chord")) for segment in segments if isinstance(segment, dict)]
                chord = normalize_chord(item.get("chord")) or " / ".join(chord for chord in segment_chords if chord)
            else:
                chord = normalize_chord(item.get("chord"))
            if not chord and not segments:
                continue
            normalized_item = dict(item)
            normalized_item["bar"] = int(item.get("bar") or index)
            normalized_item["chord"] = chord
            normalized_item["time"] = item.get("time")
            normalized_item["end"] = item.get("end")
            bars.append(normalized_item)
        return bars
    chords = payload.get("chords") or []
    if not chords:
        chords = parse_degree_progression(payload.get("progression") or payload.get("degrees"), payload.get("key"))
    if isinstance(chords, str):
        chords = [part for part in re.split(r"\s*[-|,]\s*|\s+", chords) if part]
    return [
        {"bar": index + 1, "chord": normalize_chord(chord), "time": None, "end": None}
        for index, chord in enumerate(chords)
        if normalize_chord(chord)
    ]


def rows(items: list[dict[str, Any]], columns: int) -> list[list[dict[str, Any]]]:
    return [items[index : index + columns] for index in range(0, len(items), columns)]


def grid_text(items: list[dict[str, Any]], field: str, columns: int) -> str:
    return "\n".join("| " + " | ".join(str(item.get(field) or "-") for item in row) + " |" for row in rows(items, columns))


def _event_start(event: dict[str, Any]) -> float | None:
    value = event.get("time_seconds")
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    value = event.get("time")
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def _event_end(event: dict[str, Any]) -> float | None:
    value = event.get("end_seconds")
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    value = event.get("end")
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def _format_time(seconds: float) -> str:
    bounded = max(0.0, float(seconds))
    minutes = int(bounded // 60)
    remain = bounded - minutes * 60
    return f"{minutes:02d}:{remain:05.2f}"


def _load_chordcraft_audio_helpers() -> dict[str, Any]:
    configured_root = os.environ.get("CHORDCRAFT_PROJECT_ROOT")
    project_root = Path(configured_root).expanduser().resolve() if configured_root else Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    _configure_default_acr_model_dir(project_root)
    try:
        from src._runtime import probe_audio_duration
        from src.chord_recognition import (
            ChordRecognitionError,
            estimate_song_metadata,
            postprocess_chord_events,
            recognize_chords,
        )
    except Exception as exc:
        raise RuntimeError(f"Cannot import AI-ChordCraft audio analysis helpers: {exc}") from exc
    return {
        "ChordRecognitionError": ChordRecognitionError,
        "estimate_song_metadata": estimate_song_metadata,
        "postprocess_chord_events": postprocess_chord_events,
        "probe_audio_duration": probe_audio_duration,
        "recognize_chords": recognize_chords,
    }


def _configure_default_acr_model_dir(project_root: Path) -> None:
    if "CHORDCRAFT_ACR_MODEL_DIR" in os.environ or "CHORDCRAFT_PLKD_ACR_DIR" in os.environ:
        return
    candidates = [
        project_root / "third_party" / "pseudo_label_kd_acr",
        project_root.parent / "MOSS-Music" / "third_party" / "pseudo_label_kd_acr",
    ]
    for candidate in candidates:
        if (candidate / "btc_chord_recognition.py").exists() and (candidate / "config" / "btc_config.yaml").exists():
            os.environ["CHORDCRAFT_ACR_MODEL_DIR"] = str(candidate)
            return


def _duration_from_events(events: list[dict[str, Any]]) -> float | None:
    candidates: list[float] = []
    for event in events:
        for value in (_event_start(event), _event_end(event)):
            if value is not None:
                candidates.append(value)
    if not candidates:
        return None
    return max(candidates)


def _event_intervals(events: list[dict[str, Any]], duration_seconds: float) -> list[dict[str, Any]]:
    sorted_events = sorted(
        [event for event in events if _event_start(event) is not None],
        key=lambda event: _event_start(event) or 0.0,
    )
    intervals = []
    for index, event in enumerate(sorted_events):
        start = _event_start(event)
        if start is None:
            continue
        explicit_end = _event_end(event)
        next_start = _event_start(sorted_events[index + 1]) if index + 1 < len(sorted_events) else None
        end = explicit_end if explicit_end is not None and explicit_end > start else next_start
        if end is None or end <= start:
            end = duration_seconds
        chord = normalize_chord(event.get("chord"))
        if not chord or chord.upper() in {"N", "NC", "NOCHORD"}:
            continue
        intervals.append(
            {
                "start": max(0.0, float(start)),
                "end": min(float(duration_seconds), float(end)),
                "chord": chord,
                "confidence": event.get("confidence"),
                "source": event.get("source"),
            }
        )
    return [item for item in intervals if item["end"] > item["start"]]


def _append_bar_segment(segments: list[dict[str, Any]], segment: dict[str, Any]) -> None:
    if segments and segments[-1].get("chord") == segment.get("chord"):
        segments[-1]["end_seconds"] = segment["end_seconds"]
        segments[-1]["end"] = segment["end"]
        segments[-1]["duration_seconds"] = round(
            float(segments[-1].get("duration_seconds") or 0.0) + float(segment.get("duration_seconds") or 0.0),
            3,
        )
        return
    segments.append(segment)


def events_to_measure_bars(
    events: list[dict[str, Any]],
    key: str,
    bpm: float,
    time_signature: str = "4/4",
    duration_seconds: float | None = None,
    max_bars: int | None = None,
) -> list[dict[str, Any]]:
    match = re.match(r"^(\d{1,2})\s*/\s*(\d{1,2})$", str(time_signature or "4/4"))
    beats_per_bar = int(match.group(1)) if match else 4
    if beats_per_bar <= 0 or beats_per_bar > 12:
        beats_per_bar = 4
    resolved_bpm = float(bpm or 90.0)
    if not math.isfinite(resolved_bpm) or resolved_bpm <= 0:
        resolved_bpm = 90.0

    measured_duration = duration_seconds or _duration_from_events(events) or 0.0
    bar_seconds = 60.0 / resolved_bpm * beats_per_bar
    bar_count = max(1, int(math.ceil(measured_duration / bar_seconds))) if measured_duration > 0 else 1
    if max_bars:
        bar_count = min(bar_count, max(1, int(max_bars)))

    intervals = _event_intervals(events, measured_duration or bar_seconds * bar_count)
    bars: list[dict[str, Any]] = []
    previous_chord = None

    for bar_index in range(bar_count):
        start = bar_index * bar_seconds
        end = start + bar_seconds
        segments: list[dict[str, Any]] = []
        for interval in intervals:
            overlap = max(0.0, min(end, interval["end"]) - max(start, interval["start"]))
            if overlap < 0.12:
                continue
            chord = interval["chord"]
            previous_chord = chord
            segment_start = max(start, interval["start"])
            segment_end = min(end, interval["end"])
            _append_bar_segment(
                segments,
                {
                    "chord": chord,
                    "start_seconds": round(segment_start, 3),
                    "end_seconds": round(segment_end, 3),
                    "start": _format_time(segment_start),
                    "end": _format_time(segment_end),
                    "duration_seconds": round(overlap, 3),
                    "source": interval.get("source"),
                    "confidence": interval.get("confidence"),
                },
            )
        if not segments and previous_chord:
            _append_bar_segment(
                segments,
                {
                    "chord": previous_chord,
                    "start_seconds": round(start, 3),
                    "end_seconds": round(end, 3),
                    "start": _format_time(start),
                    "end": _format_time(end),
                    "duration_seconds": round(end - start, 3),
                    "source": "carry-forward",
                    "confidence": None,
                },
            )
        if not segments:
            continue

        chords = [segment["chord"] for segment in segments]
        chord_label = " / ".join(chords)
        bars.append(
            {
                "bar": bar_index + 1,
                "chord": chord_label,
                "chords": segments,
                "time": _format_time(start),
                "end": _format_time(end),
                "start_seconds": round(start, 3),
                "end_seconds": round(end, 3),
            }
        )
    return bars


def analyze_audio(payload: dict[str, Any]) -> dict[str, Any]:
    audio_path = Path(str(payload.get("audio_path") or payload.get("audio") or "")).expanduser()
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file does not exist: {audio_path}")

    helpers = _load_chordcraft_audio_helpers()
    chord_engine = str(payload.get("chord_engine") or "plkd-btc")
    fallback_engine = str(payload.get("fallback_chord_engine") or "essentia")
    raw_events: list[dict[str, Any]]
    recognition_error = None
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            raw_events = helpers["recognize_chords"](str(audio_path), engine=chord_engine)
        used_engine = chord_engine
    except Exception as exc:
        recognition_error = str(exc)
        if not fallback_engine or fallback_engine == chord_engine:
            raise
        with contextlib.redirect_stdout(io.StringIO()):
            raw_events = helpers["recognize_chords"](str(audio_path), engine=fallback_engine)
        used_engine = fallback_engine

    processed_events = helpers["postprocess_chord_events"](
        raw_events,
        key=payload.get("key"),
        min_duration_seconds=float(payload.get("min_chord_duration_seconds") or 1.0),
    )
    metadata = helpers["estimate_song_metadata"](str(audio_path), processed_events)
    key = str(payload.get("key") or "").strip()
    if not key:
        metadata_key = metadata.get("key")
        metadata_mode = metadata.get("mode") or "major"
        key = f"{metadata_key} {metadata_mode}" if metadata_key else "C major"

    tempo_bpm = payload.get("tempo_bpm") or metadata.get("tempo_bpm") or 90
    time_signature = str(payload.get("time_signature") or metadata.get("time_signature") or "4/4")
    duration_seconds = helpers["probe_audio_duration"](str(audio_path)) or _duration_from_events(processed_events)
    bars = events_to_measure_bars(
        processed_events,
        key=key,
        bpm=float(tempo_bpm),
        time_signature=time_signature,
        duration_seconds=float(duration_seconds) if duration_seconds else None,
        max_bars=payload.get("max_bars"),
    )

    enriched_payload = {
        **payload,
        "title": payload.get("title") or audio_path.stem,
        "key": key,
        "time_signature": time_signature,
        "bars": bars,
    }
    result = analyze_progression(enriched_payload)
    result["audio_analysis"] = {
        "audio_path": str(audio_path),
        "chord_engine": used_engine,
        "fallback_from": chord_engine if recognition_error else None,
        "fallback_reason": recognition_error,
        "raw_event_count": len(raw_events),
        "event_count": len(processed_events),
        "tempo_bpm": tempo_bpm,
        "duration_seconds": duration_seconds,
        "metadata": metadata,
    }
    return result


def detect_cadences(bars: list[dict[str, Any]]) -> list[str]:
    cadences = []
    romans = [str(item.get("roman") or "") for item in bars]
    for index in range(1, len(romans)):
        pair = (romans[index - 1].rstrip("7"), romans[index].rstrip("7"))
        if pair in {("V", "I"), ("V", "i")}:
            cadences.append(f"bar {index} -> {index + 1}: authentic cadence")
        if pair in {("IV", "I"), ("iv", "i")}:
            cadences.append(f"bar {index} -> {index + 1}: plagal cadence")
        if pair in {("ii", "V"), ("ii°", "V"), ("iv", "V")}:
            cadences.append(f"bar {index} -> {index + 1}: predominant to dominant")
    return cadences


def render_html(result: dict[str, Any], columns: int) -> str:
    title = html.escape(str(result["summary"].get("title") or "Harmony Chart"))
    key = html.escape(str(result["summary"].get("key") or ""))
    cards = []
    for row in rows(result["bars"], columns):
        cells = []
        for item in row:
            segment_html = ""
            if isinstance(item.get("chords"), list) and len(item["chords"]) > 1:
                segment_html = "<div class='segments'>" + "".join(
                    f"<b>{html.escape(str(segment.get('chord') or ''))}</b>"
                    for segment in item["chords"]
                ) + "</div>"
            cells.append(
                "<div class='bar'>"
                f"<span>{html.escape(str(item['bar']))}</span>"
                f"<strong>{html.escape(str(item['chord']))}</strong>"
                f"<em>{html.escape(str(item['roman']))}</em>"
                f"<small>{html.escape(str(item['function']))}</small>"
                f"{segment_html}"
                "</div>"
            )
        cards.append("<div class='row'>" + "".join(cells) + "</div>")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{title}</title>
<style>
body {{ margin: 0; padding: 28px; background: #edf5ff; font-family: Inter, Arial, sans-serif; color: #10233f; }}
.sheet {{ max-width: 980px; margin: 0 auto; background: #fff; border: 1px solid #c7dcf7; border-radius: 18px; padding: 22px; box-shadow: 0 20px 45px rgba(29, 83, 148, .14); }}
header {{ display: flex; justify-content: space-between; gap: 16px; border-bottom: 1px solid #dce9fb; padding-bottom: 14px; margin-bottom: 16px; }}
h1 {{ margin: 0; font-size: 24px; }}
header span {{ color: #4777b0; font-weight: 800; }}
.row {{ display: grid; grid-template-columns: repeat({columns}, minmax(0, 1fr)); gap: 10px; margin-bottom: 10px; }}
.bar {{ min-height: 104px; border: 1px solid #cfe1f8; border-radius: 12px; background: linear-gradient(180deg, #f9fcff, #edf6ff); padding: 10px; display: grid; gap: 5px; }}
.bar span {{ color: #6e8ab1; font-size: 12px; font-weight: 900; }}
.bar strong {{ font-size: 24px; }}
.bar em {{ font-style: normal; color: #1769d8; font-weight: 900; }}
.bar small {{ color: #557397; font-weight: 800; }}
.segments {{ display: flex; flex-wrap: wrap; gap: 4px; margin-top: 2px; }}
.segments b {{ display: inline-flex; min-height: 20px; align-items: center; border-radius: 999px; background: #dcecff; color: #174a8d; padding: 1px 7px; font-size: 11px; }}
</style>
</head>
<body><main class="sheet"><header><h1>{title}</h1><span>{key}</span></header>{''.join(cards)}</main></body>
</html>
"""


def _analyze_bar_item(item: dict[str, Any], key: str) -> dict[str, Any]:
    segments = item.get("chords")
    if isinstance(segments, list) and segments:
        analyzed_segments = []
        roman_parts = []
        function_parts = []
        for segment in segments:
            chord = normalize_chord(segment.get("chord"))
            roman, function = roman_for_chord(chord, key)
            analyzed_segments.append(
                {
                    **segment,
                    "chord": chord,
                    "roman": roman,
                    "function": function,
                    "quality": quality(chord),
                }
            )
            roman_parts.append(roman)
            function_parts.append(function)
        chord_label = " / ".join(segment["chord"] for segment in analyzed_segments)
        return {
            **item,
            "chord": item.get("chord") or chord_label,
            "chords": analyzed_segments,
            "roman": " / ".join(roman_parts),
            "function": " / ".join(function_parts),
            "quality": "mixed" if len({segment["quality"] for segment in analyzed_segments}) > 1 else analyzed_segments[0]["quality"],
        }

    chord = normalize_chord(item.get("chord"))
    roman, function = roman_for_chord(chord, key)
    return {
        **item,
        "chord": chord,
        "roman": roman,
        "function": function,
        "quality": quality(chord),
    }


def analyze_progression(payload: dict[str, Any]) -> dict[str, Any]:
    key_root, mode = parse_key(payload.get("key"))
    key = f"{key_root} {mode}"
    columns = max(1, min(int(payload.get("columns") or 4), 8))
    bars = coerce_bars(payload)
    analyzed = []
    for item in bars:
        analyzed.append(_analyze_bar_item(item, key))
    result = {
        "summary": {
            "title": payload.get("title") or "Harmony Chart",
            "key": key,
            "mode": mode,
            "section": payload.get("section"),
            "time_signature": payload.get("time_signature") or "4/4",
            "bar_count": len(analyzed),
            "main_loop": " - ".join(item["roman"] for item in analyzed[:8]),
        },
        "bars": analyzed,
        "progression_text": grid_text(analyzed, "chord", columns),
        "roman_text": grid_text(analyzed, "roman", columns),
        "functions_text": grid_text(analyzed, "function", columns),
        "cadences": detect_cadences(analyzed),
    }
    if payload.get("output_html"):
        result["html"] = render_html(result, columns)
    return result


def analyze(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("audio_path") or payload.get("audio"):
        return analyze_audio(payload)
    return analyze_progression(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze harmony and render a measure chart.")
    parser.add_argument("--audio", help="Audio file path. Runs chord recognition before harmony analysis.")
    parser.add_argument("--input-json", help="Inline JSON input.")
    parser.add_argument("--input-file", help="Path to JSON input file.")
    parser.add_argument("--chord-engine", default="plkd-btc", help="Audio mode chord engine: plkd-btc, plkd-btc-pl, plkd-btc-sl, or essentia.")
    parser.add_argument("--fallback-chord-engine", default="essentia", help="Fallback chord engine when the primary engine fails.")
    parser.add_argument("--key", help="Optional key override, e.g. E major or C minor.")
    parser.add_argument("--tempo-bpm", type=float, help="Optional tempo override.")
    parser.add_argument("--time-signature", default=None, help="Optional meter override. Defaults to 4/4.")
    parser.add_argument("--max-bars", type=int, help="Limit rendered bars for quick inspection.")
    parser.add_argument("--json-output", help="Optional JSON output path.")
    parser.add_argument("--html-output", help="Optional HTML output path.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON.")
    args = parser.parse_args()
    if not args.audio and not args.input_json and not args.input_file:
        parser.error("Provide --audio, --input-json, or --input-file.")
    payload = json.loads(args.input_json) if args.input_json else load_json(Path(args.input_file)) if args.input_file else {}
    if args.audio:
        payload["audio_path"] = args.audio
        payload["chord_engine"] = args.chord_engine
        payload["fallback_chord_engine"] = args.fallback_chord_engine
    if args.key:
        payload["key"] = args.key
    if args.tempo_bpm:
        payload["tempo_bpm"] = args.tempo_bpm
    if args.time_signature:
        payload["time_signature"] = args.time_signature
    if args.max_bars:
        payload["max_bars"] = args.max_bars
    result = analyze(payload)
    if args.html_output:
        if "html" not in result:
            result["html"] = render_html(result, max(1, min(int(payload.get("columns") or 4), 8)))
        Path(args.html_output).write_text(result["html"], encoding="utf-8")
    if args.json_output:
        Path(args.json_output).write_text(
            json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None),
            encoding="utf-8",
        )
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
