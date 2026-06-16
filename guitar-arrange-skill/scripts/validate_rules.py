#!/usr/bin/env python3
"""Validate guitar arrangement rule resources."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RULES_DIR = ROOT / "resources" / "rules"
VOICING_DB_DIR = ROOT / "resources" / "voicing_db"
STYLE_CARDS_DIR = ROOT / "resources" / "style_cards"
VOICING_SOURCE_PATH = VOICING_DB_DIR / "source" / "chords_db_voicings.json"
VOICING_ANNOTATIONS_PATH = VOICING_DB_DIR / "overlays" / "commonness_annotations.json"
VOICING_LAYERS_PATH = VOICING_DB_DIR / "indexes" / "voicing_layers.json"
LAYER_INDEX_DIR = VOICING_DB_DIR / "indexes" / "layer_indexes"
REQUIRED_LAYER_INDEX_FILES = {
    "manifest.json",
    "musical_taxonomy.json",
    "guitar_playability.json",
    "release_review_pools.json",
    "style_fit.json",
    "voice_leading.json",
}

REQUIRED_RULE_FILES = {
    "capo_rules.json": ["max_capo", "weights", "beginner_common_shapes"],
    "voicing_scoring_rules.json": ["target_difficulty", "weights", "candidate_pool", "transition_weights", "fallback_order"],
    "playability_rules.json": ["levels", "hard_avoid_for_beginner", "warning_thresholds"],
    "simplification_rules.json": ["quality_rewrites", "slash_chords", "enharmonic_preferences"],
    "validation_rules.json": ["supported_time_signatures", "required_output_fields", "fail_on", "warn_on"],
    "practice_note_rules.json": ["templates", "section_labels"],
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []
    for filename, required_keys in REQUIRED_RULE_FILES.items():
        path = RULES_DIR / filename
        if not path.exists():
            errors.append(f"Missing rule file: {path}")
            continue
        try:
            payload = load_json(path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Invalid JSON in {path}: {exc}")
            continue
        for key in required_keys:
            if key not in payload:
                errors.append(f"{filename} missing required key: {key}")
        if payload.get("version") is None:
            errors.append(f"{filename} missing version")

    validation = load_json(RULES_DIR / "validation_rules.json")
    output_fields = set(validation.get("required_output_fields") or [])
    expected_fields = {"capo", "play_as_key", "display_chords", "voicings", "style_guidance", "practice_notes", "exports", "validation"}
    missing_output = expected_fields - output_fields
    if missing_output:
        errors.append(f"validation_rules.json missing output fields: {sorted(missing_output)}")

    supported_styles = set(validation.get("supported_styles") or [])
    style_files = {path.stem for path in STYLE_CARDS_DIR.glob("*.json")}
    if style_files != supported_styles:
        errors.append(f"style_cards must exactly match supported styles: {sorted(supported_styles)}")
    for style in sorted(supported_styles):
        path = STYLE_CARDS_DIR / f"{style}.json"
        if not path.exists():
            continue
        card = load_json(path)
        for key in ["preferred_tags", "transition_preferences", "harmony", "guitar_arrangement"]:
            if key not in card:
                errors.append(f"{path.name} missing required key: {key}")
        harmony = card.get("harmony") or {}
        for key in ["core_principles", "chord_vocabulary", "common_moves", "section_recipes", "reharmonization_moves", "arrangement_hints"]:
            if key not in harmony:
                errors.append(f"{path.name} harmony missing required key: {key}")
        forbidden_harmony_keys = {"preferred_qualities", "section_guidance"}
        for key in forbidden_harmony_keys & set(harmony):
            errors.append(f"{path.name} harmony should not contain statistical key: {key}")

    voicing_rules = load_json(RULES_DIR / "voicing_scoring_rules.json")
    pool = voicing_rules.get("candidate_pool") or {}
    if int(pool.get("top_k_per_chord", 0)) <= 0:
        errors.append("voicing_scoring_rules.json candidate_pool.top_k_per_chord must be positive")
    transition_weights = voicing_rules.get("transition_weights") or {}
    for key in [
        "shared_fretted_note_bonus",
        "shared_open_string_bonus",
        "top_note_same_bonus",
        "position_distance_penalty",
        "finger_movement_penalty",
        "barre_switch_beginner_penalty",
    ]:
        if key not in transition_weights:
            errors.append(f"voicing_scoring_rules.json transition_weights missing key: {key}")

    voicing_path = VOICING_SOURCE_PATH
    if voicing_path.exists():
        voicing_payload = load_json(voicing_path)
        source = voicing_payload.get("source") or {}
        if source.get("license") != "MIT":
            errors.append("source/chords_db_voicings.json source.license must be MIT")
        voicings = voicing_payload.get("voicings")
        if not isinstance(voicings, list):
            errors.append("source/chords_db_voicings.json must contain voicings list")
        else:
            for index, item in enumerate(voicings):
                prefix = f"external voicing[{index}] {item.get('symbol', '<missing>')}"
                if not isinstance(item.get("frets"), list) or len(item["frets"]) != 6:
                    errors.append(f"{prefix}: frets must contain six items")
                if not isinstance(item.get("fingers"), list) or len(item["fingers"]) != 6:
                    errors.append(f"{prefix}: fingers must contain six items")
                if item.get("source") != "tombatossals/chords-db":
                    errors.append(f"{prefix}: source metadata missing")
                if item.get("source_license") != "MIT":
                    errors.append(f"{prefix}: license metadata missing")
    else:
        errors.append(f"Missing source voicing database: {voicing_path}")

    if VOICING_ANNOTATIONS_PATH.exists():
        annotation_payload = load_json(VOICING_ANNOTATIONS_PATH)
        annotations = annotation_payload.get("annotations")
        if not isinstance(annotations, dict):
            errors.append("overlays/commonness_annotations.json must contain annotations object")
    else:
        errors.append(f"Missing voicing annotation overlay: {VOICING_ANNOTATIONS_PATH}")

    if not VOICING_LAYERS_PATH.exists():
        errors.append(f"Missing layered voicing index: {VOICING_LAYERS_PATH}")
    else:
        layers_payload = load_json(VOICING_LAYERS_PATH)
        for key in ["stats", "layers", "voicings"]:
            if key not in layers_payload:
                errors.append(f"voicing_layers.json missing required key: {key}")
        layers = layers_payload.get("layers") or {}
        for key in [
            "by_family",
            "by_quality",
            "by_shape_type",
            "by_difficulty",
            "by_review_status",
            "by_style_fit",
            "by_harmony_tier",
            "by_playability_tier",
            "by_review_priority",
            "by_release_layer",
        ]:
            if key not in layers:
                errors.append(f"voicing_layers.json layers missing required key: {key}")
        layer_voicings = layers_payload.get("voicings")
        if not isinstance(layer_voicings, list) or not layer_voicings:
            errors.append("voicing_layers.json must contain non-empty voicings list")
        else:
            sample = layer_voicings[0]
            for key in [
                "id",
                "symbol",
                "family",
                "quality",
                "harmony_tier",
                "shape_types",
                "difficulty_band",
                "playability_tier",
                "voice_leading",
                "style_fit",
                "review_status",
                "review_priority",
                "release_layer",
            ]:
                if key not in sample:
                    errors.append(f"voicing_layers.json voicing item missing required key: {key}")

    for filename in sorted(REQUIRED_LAYER_INDEX_FILES):
        path = LAYER_INDEX_DIR / filename
        if not path.exists():
            errors.append(f"Missing layer index file: {path}")
            continue
        try:
            layer_index = load_json(path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Invalid JSON in {path}: {exc}")
            continue
        if layer_index.get("version") is None:
            errors.append(f"{filename} missing version")
        if filename != "manifest.json" and "indexes" not in layer_index:
            errors.append(f"{filename} missing indexes")

    manifest_path = LAYER_INDEX_DIR / "manifest.json"
    if manifest_path.exists():
        manifest = load_json(manifest_path)
        manifest_files = set((manifest.get("files") or {}).keys())
        missing_from_manifest = (REQUIRED_LAYER_INDEX_FILES - {"manifest.json"}) - manifest_files
        if missing_from_manifest:
            errors.append(f"layer_indexes/manifest.json missing files: {sorted(missing_from_manifest)}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Rule validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
