#!/usr/bin/env python3
"""Guitar harmony and voicing arranger for AI-ChordCraft musician skills."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VOICING_DIR = ROOT / "resources" / "voicing_db"
VOICINGS_PATH = VOICING_DIR / "source" / "chords_db_voicings.json"
VOICING_ANNOTATIONS_PATH = VOICING_DIR / "overlays" / "commonness_annotations.json"
STYLE_CARDS_DIR = ROOT / "resources" / "style_cards"
RULES_DIR = ROOT / "resources" / "rules"

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
OPEN_STRING_PCS = [4, 9, 2, 7, 11, 4]
LEVEL_ORDER = {"beginner": 1, "intermediate": 2}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_voicings() -> list[dict[str, Any]]:
    payload = load_json(VOICINGS_PATH)
    if isinstance(payload, dict) and isinstance(payload.get("voicings"), list):
        return apply_voicing_annotations(payload["voicings"])
    if isinstance(payload, list):
        return apply_voicing_annotations(payload)
    raise ValueError(f"Invalid voicing database format: {VOICINGS_PATH}")


def merge_voicings(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = []
    seen = set()
    for group in groups:
        for item in group:
            symbol = normalize_symbol(item.get("symbol"))
            frets = tuple(item.get("frets") or [])
            key = (symbol, frets)
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def voicing_annotation_key(symbol: str, frets: list[Any]) -> str:
    return f"{normalize_symbol(symbol)}|{','.join(str(int(fret)) for fret in frets[:6] if isinstance(fret, int))}"


def load_voicing_annotations() -> dict[str, Any]:
    if not VOICING_ANNOTATIONS_PATH.exists():
        return {}
    payload = load_json(VOICING_ANNOTATIONS_PATH)
    if not isinstance(payload, dict):
        return {}
    annotations = payload.get("annotations") or {}
    return annotations if isinstance(annotations, dict) else {}


def apply_voicing_annotations(voicings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annotations = load_voicing_annotations()
    if not annotations:
        return voicings
    result = []
    for item in voicings:
        frets = item.get("frets") or []
        symbol = normalize_symbol(item.get("symbol"))
        if len(frets) == 6:
            annotation = annotations.get(voicing_annotation_key(symbol, frets))
            if annotation:
                result.append({**item, "annotation": annotation})
                continue
        result.append(item)
    return result


def load_rules() -> dict[str, Any]:
    return {
        "capo": load_json(RULES_DIR / "capo_rules.json"),
        "voicing": load_json(RULES_DIR / "voicing_scoring_rules.json"),
        "playability": load_json(RULES_DIR / "playability_rules.json"),
        "simplification": load_json(RULES_DIR / "simplification_rules.json"),
        "validation": load_json(RULES_DIR / "validation_rules.json"),
        "practice_notes": load_json(RULES_DIR / "practice_note_rules.json"),
    }


def normalize_symbol(symbol: Any) -> str:
    text = str(symbol or "").strip()
    text = text.replace("♯", "#").replace("♭", "b")
    if not text:
        return ""
    return text[0].upper() + text[1:]


def split_chord(symbol: str) -> tuple[str, str]:
    text = normalize_symbol(symbol)
    if len(text) >= 2 and text[:2] in PC:
        return text[:2], text[2:]
    return text[:1], text[1:]


def prefer_flats(key: str, chords: list[str]) -> bool:
    text = f"{key} {' '.join(chords)}"
    return "b" in text or any(root in text for root in ["F ", "Bb", "Eb", "Ab", "Db"])


def transpose_chord(symbol: str, semitones: int, use_flats: bool = False) -> str:
    root, suffix = split_chord(symbol)
    if root not in PC:
        return normalize_symbol(symbol)
    names = PITCHES_FLAT if use_flats else PITCHES_SHARP
    return f"{names[(PC[root] + semitones) % 12]}{suffix}"


def simplify_chord(symbol: str, level: str = "beginner", rules: dict[str, Any] | None = None) -> str:
    root, suffix = split_chord(symbol)
    if "/" in suffix and rules:
        slash_mode = (rules.get("slash_chords") or {}).get(level)
        if slash_mode == "drop_bass":
            suffix = suffix.split("/", 1)[0]
    low = suffix.lower()
    if rules:
        for rewrite in rules.get("quality_rewrites") or []:
            pattern = str(rewrite.get("pattern") or "").lower()
            if pattern and pattern in low:
                return f"{root}{rewrite.get(level, rewrite.get('beginner', ''))}"
    if low.startswith("m") and not low.startswith("maj"):
        return f"{root}m"
    return root


def transpose_key(key: str, semitones: int, use_flats: bool = False) -> str:
    parts = str(key or "").strip().split()
    if not parts:
        return ""
    root, suffix = split_chord(parts[0])
    mode = " ".join(parts[1:]) or "major"
    if root not in PC:
        return key
    names = PITCHES_FLAT if use_flats else PITCHES_SHARP
    return f"{names[(PC[root] + semitones) % 12]} {mode}".strip()


def voicing_index(voicings: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for item in voicings:
        symbol = normalize_symbol(item.get("symbol"))
        result.setdefault(symbol, []).append(item)
    return result


def has_voicing(chord: str, index: dict[str, list[dict[str, Any]]]) -> bool:
    return normalize_symbol(chord) in index or simplify_chord(chord) in index


def voicing_candidates(
    chord: str,
    index: dict[str, list[dict[str, Any]]],
    level: str = "beginner",
    simplification_rules: dict[str, Any] | None = None,
) -> tuple[str, list[dict[str, Any]], bool]:
    symbol = normalize_symbol(chord)
    if symbol in index:
        return symbol, index[symbol], False
    simplified = simplify_chord(symbol, level=level, rules=simplification_rules)
    return simplified, index.get(simplified, []), simplified != symbol


def capo_score(
    play_chords: list[str],
    capo: int,
    index: dict[str, list[dict[str, Any]]],
    level: str,
    known_chords: set[str],
    rules: dict[str, Any],
) -> float:
    capo_rules = rules["capo"]
    simplification_rules = rules["simplification"]
    weights = capo_rules["weights"]
    beginner_common = set(capo_rules.get("beginner_common_shapes") or [])
    score = 0.0
    for chord in play_chords:
        voicing_symbol, candidates, simplified = voicing_candidates(
            chord,
            index,
            level=level,
            simplification_rules=simplification_rules,
        )
        if not candidates:
            score += float(weights["missing_voicing"])
            continue
        best = min(candidates, key=lambda item: int(item.get("difficulty", 5)))
        tags = set(best.get("tags") or [])
        if "open" in tags:
            score += float(weights["open_chord"])
        if voicing_symbol in beginner_common:
            score += float(weights["beginner_common_shape"])
        if voicing_symbol in known_chords:
            score += float(weights["known_chord"])
        if best.get("barres"):
            score += float(weights["barre_beginner" if level == "beginner" else "barre_intermediate"])
        score += max(0, int(best.get("difficulty", 1)) - 2) * float(weights["difficulty_above_target"])
        if simplified:
            score += float(weights["simplified_chord"])
        suffix = split_chord(chord)[1]
        if "/" in suffix:
            score += float(weights.get("slash_chord_penalty", 0))
        if any(token in suffix.lower() for token in ["maj7", "m7b5", "add9", "sus", "dim", "aug"]):
            score += float(weights.get("complex_extension_penalty", 0))
    score -= capo * float(capo_rules["capo_penalty_per_fret"])
    if capo > int(capo_rules["high_capo_threshold"]):
        score -= float(capo_rules["high_capo_extra_penalty"])
    return score


def choose_capo(payload: dict[str, Any], index: dict[str, list[dict[str, Any]]], rules: dict[str, Any]) -> dict[str, Any]:
    chords = [normalize_symbol(chord) for chord in payload.get("chords") or []]
    use_flats = prefer_flats(payload.get("key", ""), chords)
    level = str(payload.get("user_level") or "beginner")
    known_chords = {normalize_symbol(chord) for chord in payload.get("known_chords") or []}
    preferred = payload.get("preferred_capo")
    max_capo = int(rules["capo"].get("max_capo", 5))
    capo_range = [int(preferred)] if isinstance(preferred, int) and 0 <= preferred <= max_capo else range(0, max_capo + 1)

    candidates = []
    for capo in capo_range:
        play_chords = [transpose_chord(chord, -capo, use_flats=use_flats) for chord in chords]
        score = capo_score(play_chords, capo, index, level, known_chords, rules)
        if isinstance(preferred, int) and capo == preferred:
            score += float(rules["capo"].get("preferred_capo_bonus", 0))
        candidates.append({"capo": capo, "display_chords": play_chords, "score": score})
    candidates.sort(key=lambda item: float(item["score"]), reverse=True)
    best = candidates[0]
    return {
        "capo": best["capo"],
        "display_chords": best["display_chords"],
        "play_as_key": transpose_key(str(payload.get("key") or ""), -int(best["capo"]), use_flats=use_flats),
    }


def voicing_score(
    item: dict[str, Any],
    style: str,
    level: str,
    style_card: dict[str, Any],
    rules: dict[str, Any],
    known_chords: set[str],
    modern_bonus: float = 0.0,
) -> float:
    scoring = rules["voicing"]
    weights = scoring["weights"]
    target_difficulty = int((scoring.get("target_difficulty") or {}).get(level, 2))
    score = 0.0
    tags = set(item.get("tags") or [])
    annotation = item.get("annotation") if isinstance(item.get("annotation"), dict) else {}
    preferred_tags = set(style_card.get("preferred_tags") or [])
    score += len(tags & preferred_tags) * float(weights["preferred_style_tag"])
    if "open" in tags:
        score += float(weights["open_string_bonus"])
    if "common" in tags:
        score += float(weights["common_shape_bonus"])
    if level == "beginner" and "beginner" in tags:
        score += float(weights["beginner_tag_bonus"])
    if style in item.get("best_for", []):
        score += float(weights["style_best_for"])
    if style in annotation.get("styles", []):
        score += float(weights.get("annotation_style_bonus", 0))
    commonness = annotation.get("commonness")
    if isinstance(commonness, int):
        score += commonness * float(weights.get("annotation_commonness_step_bonus", 0))
    status = annotation.get("status")
    if status == "preferred":
        score += float(weights.get("annotation_preferred_bonus", 0))
    elif status == "common":
        score += float(weights.get("annotation_common_bonus", 0))
    elif status == "rare":
        score += float(weights.get("annotation_rare_penalty", 0))
    elif status == "rejected":
        score += float(weights.get("annotation_rejected_penalty", 0))
    if normalize_symbol(item.get("symbol")) in known_chords:
        score += float(weights["known_chord_bonus"])
    if level in item.get("avoid_for", []):
        score += float(weights["avoid_for_penalty"])
    if item.get("barres"):
        score += float(weights["barre_beginner_penalty"] if level == "beginner" else weights["barre_intermediate_penalty"])
    score += max(0, int(item.get("difficulty", 1)) - target_difficulty) * float(weights["difficulty_step_penalty"])
    frets = [int(fret) for fret in item.get("frets", []) if isinstance(fret, int) and fret > 0]
    if frets:
        score += max(0, max(frets) - min(frets) - 3) * float(weights.get("fret_span_penalty", 0))
    score += max(0, int(item.get("position") or 1) - 1) * float(weights.get("position_penalty", 0))
    score += modern_bonus
    return score


def shape_from_frets(frets: list[Any]) -> str:
    return "".join("x" if not isinstance(fret, int) or fret < 0 else str(fret) for fret in frets)


def positive_frets(item: dict[str, Any]) -> list[int]:
    return [int(fret) for fret in item.get("frets", []) if isinstance(fret, int) and fret > 0]


def fret_center(item: dict[str, Any]) -> float:
    frets = positive_frets(item)
    if not frets:
        return 0.0
    return sum(frets) / len(frets)


def fretted_positions(item: dict[str, Any]) -> set[tuple[int, int]]:
    result = set()
    for string, fret in enumerate(item.get("frets", [])[:6]):
        if isinstance(fret, int) and fret > 0:
            result.add((string, fret))
    return result


def open_string_positions(item: dict[str, Any]) -> set[int]:
    return {
        string
        for string, fret in enumerate(item.get("frets", [])[:6])
        if isinstance(fret, int) and fret == 0
    }


def top_note_pitch(item: dict[str, Any]) -> int | None:
    for string in range(5, -1, -1):
        frets = item.get("frets", [])
        if string >= len(frets):
            continue
        fret = frets[string]
        if isinstance(fret, int) and fret >= 0:
            return (OPEN_STRING_PCS[string] + fret) % 12
    return None


def bass_note_pitch(item: dict[str, Any]) -> int | None:
    for string, fret in enumerate(item.get("frets", [])[:6]):
        if isinstance(fret, int) and fret >= 0:
            return (OPEN_STRING_PCS[string] + fret) % 12
    return None


def pitch_class_distance(a: int | None, b: int | None) -> int | None:
    if a is None or b is None:
        return None
    diff = abs(a - b) % 12
    return min(diff, 12 - diff)


def finger_positions(item: dict[str, Any]) -> dict[int, list[tuple[int, int]]]:
    result: dict[int, list[tuple[int, int]]] = {}
    frets = item.get("frets", [])[:6]
    fingers = item.get("fingers", [])[:6]
    for string, (fret, finger) in enumerate(zip(frets, fingers)):
        if isinstance(fret, int) and fret > 0 and isinstance(finger, int) and finger > 0:
            result.setdefault(finger, []).append((string, fret))
    return result


def finger_movement_distance(prev: dict[str, Any], curr: dict[str, Any]) -> float:
    prev_positions = finger_positions(prev)
    curr_positions = finger_positions(curr)
    distance = 0.0
    for finger in set(prev_positions) & set(curr_positions):
        best = min(
            abs(prev_fret - curr_fret) + 0.5 * abs(prev_string - curr_string)
            for prev_string, prev_fret in prev_positions[finger]
            for curr_string, curr_fret in curr_positions[finger]
        )
        distance += best
    return distance


def style_transition_multiplier(style_card: dict[str, Any], key: str) -> float:
    preferences = style_card.get("transition_preferences") or {}
    if key == "open" and not preferences.get("prefer_open_string_continuity", True):
        return 0.25
    if key == "top_note" and not preferences.get("prefer_top_note_continuity", True):
        return 0.35
    if key == "bass" and not preferences.get("prefer_bass_step_motion", True):
        return 0.35
    if key == "position":
        movement = preferences.get("allow_position_movement", "low")
        if movement == "high":
            return 0.35
        if movement == "medium":
            return 0.65
    return 1.0


def transition_score(
    prev: dict[str, Any],
    curr: dict[str, Any],
    level: str,
    style_card: dict[str, Any],
    rules: dict[str, Any],
) -> float:
    weights = rules["voicing"].get("transition_weights") or {}
    score = 0.0

    shared_fretted = len(fretted_positions(prev) & fretted_positions(curr))
    score += shared_fretted * float(weights.get("shared_fretted_note_bonus", 0))

    shared_open = len(open_string_positions(prev) & open_string_positions(curr))
    score += (
        shared_open
        * float(weights.get("shared_open_string_bonus", 0))
        * style_transition_multiplier(style_card, "open")
    )

    if prev.get("shape") == curr.get("shape") and prev.get("voicing_symbol") == curr.get("voicing_symbol"):
        score += float(weights.get("same_shape_bonus", 0))

    top_distance = pitch_class_distance(top_note_pitch(prev), top_note_pitch(curr))
    if top_distance == 0:
        score += float(weights.get("top_note_same_bonus", 0)) * style_transition_multiplier(style_card, "top_note")
    elif top_distance in (1, 2):
        score += float(weights.get("top_note_step_bonus", 0)) * style_transition_multiplier(style_card, "top_note")

    bass_distance = pitch_class_distance(bass_note_pitch(prev), bass_note_pitch(curr))
    if bass_distance in (1, 2):
        score += float(weights.get("bass_step_bonus", 0)) * style_transition_multiplier(style_card, "bass")

    position_distance = abs(int(prev.get("position") or 1) - int(curr.get("position") or 1))
    score += (
        position_distance
        * float(weights.get("position_distance_penalty", 0))
        * style_transition_multiplier(style_card, "position")
    )

    center_distance = abs(fret_center(prev) - fret_center(curr))
    score += center_distance * float(weights.get("fret_center_distance_penalty", 0))
    if center_distance > 5:
        score += (center_distance - 5) * float(weights.get("wide_fret_jump_penalty", 0))

    score += finger_movement_distance(prev, curr) * float(weights.get("finger_movement_penalty", 0))

    if bool(prev.get("barres")) != bool(curr.get("barres")):
        key = "barre_switch_beginner_penalty" if level == "beginner" else "barre_switch_intermediate_penalty"
        score += float(weights.get(key, 0))

    return score


def serialize_voicing_candidate(
    chord: str,
    used_symbol: str,
    item: dict[str, Any],
    local_score: float,
    simplified: bool,
    coloration: bool,
    coloration_reason: str,
) -> dict[str, Any]:
    frets = item.get("frets", [])
    annotation = item.get("annotation") if isinstance(item.get("annotation"), dict) else {}
    return {
        "chord": chord,
        "voicing_symbol": used_symbol,
        "shape": shape_from_frets(frets),
        "frets": frets,
        "fingers": item.get("fingers"),
        "position": item.get("position"),
        "barres": item.get("barres", []),
        "difficulty": item.get("difficulty"),
        "tags": item.get("tags", []),
        "reason": item.get("reason", ""),
        "commonness": annotation.get("commonness"),
        "annotation_status": annotation.get("status"),
        "annotation_contexts": annotation.get("contexts", []),
        "coloration": used_symbol if coloration else None,
        "coloration_reason": coloration_reason if coloration else "",
        "_local_score": local_score,
        "_simplified": simplified,
    }


def modern_preferred_symbols(
    chords: list[str],
    style: str,
    level: str,
    rules: dict[str, Any],
) -> dict[str, tuple[str, float, str]]:
    result: dict[str, tuple[str, float, str]] = {}
    level_rank = LEVEL_ORDER.get(level, 1)
    chord_set = set(chords)
    for item in (rules["voicing"].get("modern_open_sets") or {}).values():
        if style not in item.get("applies_to_styles", []):
            continue
        if level_rank < LEVEL_ORDER.get(str(item.get("min_level") or "beginner"), 1):
            continue
        required = set(item.get("progression_contains") or [])
        if not required.issubset(chord_set):
            continue
        preferred = item.get("preferred_voicing_symbols") or []
        base_map = {
            simplify_chord(symbol, level="beginner", rules=rules["simplification"]): symbol
            for symbol in preferred
        }
        for base, symbol in base_map.items():
            result[base] = (symbol, float(item.get("bonus", 0)), str(item.get("reason") or ""))
    return result


def choose_voicings(
    chords: list[str],
    index: dict[str, list[dict[str, Any]]],
    style: str,
    level: str,
    style_card: dict[str, Any],
    rules: dict[str, Any],
    known_chords: set[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    warnings = []
    candidate_groups: list[list[dict[str, Any]]] = []
    modern_map = modern_preferred_symbols(chords, style, level, rules)
    pool_rules = rules["voicing"].get("candidate_pool") or {}
    top_k = int(pool_rules.get("top_k_per_chord", 12))
    max_raw = int(pool_rules.get("max_raw_candidates_per_symbol", 80))

    for chord in chords:
        preferred = modern_map.get(simplify_chord(chord, level="beginner", rules=rules["simplification"]))
        if preferred and preferred[0] in index:
            used_symbol = preferred[0]
            candidates = index[used_symbol][:max_raw]
            simplified = False
            coloration = used_symbol != chord
            coloration_reason = preferred[2]
            modern_bonus = preferred[1]
        else:
            used_symbol, candidates, simplified = voicing_candidates(
                chord,
                index,
                level=level,
                simplification_rules=rules["simplification"],
            )
            candidates = candidates[:max_raw]
            coloration = False
            coloration_reason = ""
            modern_bonus = 0.0
        if not candidates:
            warnings.append(f"No voicing found for {chord}.")
            candidate_groups.append([])
            continue

        scored_candidates = []
        for item in candidates:
            local_score = voicing_score(
                item,
                style,
                level,
                style_card,
                rules,
                known_chords,
                modern_bonus=modern_bonus if normalize_symbol(item.get("symbol")) == used_symbol else 0.0,
            )
            scored_candidates.append(
                serialize_voicing_candidate(
                    chord,
                    used_symbol,
                    item,
                    local_score,
                    simplified,
                    coloration,
                    coloration_reason,
                )
            )
        scored_candidates.sort(key=lambda item: float(item["_local_score"]), reverse=True)
        candidate_groups.append(scored_candidates[:top_k])
        if simplified:
            warnings.append(f"{chord} simplified to {used_symbol} for available guitar voicing.")

    if any(not group for group in candidate_groups):
        selected = [group[0] for group in candidate_groups if group]
        return [strip_internal_voicing_fields(item) for item in selected], warnings

    selected = choose_voicing_path(candidate_groups, level, style_card, rules)
    return [strip_internal_voicing_fields(item) for item in selected], warnings


def choose_voicing_path(
    candidate_groups: list[list[dict[str, Any]]],
    level: str,
    style_card: dict[str, Any],
    rules: dict[str, Any],
) -> list[dict[str, Any]]:
    if not candidate_groups:
        return []

    dp: list[list[float]] = []
    back: list[list[int | None]] = []
    dp.append([float(item["_local_score"]) for item in candidate_groups[0]])
    back.append([None for _ in candidate_groups[0]])

    for index in range(1, len(candidate_groups)):
        group_scores = []
        group_back = []
        for curr in candidate_groups[index]:
            best_score = None
            best_prev = 0
            for prev_index, prev in enumerate(candidate_groups[index - 1]):
                score = (
                    dp[index - 1][prev_index]
                    + float(curr["_local_score"])
                    + transition_score(prev, curr, level, style_card, rules)
                )
                if best_score is None or score > best_score:
                    best_score = score
                    best_prev = prev_index
            group_scores.append(float(best_score if best_score is not None else curr["_local_score"]))
            group_back.append(best_prev)
        dp.append(group_scores)
        back.append(group_back)

    last_index = max(range(len(dp[-1])), key=lambda item: dp[-1][item])
    path = [last_index]
    for index in range(len(candidate_groups) - 1, 0, -1):
        previous = back[index][path[-1]]
        path.append(int(previous if previous is not None else 0))
    path.reverse()
    return [candidate_groups[index][candidate_index] for index, candidate_index in enumerate(path)]


def strip_internal_voicing_fields(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if not key.startswith("_")}


def make_chordpro(payload: dict[str, Any], plan: dict[str, Any]) -> str:
    section = str(payload.get("section") or "section")
    title = str(payload.get("title") or "AI-ChordCraft Guitar Draft")
    lines = [
        f"{{title: {title}}}",
        f"{{key: {payload.get('key', '')}}}",
        f"{{capo: {plan['capo']}}}",
        f"{{tempo: {payload.get('bpm', '')}}}",
        "",
        f"{{start_of_{section}}}",
        " ".join(f"[{chord}]" for chord in plan["display_chords"]),
        f"{{end_of_{section}}}",
        "",
    ]
    return "\n".join(lines)


def validate(payload: dict[str, Any], result: dict[str, Any], warnings: list[str], rules: dict[str, Any]) -> dict[str, Any]:
    errors = []
    validation_rules = rules["validation"]
    playability_rules = rules["playability"]
    if payload.get("time_signature") not in validation_rules["supported_time_signatures"]:
        message = "V1 only supports 4/4."
        if validation_rules.get("fail_on", {}).get("unsupported_meter"):
            errors.append(message)
        else:
            warnings.append(message)
    if not payload.get("chords") and validation_rules.get("fail_on", {}).get("empty_chords"):
        errors.append("No chords were provided.")
    if str(payload.get("style")) not in validation_rules["supported_styles"]:
        warnings.append(f"Unsupported style {payload.get('style')}; used fallback scoring.")
    if str(payload.get("section")) not in validation_rules["supported_sections"]:
        warnings.append(f"Unsupported section {payload.get('section')}; used fallback scoring.")
    if str(payload.get("user_level")) not in validation_rules["supported_levels"]:
        warnings.append(f"Unsupported user level {payload.get('user_level')}; used fallback scoring.")
    if len(result.get("voicings", [])) != len(result.get("display_chords", [])):
        message = "Some display chords do not have voicings."
        warnings.append(message)
        if not result.get("voicings") and validation_rules.get("fail_on", {}).get("missing_all_voicings"):
            errors.append(message)
    if str(payload.get("user_level")) == "beginner":
        barre_count = sum(1 for item in result.get("voicings", []) if item.get("barres"))
        max_barre = int((playability_rules["levels"].get("beginner") or {}).get("max_barre_count", 0))
        if barre_count > max_barre:
            warnings.append(f"Beginner arrangement still contains {barre_count} barre voicing(s).")
    difficulties = [
        float(item.get("difficulty"))
        for item in result.get("voicings", [])
        if isinstance(item.get("difficulty"), (int, float))
    ]
    level_rules = (playability_rules["levels"].get(str(payload.get("user_level"))) or {})
    if difficulties and level_rules:
        average = sum(difficulties) / len(difficulties)
        if average > float(level_rules.get("max_average_difficulty", 99)):
            warnings.append(f"Average voicing difficulty {average:.2f} exceeds target for {payload.get('user_level')}.")
    if len(result.get("practice_notes") or []) < int(validation_rules.get("minimum_practice_notes", 1)):
        warnings.append("Practice notes are missing.")
    if not result.get("exports", {}).get("chordpro"):
        warnings.append("ChordPro export is missing.")
    return {"ok": not errors, "errors": errors, "warnings": warnings}


def build_practice_notes(
    payload: dict[str, Any],
    result: dict[str, Any],
    rules: dict[str, Any],
) -> list[str]:
    note_rules = rules["practice_notes"]
    playability = rules["playability"]
    templates = note_rules["templates"]
    level = str(payload.get("user_level") or "beginner")
    ratio = int(float((playability["levels"].get(level) or {}).get("practice_tempo_ratio", 0.75)) * 100)
    original = " - ".join(normalize_symbol(chord) for chord in payload.get("chords") or [])
    display = " - ".join(result["display_chords"])
    if int(result["capo"]) > 0:
        first = templates["capo_transform"].format(capo=result["capo"], original=original, display=display)
    else:
        first = templates["no_capo"]
    notes = [first]
    if level == "beginner":
        notes.append(templates["beginner_tempo"].format(ratio=ratio))
    else:
        notes.append(templates["intermediate_voicing"])
    harmony_hints = (result.get("style_guidance", {}).get("harmony") or {}).get("arrangement_hints") or []
    if harmony_hints:
        notes.append(harmony_hints[0])
    if payload.get("goal"):
        notes.append(templates["goal"].format(goal=payload["goal"]))
    return notes


def arrange(payload: dict[str, Any]) -> dict[str, Any]:
    rules = load_rules()
    voicings = load_voicings()
    index = voicing_index(voicings)
    style = str(payload.get("style") or "pop")
    level = str(payload.get("user_level") or "beginner")
    style_path = STYLE_CARDS_DIR / f"{style}.json"
    style_card = load_json(style_path) if style_path.exists() else {}
    harmony_guidance = style_card.get("harmony") or {}
    arrangement_guidance = style_card.get("guitar_arrangement") or {}
    known_chords = {normalize_symbol(chord) for chord in payload.get("known_chords") or []}

    capo_plan = choose_capo(payload, index, rules)
    selected_voicings, warnings = choose_voicings(
        capo_plan["display_chords"],
        index,
        style,
        level,
        style_card,
        rules,
        known_chords,
    )
    result = {
        "title": str(payload.get("title") or "AI-ChordCraft Guitar Draft"),
        "key": str(payload.get("key") or ""),
        "bpm": payload.get("bpm"),
        "time_signature": str(payload.get("time_signature") or ""),
        "section": str(payload.get("section") or ""),
        "style": style,
        "user_level": level,
        "capo": capo_plan["capo"],
        "play_as_key": capo_plan["play_as_key"],
        "display_chords": capo_plan["display_chords"],
        "voicings": selected_voicings,
        "style_guidance": {
            "harmony": harmony_guidance,
            "guitar_arrangement": arrangement_guidance,
        },
        "practice_notes": [],
        "exports": {
            "chord_diagrams": selected_voicings,
            "chord_diagrams_png": None,
            "chordpro": "",
        },
    }
    result["practice_notes"] = build_practice_notes(payload, result, rules)
    result["exports"]["chordpro"] = make_chordpro(payload, result)
    result["validation"] = validate(payload, result, warnings, rules)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Arrange a chord progression for guitar vocal accompaniment.")
    parser.add_argument("--input-json", help="Inline JSON input.")
    parser.add_argument("--input-file", help="Path to JSON input file.")
    parser.add_argument("--diagram-png-output", help="Optional PNG path for rendered selected chord diagrams.")
    parser.add_argument("--diagram-columns", type=int, default=4, help="Number of columns in the optional diagram PNG.")
    parser.add_argument("--include-duplicate-diagrams", action="store_true", help="Render repeated chord/shape pairs in PNG.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON.")
    args = parser.parse_args()

    if not args.input_json and not args.input_file:
        parser.error("Provide --input-json or --input-file.")
    payload = json.loads(args.input_json) if args.input_json else load_json(Path(args.input_file))
    output = arrange(payload)
    if args.diagram_png_output:
        from render_chord_diagrams import render_chord_diagrams_png

        png_path = render_chord_diagrams_png(
            output,
            Path(args.diagram_png_output),
            columns=args.diagram_columns,
            include_duplicates=args.include_duplicate_diagrams,
        )
        output["exports"]["chord_diagrams_png"] = str(png_path)
    print(json.dumps(output, ensure_ascii=False, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
