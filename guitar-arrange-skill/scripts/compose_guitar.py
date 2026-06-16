#!/usr/bin/env python3
"""High-level guitar harmony arranger.

This script accepts a broad natural-language request plus optional structured
constraints. It plans a chord progression, then delegates capo/voicing/rendering
to arrange_guitar.py.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from arrange_guitar import arrange


SUPPORTED_STYLES = {"pop", "rock", "rnb", "blues", "funk"}
SUPPORTED_LEVELS = {"beginner", "intermediate"}
DEFAULT_KEY = "C major"

PITCHES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
PITCHES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
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
MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]
MAJOR_TRIADS = ["", "m", "m", "", "", "m", "dim"]
MINOR_TRIADS = ["m", "dim", "", "m", "m", "", ""]

STYLE_ALIASES = {
    "pop": ["pop", "流行", "民谣", "弹唱"],
    "rock": ["rock", "摇滚", "朋克", "power"],
    "rnb": ["rnb", "r&b", "r b", "neo soul", "neosoul", "灵魂"],
    "blues": ["blues", "布鲁斯", "蓝调", "十二小节", "12bar", "12 bar"],
    "funk": ["funk", "放克", "律动"],
}
SECTION_ALIASES = {
    "intro": ["intro", "前奏"],
    "verse": ["verse", "主歌"],
    "pre_chorus": ["pre chorus", "pre-chorus", "预副歌", "导歌"],
    "chorus": ["chorus", "副歌", "高潮"],
    "bridge": ["bridge", "桥段"],
    "outro": ["outro", "尾奏"],
    "interlude": ["interlude", "间奏"],
    "12bar": ["12bar", "12 bar", "十二小节"],
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


def prefer_flats(key: str) -> bool:
    root, _mode = parse_key(key)
    return "b" in root or root in {"F", "Bb", "Eb", "Ab", "Db", "Gb"}


def pitch_name(pc: int, use_flats: bool) -> str:
    return (PITCHES_FLAT if use_flats else PITCHES_SHARP)[pc % 12]


def parse_key(value: Any) -> tuple[str, str]:
    text = str(value or DEFAULT_KEY).strip().replace("♯", "#").replace("♭", "b")
    parts = text.split()
    root = normalize_symbol(parts[0]) if parts else "C"
    mode_text = " ".join(parts[1:]).lower()
    mode = "minor" if mode_text in {"minor", "min", "m", "小调", "小"} or "minor" in mode_text else "major"
    if root not in PC:
        return "C", "major"
    return root, mode


def key_text(root: str, mode: str) -> str:
    return f"{root} {mode}"


def chord_from_degree(key: str, degree: int, quality_override: str | None = None) -> str:
    root, mode = parse_key(key)
    use_flats = prefer_flats(key)
    scale = MINOR_SCALE if mode == "minor" else MAJOR_SCALE
    qualities = MINOR_TRIADS if mode == "minor" else MAJOR_TRIADS
    index = (degree - 1) % 7
    chord_root = pitch_name(PC[root] + scale[index], use_flats)
    suffix = quality_override if quality_override is not None else qualities[index]
    return f"{chord_root}{suffix}"


def roman_to_chord(key: str, roman: str) -> str:
    text = roman.strip()
    quality_override = None
    if text.endswith("7"):
        text = text[:-1]
        quality_override = "7"
    degree_map = {
        "I": 1,
        "II": 2,
        "III": 3,
        "IV": 4,
        "V": 5,
        "VI": 6,
        "VII": 7,
        "i": 1,
        "ii": 2,
        "iii": 3,
        "iv": 4,
        "v": 5,
        "vi": 6,
        "vii": 7,
    }
    degree = degree_map.get(text)
    if degree is None:
        return roman
    if text.islower() and quality_override is None:
        quality_override = "m"
    return chord_from_degree(key, degree, quality_override)


def parse_chord_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [normalize_symbol(item) for item in value if normalize_symbol(item)]
    if not isinstance(value, str):
        return []
    parts = re.split(r"[\s,|>]+|(?:\s*-\s*)", value.strip())
    return [normalize_symbol(part) for part in parts if normalize_symbol(part)]


def text_contains(text: str, words: list[str]) -> bool:
    low = text.lower()
    return any(word.lower() in low for word in words)


def infer_style(request: str, context: dict[str, Any]) -> str:
    value = str(context.get("style") or "").lower()
    if value in SUPPORTED_STYLES:
        return value
    for style, aliases in STYLE_ALIASES.items():
        if text_contains(request, aliases):
            return style
    return "pop"


def infer_section(request: str, context: dict[str, Any], style: str) -> str:
    value = str(context.get("section") or "").lower()
    if value in {"intro", "verse", "pre_chorus", "chorus", "bridge", "interlude", "outro"}:
        return value
    if value == "12bar":
        return "chorus"
    for section, aliases in SECTION_ALIASES.items():
        if text_contains(request, aliases):
            return "chorus" if section == "12bar" else section
    if style == "blues" and text_contains(request, ["12", "十二小节"]):
        return "chorus"
    return "chorus"


def infer_level(request: str, constraints: dict[str, Any]) -> str:
    value = str(constraints.get("user_level") or "").lower()
    if value in SUPPORTED_LEVELS:
        return value
    if text_contains(request, ["初学", "新手", "简单", "不要太难", "beginner", "easy"]):
        return "beginner"
    return "intermediate"


def infer_key(request: str, context: dict[str, Any], style: str) -> str:
    if context.get("key"):
        root, mode = parse_key(context["key"])
        return key_text(root, mode)
    text = request.replace("＃", "#").replace("♯", "#").replace("♭", "b")
    match = re.search(r"(?:key\s+of|in)\s+([A-G](?:#|b)?)\s*(major|minor|maj|min)\b", text, re.I)
    if match:
        root = normalize_symbol(match.group(1))
        mode_token = match.group(2).lower()
        mode = "minor" if mode_token in {"minor", "min"} else "major"
        return key_text(root, mode)
    match = re.search(r"\b([A-G](?:#|b)?)\s*(major|minor)\s+key\b", text, re.I)
    if match:
        root = normalize_symbol(match.group(1))
        mode = "minor" if match.group(2).lower() == "minor" else "major"
        return key_text(root, mode)
    match = re.search(r"([A-G](?:#|b)?)[\s-]*(大调|小调)", text)
    if match:
        return key_text(normalize_symbol(match.group(1)), "minor" if match.group(2) == "小调" else "major")
    if style == "blues":
        return "E minor" if text_contains(request, ["小调", "minor", "minor blues"]) else "E major"
    return DEFAULT_KEY


def infer_bar_count(request: str, context: dict[str, Any], style: str) -> int:
    if isinstance(context.get("bar_count"), int) and context["bar_count"] > 0:
        return int(context["bar_count"])
    match = re.search(r"(\d+)\s*(?:bar|bars|小节)", request, re.I)
    if match:
        return max(1, int(match.group(1)))
    if style == "blues" and text_contains(request, ["12", "十二小节", "12bar", "12 bar"]):
        return 12
    return 8


def infer_capo_policy(request: str, constraints: dict[str, Any]) -> tuple[str, int | None]:
    if isinstance(constraints.get("preferred_capo"), int):
        return "fixed", int(constraints["preferred_capo"])
    policy = str(constraints.get("capo_policy") or "").lower()
    if policy in {"auto", "no_capo", "prefer_capo", "fixed"}:
        return policy, None
    if text_contains(request, ["不用变调夹", "不要变调夹", "no capo", "不使用 capo", "不使用变调夹"]):
        return "no_capo", 0
    if text_contains(request, ["变调夹", "capo"]):
        return "auto", None
    return "auto", None


def infer_color_level(request: str, goal: dict[str, Any], style: str) -> str:
    value = str(goal.get("color_level") or "").lower()
    if value in {"plain", "light", "colorful"}:
        return value
    if style in {"rnb", "funk"} or text_contains(request, ["高级", "丰富", "r&b", "rnb", "爵士", "jazz", "colorful"]):
        return "colorful"
    if text_contains(request, ["简单", "朴素", "plain", "三和弦"]):
        return "plain"
    return "light"


def has_minor_quality(chord: str) -> bool:
    _root, suffix = split_chord(chord)
    low = suffix.lower()
    return low.startswith("m") and not low.startswith("maj")


def scale_degree_interval(chord: str, key: str) -> int | None:
    key_root, _mode = parse_key(key)
    chord_root, _suffix = split_chord(chord)
    if key_root not in PC or chord_root not in PC:
        return None
    return (PC[chord_root] - PC[key_root]) % 12


def colorize_chord(chord: str, style: str, color_level: str) -> str:
    if color_level == "plain":
        return chord
    root, suffix = split_chord(chord)
    low = suffix.lower()
    if any(token in low for token in ["7", "9", "sus", "add", "dim", "aug"]):
        return chord
    if style == "rnb":
        return f"{root}m7" if has_minor_quality(chord) else f"{root}maj7"
    if style == "blues":
        if has_minor_quality(chord):
            return f"{root}m7"
        return f"{root}7"
    if style == "funk":
        return f"{root}m7" if has_minor_quality(chord) else f"{root}7"
    if style == "pop" and color_level == "colorful":
        return f"{root}m7" if has_minor_quality(chord) else f"{root}add9"
    return chord


def colorize_chord_in_key(chord: str, key: str, style: str, color_level: str) -> str:
    if color_level == "plain":
        return chord
    root, suffix = split_chord(chord)
    low = suffix.lower()
    if any(token in low for token in ["7", "9", "sus", "add", "dim", "aug"]):
        return chord
    interval = scale_degree_interval(chord, key)
    if style == "rnb" and interval == 7 and not has_minor_quality(chord):
        return f"{root}7"
    if style in {"blues", "funk"} and interval == 7 and not has_minor_quality(chord):
        return f"{root}7"
    return colorize_chord(chord, style, color_level)


def expand_to_bars(chords: list[str], bar_count: int) -> list[str]:
    if not chords:
        return []
    return [chords[index % len(chords)] for index in range(bar_count)]


def plan_progression(
    key: str,
    style: str,
    section: str,
    bar_count: int,
    color_level: str,
    source_chords: list[str],
    request: str,
) -> tuple[list[str], dict[str, Any]]:
    if source_chords:
        chords = [colorize_chord_in_key(chord, key, style, color_level) for chord in source_chords]
        return chords, {"source": "source_chords", "template": "user_supplied"}

    root, mode = parse_key(key)
    if style == "blues" and bar_count == 12:
        if mode == "minor":
            i = f"{root}m7"
            iv = colorize_chord(chord_from_degree(key, 4), "blues", "colorful")
            v = chord_from_degree(key, 5, "7")
            return [i, i, i, i, iv, iv, i, i, v, iv, i, v], {"source": "template", "template": "minor_12_bar_blues"}
        i7 = chord_from_degree(key, 1, "7")
        iv7 = chord_from_degree(key, 4, "7")
        v7 = chord_from_degree(key, 5, "7")
        return [i7, i7, i7, i7, iv7, iv7, i7, i7, v7, iv7, i7, v7], {"source": "template", "template": "major_12_bar_blues"}

    templates = {
        "pop": ["I", "V", "vi", "IV"] if section == "chorus" else ["vi", "IV", "I", "V"],
        "rock": ["I", "bVII", "IV", "I"],
        "rnb": ["I", "vi", "ii", "V"],
        "funk": ["i", "iv", "i", "V7"] if mode == "minor" else ["I7", "IV7", "I7", "V7"],
        "blues": ["I7", "IV7", "I7", "V7"],
    }
    roman_template = templates.get(style, templates["pop"])
    chords = []
    for roman in roman_template:
        if roman == "bVII":
            root_pc = PC[root]
            chords.append(f"{pitch_name(root_pc + 10, prefer_flats(key))}")
        else:
            chords.append(roman_to_chord(key, roman))
    chords = [colorize_chord_in_key(chord, key, style, color_level) for chord in chords]
    return expand_to_bars(chords, min(bar_count, 16)), {"source": "template", "template": f"{style}_{section}_{mode}"}


def compact_progression(chords: list[str]) -> list[str]:
    if len(chords) <= 8:
        return chords
    result = []
    for chord in chords:
        if chord not in result:
            result.append(chord)
    return result


def chord_degree(chord: str, key: str) -> str:
    key_root, mode = parse_key(key)
    chord_root, suffix = split_chord(chord)
    if key_root not in PC or chord_root not in PC:
        return ""
    interval = (PC[chord_root] - PC[key_root]) % 12
    major_map = {0: "I", 2: "ii", 4: "iii", 5: "IV", 7: "V", 9: "vi", 11: "vii dim"}
    minor_map = {0: "i", 2: "ii dim", 3: "III", 5: "iv", 7: "v", 8: "VI", 10: "VII"}
    degree = (minor_map if mode == "minor" else major_map).get(interval, str(interval))
    if mode == "minor" and interval == 7 and not has_minor_quality(chord):
        degree = "V"
    low = suffix.lower()
    if "maj7" in low:
        return f"{degree}maj7"
    if "m7b5" in low:
        return f"{degree}7b5"
    if "7" in low:
        return f"{degree}7"
    if "9" in low:
        return f"{degree}9"
    if "sus" in low:
        return f"{degree}sus"
    return degree


def bars_from_chords(chords: list[str], key: str, section: str = "section") -> list[dict[str, Any]]:
    return [
        {
            "bar": index + 1,
            "section": section,
            "chord": chord,
            "degree": chord_degree(chord, key),
        }
        for index, chord in enumerate(chords)
    ]


def progression_grid(chords: list[str], key: str, columns: int = 4) -> dict[str, Any]:
    bars = bars_from_chords(chords, key)
    rows = [bars[index : index + columns] for index in range(0, len(bars), columns)]
    return {
        "columns": columns,
        "rows": rows,
        "text": "\n".join("| " + " | ".join(bar["chord"] for bar in row) + " |" for row in rows),
        "degrees_text": "\n".join("| " + " | ".join(bar["degree"] for bar in row) + " |" for row in rows),
    }


def make_practice_text(result: dict[str, Any], plan: dict[str, Any]) -> str:
    lines = [
        "AI-ChordCraft Guitar Lead Sheet",
        f"Key: {plan['key']}    Style: {plan['style']}    Capo: {result.get('capo', 0)}",
        "",
        "Progression:",
        progression_grid(plan["planned_chords"], plan["key"])["text"],
        "",
        "Degrees:",
        progression_grid(plan["planned_chords"], plan["key"])["degrees_text"],
        "",
        "Voicings:",
    ]
    for item in result.get("voicings", []):
        lines.append(
            f"- {item.get('chord')}: {item.get('shape')} "
            f"(commonness={item.get('commonness')}, status={item.get('annotation_status')})"
        )
    return "\n".join(lines) + "\n"


def make_chordpro_full(result: dict[str, Any], plan: dict[str, Any]) -> str:
    lines = [
        f"{{title: {result.get('title', 'AI-ChordCraft Guitar Arrangement')}}}",
        f"{{key: {plan['key']}}}",
        f"{{capo: {result.get('capo', 0)}}}",
        f"{{tempo: {result.get('bpm', '')}}}",
        "",
        f"{{start_of_{plan['section']}}}",
    ]
    grid = progression_grid(plan["planned_chords"], plan["key"])
    for row in grid["rows"]:
        lines.append(" ".join(f"[{bar['chord']}]" for bar in row))
    lines.extend([f"{{end_of_{plan['section']}}}", ""])
    return "\n".join(lines)


def make_voicing_summary(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "chord": item.get("chord"),
            "shape": item.get("shape"),
            "frets": item.get("frets"),
            "barres": item.get("barres", []),
            "difficulty": item.get("difficulty"),
            "commonness": item.get("commonness"),
            "status": item.get("annotation_status"),
            "contexts": item.get("annotation_contexts", []),
        }
        for item in result.get("voicings", [])
    ]


def build_diverse_exports(result: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    grid = progression_grid(plan["planned_chords"], plan["key"])
    return {
        "progression_grid": grid,
        "lead_sheet": {
            "title": result.get("title", "AI-ChordCraft Guitar Arrangement"),
            "key": plan["key"],
            "style": plan["style"],
            "section": plan["section"],
            "bar_count": plan["bar_count"],
            "capo": result.get("capo", 0),
            "play_as_key": result.get("play_as_key"),
            "bars": bars_from_chords(plan["planned_chords"], plan["key"], plan["section"]),
            "unique_voicings": make_voicing_summary(result),
        },
        "practice_text": make_practice_text(result, plan),
        "chordpro_full": make_chordpro_full(result, plan),
        "voicing_summary": make_voicing_summary(result),
    }


def write_export_files(result: dict[str, Any], export_dir: Path) -> dict[str, str]:
    export_dir.mkdir(parents=True, exist_ok=True)
    exports = result.get("exports", {})
    files = {
        "result_json": export_dir / "arrangement.json",
        "lead_sheet_json": export_dir / "lead_sheet.json",
        "practice_text": export_dir / "practice_sheet.txt",
        "chordpro": export_dir / "arrangement.cho",
        "voicing_summary": export_dir / "voicing_summary.json",
    }
    files["lead_sheet_json"].write_text(json.dumps(exports.get("lead_sheet", {}), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files["practice_text"].write_text(str(exports.get("practice_text", "")), encoding="utf-8")
    files["chordpro"].write_text(str(exports.get("chordpro_full") or exports.get("chordpro") or ""), encoding="utf-8")
    files["voicing_summary"].write_text(json.dumps(exports.get("voicing_summary", []), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    file_map = {key: str(path) for key, path in files.items()}
    result.setdefault("exports", {})["files"] = file_map
    files["result_json"].write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return file_map


def normalize_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    request = str(payload.get("request") or payload.get("goal") or "").strip()
    music_context = payload.get("music_context") if isinstance(payload.get("music_context"), dict) else {}
    harmony_goal = payload.get("harmony_goal") if isinstance(payload.get("harmony_goal"), dict) else {}
    guitar_constraints = payload.get("guitar_constraints") if isinstance(payload.get("guitar_constraints"), dict) else {}

    # Backward-compatible aliases.
    for key in ["key", "style", "section", "bar_count", "time_signature", "tempo", "bpm"]:
        if key in payload and key not in music_context:
            music_context[key] = payload[key]
    for key in ["user_level", "preferred_capo", "capo_policy", "known_chords"]:
        if key in payload and key not in guitar_constraints:
            guitar_constraints[key] = payload[key]

    style = infer_style(request, music_context)
    key = infer_key(request, music_context, style)
    section = infer_section(request, music_context, style)
    level = infer_level(request, guitar_constraints)
    bar_count = infer_bar_count(request, music_context, style)
    color_level = infer_color_level(request, harmony_goal, style)
    capo_policy, inferred_capo = infer_capo_policy(request, guitar_constraints)
    source_chords = parse_chord_list(payload.get("source_chords") or payload.get("chords"))
    planned_chords, plan = plan_progression(key, style, section, bar_count, color_level, source_chords, request)
    arranger_chords = compact_progression(planned_chords)

    preferred_capo = guitar_constraints.get("preferred_capo")
    if capo_policy == "no_capo":
        preferred_capo = 0
    elif inferred_capo is not None:
        preferred_capo = inferred_capo
    elif not isinstance(preferred_capo, int):
        preferred_capo = None

    return {
        "task": "guitar_arrange",
        "title": str(payload.get("title") or "AI-ChordCraft Guitar Arrangement"),
        "key": key,
        "bpm": int(music_context.get("bpm") or music_context.get("tempo") or payload.get("bpm") or 92),
        "time_signature": str(music_context.get("time_signature") or payload.get("time_signature") or "4/4"),
        "section": section,
        "style": style,
        "user_level": level,
        "goal": request or str(payload.get("goal") or "根据用户描述生成吉他和声编配"),
        "chords": arranger_chords,
        "preferred_capo": preferred_capo,
        "known_chords": guitar_constraints.get("known_chords") or payload.get("known_chords") or [],
        "_composition_plan": {
            **plan,
            "request": request,
            "style": style,
            "key": key,
            "section": section,
            "bar_count": bar_count,
            "color_level": color_level,
            "capo_policy": capo_policy,
            "planned_chords": planned_chords,
            "arranger_chords": arranger_chords,
        },
    }


def compose(payload: dict[str, Any]) -> dict[str, Any]:
    arranger_payload = normalize_request_payload(payload)
    plan = arranger_payload.pop("_composition_plan")
    result = arrange(arranger_payload)
    result["composition"] = {
        "request": plan["request"],
        "source": plan["source"],
        "template": plan["template"],
        "planned_chords": plan["planned_chords"],
        "arranger_chords": plan["arranger_chords"],
        "music_context": {
            "key": plan["key"],
            "style": plan["style"],
            "section": plan["section"],
            "bar_count": plan["bar_count"],
            "color_level": plan["color_level"],
            "capo_policy": plan["capo_policy"],
        },
    }
    result.setdefault("exports", {}).update(build_diverse_exports(result, plan))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Compose and arrange guitar harmony from a broad request.")
    parser.add_argument("--input-json", help="Inline JSON input.")
    parser.add_argument("--input-file", help="Path to JSON input file.")
    parser.add_argument("--diagram-png-output", help="Optional PNG path for rendered selected chord diagrams.")
    parser.add_argument("--diagram-columns", type=int, default=4, help="Number of columns in the optional diagram PNG.")
    parser.add_argument("--include-duplicate-diagrams", action="store_true", help="Render repeated chord/shape pairs in PNG.")
    parser.add_argument("--export-dir", help="Optional directory for JSON, ChordPro, and text exports.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON.")
    args = parser.parse_args()

    if not args.input_json and not args.input_file:
        parser.error("Provide --input-json or --input-file.")
    payload = json.loads(args.input_json) if args.input_json else load_json(Path(args.input_file))
    output = compose(payload)
    if args.diagram_png_output:
        from render_chord_diagrams import render_chord_diagrams_png

        png_path = render_chord_diagrams_png(
            output,
            Path(args.diagram_png_output),
            columns=args.diagram_columns,
            include_duplicates=args.include_duplicate_diagrams,
        )
        output["exports"]["chord_diagrams_png"] = str(png_path)
    if args.export_dir:
        write_export_files(output, Path(args.export_dir))
    print(json.dumps(output, ensure_ascii=False, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
