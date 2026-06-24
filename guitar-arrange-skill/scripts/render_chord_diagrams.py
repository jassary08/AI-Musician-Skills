#!/usr/bin/env python3
"""Render selected guitar chord voicings to a PNG chord-sheet image.

The renderer is intentionally dependency-free so the skill can export diagrams
in a clean demo environment without Pillow, matplotlib, or a browser.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import zlib
from pathlib import Path
from typing import Any


BG = (244, 248, 255)
CARD = (255, 255, 255)
CARD_HEAD = (231, 240, 255)
BORDER = (190, 208, 236)
INK = (21, 32, 51)
MUTED = (102, 119, 143)
GRID = (64, 82, 111)
NUT = (28, 40, 64)
BLUE = (30, 96, 220)
BLUE_DARK = (16, 62, 148)
ACCENT = (236, 242, 252)
SHADOW = (214, 224, 242)
WHITE = (255, 255, 255)


FONT: dict[str, list[str]] = {
    " ": ["000", "000", "000", "000", "000", "000", "000"],
    "-": ["000", "000", "000", "111", "000", "000", "000"],
    "/": ["001", "001", "010", "010", "100", "100", "000"],
    "#": ["01010", "11111", "01010", "01010", "11111", "01010", "00000"],
    "(": ["010", "100", "100", "100", "100", "100", "010"],
    ")": ["010", "001", "001", "001", "001", "001", "010"],
    "0": ["111", "101", "101", "101", "101", "101", "111"],
    "1": ["010", "110", "010", "010", "010", "010", "111"],
    "2": ["111", "001", "001", "111", "100", "100", "111"],
    "3": ["111", "001", "001", "111", "001", "001", "111"],
    "4": ["101", "101", "101", "111", "001", "001", "001"],
    "5": ["111", "100", "100", "111", "001", "001", "111"],
    "6": ["111", "100", "100", "111", "101", "101", "111"],
    "7": ["111", "001", "001", "010", "010", "010", "010"],
    "8": ["111", "101", "101", "111", "101", "101", "111"],
    "9": ["111", "101", "101", "111", "001", "001", "111"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01111", "10000", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["111", "010", "010", "010", "010", "010", "111"],
    "J": ["00111", "00010", "00010", "00010", "10010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    "a": ["00000", "00000", "01110", "00001", "01111", "10001", "01111"],
    "b": ["10000", "10000", "11110", "10001", "10001", "10001", "11110"],
    "d": ["00001", "00001", "01111", "10001", "10001", "10001", "01111"],
    "i": ["010", "000", "110", "010", "010", "010", "111"],
    "j": ["001", "000", "001", "001", "001", "101", "010"],
    "m": ["00000", "00000", "11010", "10101", "10101", "10101", "10101"],
    "n": ["00000", "00000", "11110", "10001", "10001", "10001", "10001"],
    "o": ["00000", "00000", "01110", "10001", "10001", "10001", "01110"],
    "r": ["00000", "00000", "10110", "11001", "10000", "10000", "10000"],
    "s": ["00000", "00000", "01111", "10000", "01110", "00001", "11110"],
    "u": ["00000", "00000", "10001", "10001", "10001", "10011", "01101"],
    "v": ["00000", "00000", "10001", "10001", "10001", "01010", "00100"],
    ":": ["0", "1", "0", "0", "1", "0", "0"],
    "|": ["1", "1", "1", "1", "1", "1", "1"],
}

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
MAJOR_DEGREES = {
    0: "I",
    2: "ii",
    4: "iii",
    5: "IV",
    7: "V",
    9: "vi",
    11: "vii dim",
}
MINOR_DEGREES = {
    0: "i",
    2: "ii dim",
    3: "III",
    5: "iv",
    7: "v",
    8: "VI",
    10: "VII",
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


def key_root_and_mode(key: Any) -> tuple[str | None, str]:
    parts = str(key or "").strip().replace("♯", "#").replace("♭", "b").split()
    if not parts:
        return None, "major"
    root = normalize_symbol(parts[0])
    mode = " ".join(parts[1:]).lower() if len(parts) > 1 else "major"
    if "minor" in mode or mode in {"min", "m"}:
        mode = "minor"
    else:
        mode = "major"
    return root if root in PC else None, mode


def chord_degree(symbol: Any, key: Any) -> str:
    key_root, mode = key_root_and_mode(key)
    chord_root, suffix = split_chord(str(symbol or ""))
    if key_root not in PC or chord_root not in PC:
        return ""
    interval = (PC[chord_root] - PC[key_root]) % 12
    low = suffix.lower()
    if mode == "minor":
        degree = MINOR_DEGREES.get(interval)
        if interval == 7 and not low.startswith("m"):
            degree = "V"
    else:
        degree = MAJOR_DEGREES.get(interval)
    if not degree:
        return f"{interval}"
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


def render_key(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("play_as_key") or payload.get("key") or "").strip()


def render_capo(payload: Any) -> Any:
    return payload.get("capo") if isinstance(payload, dict) and payload.get("capo") is not None else 0


class Canvas:
    """Logical-coordinate canvas rendered at an internal supersample factor.

    All public drawing methods take logical pixels. The canvas keeps an
    internal buffer scaled by ``ss`` and box-downsamples on save, which gives
    cheap anti-aliasing for circles, diagonal lines, and barre bars without any
    third-party imaging dependency.
    """

    def __init__(
        self,
        width: int,
        height: int,
        bg: tuple[int, int, int] = BG,
        ss: int = 2,
    ) -> None:
        self.ss = max(1, int(ss))
        self.lw = width
        self.lh = height
        self.width = width * self.ss
        self.height = height * self.ss
        self.pixels = bytearray(self.width * self.height * 3)
        self._fill_phys(0, 0, self.width, self.height, bg)

    # --- physical-space primitives (already scaled) ---

    def _set_phys(self, x: int, y: int, color: tuple[int, int, int]) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            offset = (y * self.width + x) * 3
            self.pixels[offset : offset + 3] = bytes(color)

    def _fill_phys(self, x: int, y: int, w: int, h: int, color: tuple[int, int, int]) -> None:
        x0 = max(0, x)
        x1 = min(self.width, x + w)
        if x1 <= x0:
            return
        run = bytes(color) * (x1 - x0)
        for yy in range(max(0, y), min(self.height, y + h)):
            start = (yy * self.width + x0) * 3
            self.pixels[start : start + len(run)] = run

    def _circle_phys(self, cx: int, cy: int, r: int, color: tuple[int, int, int]) -> None:
        rr = r * r
        for y in range(cy - r, cy + r + 1):
            dy2 = (y - cy) * (y - cy)
            for x in range(cx - r, cx + r + 1):
                if (x - cx) * (x - cx) + dy2 <= rr:
                    self._set_phys(x, y, color)

    def _ring_phys(self, cx: int, cy: int, r: int, thickness: int, color: tuple[int, int, int]) -> None:
        outer = r * r
        inner = max(0, r - thickness) ** 2
        for y in range(cy - r, cy + r + 1):
            dy2 = (y - cy) * (y - cy)
            for x in range(cx - r, cx + r + 1):
                dist = (x - cx) * (x - cx) + dy2
                if inner <= dist <= outer:
                    self._set_phys(x, y, color)

    def _line_phys(self, x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int], thickness: int) -> None:
        dx = abs(x2 - x1)
        dy = -abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx + dy
        radius = max(0, thickness // 2)
        while True:
            self._fill_phys(x1 - radius, y1 - radius, thickness, thickness, color)
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x1 += sx
            if e2 <= dx:
                err += dx
                y1 += sy

    # --- logical-space public API (scaled by ss) ---

    def fill_rect(self, x: int, y: int, w: int, h: int, color: tuple[int, int, int]) -> None:
        s = self.ss
        self._fill_phys(x * s, y * s, w * s, h * s, color)

    def rect(self, x: int, y: int, w: int, h: int, color: tuple[int, int, int], thickness: int = 1) -> None:
        self.fill_rect(x, y, w, thickness, color)
        self.fill_rect(x, y + h - thickness, w, thickness, color)
        self.fill_rect(x, y, thickness, h, color)
        self.fill_rect(x + w - thickness, y, thickness, h, color)

    def round_rect(self, x: int, y: int, w: int, h: int, radius: int, color: tuple[int, int, int]) -> None:
        """Filled rectangle with rounded corners (used for header chips/cards)."""
        s = self.ss
        r = max(0, radius) * s
        px, py, pw, ph = x * s, y * s, w * s, h * s
        self._fill_phys(px + r, py, pw - 2 * r, ph, color)
        self._fill_phys(px, py + r, pw, ph - 2 * r, color)
        for cx, cy in (
            (px + r, py + r),
            (px + pw - r - 1, py + r),
            (px + r, py + ph - r - 1),
            (px + pw - r - 1, py + ph - r - 1),
        ):
            self._circle_phys(cx, cy, r, color)

    def line(self, x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int], thickness: int = 1) -> None:
        s = self.ss
        self._line_phys(x1 * s, y1 * s, x2 * s, y2 * s, color, max(1, thickness * s))

    def circle(self, cx: int, cy: int, r: int, color: tuple[int, int, int]) -> None:
        s = self.ss
        self._circle_phys(cx * s, cy * s, r * s, color)

    def ring(self, cx: int, cy: int, r: int, color: tuple[int, int, int], thickness: int = 2) -> None:
        s = self.ss
        self._ring_phys(cx * s, cy * s, r * s, max(1, thickness * s), color)

    def cross(self, cx: int, cy: int, r: int, color: tuple[int, int, int], thickness: int = 2) -> None:
        s = self.ss
        self._line_phys((cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s, color, max(1, thickness * s))
        self._line_phys((cx - r) * s, (cy + r) * s, (cx + r) * s, (cy - r) * s, color, max(1, thickness * s))

    def draw_text(self, x: int, y: int, text: str, color: tuple[int, int, int] = INK, scale: int = 2) -> None:
        s = self.ss
        cursor = x * s
        step = scale * s
        for ch in text:
            glyph = FONT.get(ch) or FONT.get(ch.upper()) or FONT[" "]
            for row, bits in enumerate(glyph):
                for col, bit in enumerate(bits):
                    if bit == "1":
                        self._fill_phys(cursor + col * step, y * s + row * step, step, step, color)
            cursor += (len(glyph[0]) + 1) * step

    def text_width(self, text: str, scale: int = 2) -> int:
        width = 0
        for ch in text:
            glyph = FONT.get(ch) or FONT.get(ch.upper()) or FONT[" "]
            width += (len(glyph[0]) + 1) * scale
        return width

    def _downsample(self) -> tuple[int, int, bytearray]:
        if self.ss == 1:
            return self.width, self.height, self.pixels
        s = self.ss
        out = bytearray(self.lw * self.lh * 3)
        area = s * s
        src = self.pixels
        sw = self.width
        for oy in range(self.lh):
            for ox in range(self.lw):
                r = g = b = 0
                base_y = oy * s
                base_x = ox * s
                for dy in range(s):
                    row = ((base_y + dy) * sw + base_x) * 3
                    for _dx in range(s):
                        r += src[row]
                        g += src[row + 1]
                        b += src[row + 2]
                        row += 3
                o = (oy * self.lw + ox) * 3
                out[o] = r // area
                out[o + 1] = g // area
                out[o + 2] = b // area
        return self.lw, self.lh, out

    def save_png(self, path: Path) -> None:
        def chunk(kind: bytes, data: bytes) -> bytes:
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

        width, height, pixels = self._downsample()
        rows = bytearray()
        stride = width * 3
        for y in range(height):
            rows.append(0)
            rows.extend(pixels[y * stride : (y + 1) * stride])
        payload = b"".join(
            [
                b"\x89PNG\r\n\x1a\n",
                chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
                chunk(b"IDAT", zlib.compress(bytes(rows), 9)),
                chunk(b"IEND", b""),
            ]
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


def normalize_frets(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value[:6]:
        if isinstance(item, int):
            result.append(item)
        elif isinstance(item, str) and item.lower() == "x":
            result.append(-1)
        else:
            try:
                result.append(int(item))
            except Exception:  # noqa: BLE001
                result.append(-1)
    return result if len(result) == 6 else []


def collect_voicings(payload: Any, include_duplicates: bool = False) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        voicings = payload
    elif isinstance(payload, dict):
        voicings = payload.get("voicings") or (payload.get("exports") or {}).get("chord_diagrams") or []
    else:
        voicings = []

    selected = []
    seen: set[tuple[str, tuple[int, ...]]] = set()
    for item in voicings:
        if not isinstance(item, dict):
            continue
        frets = normalize_frets(item.get("frets"))
        if not frets:
            continue
        symbol = str(item.get("voicing_symbol") or item.get("symbol") or item.get("chord") or "").strip()
        key = (symbol, tuple(frets))
        if not include_duplicates and key in seen:
            continue
        seen.add(key)
        selected.append({**item, "frets": frets})
    return selected


def draw_chord(canvas: Canvas, item: dict[str, Any], x: int, y: int, w: int, h: int) -> None:
    # soft drop shadow + card with a tinted title band
    canvas.round_rect(x + 3, y + 4, w, h, 10, SHADOW)
    canvas.round_rect(x, y, w, h, 10, CARD)
    canvas.fill_rect(x + 2, y + 2, w - 4, 40, CARD_HEAD)
    canvas.rect(x, y, w, h, BORDER, 2)

    label = str(item.get("voicing_symbol") or item.get("symbol") or item.get("chord") or "Chord")
    label_scale = 3 if len(label) <= 5 else 2
    label_x = x + (w - canvas.text_width(label, label_scale)) // 2
    canvas.draw_text(label_x, y + 13, label, INK, label_scale)

    degree = str(item.get("degree") or "").strip()
    if degree:
        degree_x = x + (w - canvas.text_width(degree, 2)) // 2
        canvas.draw_text(degree_x, y + 48, degree, BLUE_DARK, 2)

    frets = item["frets"]
    fingers = item.get("fingers") if isinstance(item.get("fingers"), list) else []
    fingers = [int(value) if isinstance(value, int) else 0 for value in fingers[:6]]
    fingers = fingers + [0] * (6 - len(fingers))
    pressed = [fret for fret in frets if fret > 0]
    position = item.get("position")
    base_fret = int(position) if isinstance(position, int) and position > 1 else 1
    if pressed and base_fret == 1 and max(pressed) > 5:
        base_fret = min(pressed)

    grid_left = x + 44
    grid_top = y + 86
    grid_w = w - 88
    grid_h = 146
    string_gap = grid_w // 5
    fret_gap = grid_h // 5
    xs = [grid_left + idx * string_gap for idx in range(6)]

    # fretboard fill behind the grid for a touch of depth
    canvas.fill_rect(grid_left, grid_top, grid_w, grid_h, ACCENT)

    for idx in range(6):
        canvas.line(xs[idx], grid_top, xs[idx], grid_top + grid_h, GRID, 2)
    for idx in range(6):
        is_nut = idx == 0 and base_fret == 1
        thickness = 6 if is_nut else 2
        color = NUT if is_nut else GRID
        canvas.line(grid_left, grid_top + idx * fret_gap, grid_left + grid_w, grid_top + idx * fret_gap, color, thickness)

    if base_fret > 1:
        canvas.draw_text(x + 14, grid_top + 3, f"{base_fret}fr", MUTED, 2)

    # open (ring) / muted (cross) markers above the nut, drawn as real glyphs
    for idx, fret in enumerate(frets):
        if fret < 0:
            canvas.cross(xs[idx], grid_top - 16, 7, MUTED, 2)
        elif fret == 0:
            canvas.ring(xs[idx], grid_top - 16, 7, MUTED, 2)

    for barre_fret in item.get("barres") or []:
        if not isinstance(barre_fret, int) or not (base_fret <= barre_fret < base_fret + 5):
            continue
        string_indices = [idx for idx, fret in enumerate(frets) if fret == barre_fret]
        if len(string_indices) < 2:
            continue
        yy = grid_top + int((barre_fret - base_fret + 0.5) * fret_gap)
        canvas.line(xs[min(string_indices)], yy, xs[max(string_indices)], yy, BLUE_DARK, 13)

    for idx, fret in enumerate(frets):
        if fret <= 0 or not (base_fret <= fret < base_fret + 5):
            continue
        cx = xs[idx]
        cy = grid_top + int((fret - base_fret + 0.5) * fret_gap)
        canvas.circle(cx, cy, 12, BLUE_DARK)
        canvas.circle(cx, cy, 10, BLUE)
        finger = fingers[idx]
        if finger > 0:
            text = str(finger)
            canvas.draw_text(cx - canvas.text_width(text, 1) // 2, cy - 4, text, WHITE, 1)

    shape = str(item.get("shape") or "".join("x" if fret < 0 else str(fret) for fret in frets))
    shape_x = x + (w - canvas.text_width(shape, 2)) // 2
    canvas.draw_text(shape_x, y + h - 24, shape, MUTED, 2)


def add_degree_labels(voicings: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    if not key:
        return voicings
    result = []
    for item in voicings:
        symbol = item.get("voicing_symbol") or item.get("symbol") or item.get("chord")
        result.append({**item, "degree": item.get("degree") or chord_degree(symbol, key)})
    return result


def header_fields(payload: Any) -> list[tuple[str, str]]:
    """Collect the meta line shown at the top of a practice sheet."""
    if not isinstance(payload, dict):
        return []
    capo = render_capo(payload)
    key = render_key(payload)
    pairs: list[tuple[str, str]] = []
    if key:
        pairs.append(("Key", key))
    pairs.append(("Capo", str(capo if capo not in (None, "") else 0)))
    for label, field in (("BPM", "bpm"), ("Time", "time_signature"), ("Style", "style")):
        value = payload.get(field)
        if value not in (None, ""):
            pairs.append((label, str(value)))
    return pairs


def progression_bars(payload: Any) -> list[dict[str, str]]:
    """Pull the ordered bar-by-bar progression for the sheet header strip."""
    if not isinstance(payload, dict):
        return []
    exports = payload.get("exports") or {}
    grid = exports.get("progression_grid") or {}
    rows = grid.get("rows") if isinstance(grid, dict) else None
    bars: list[dict[str, str]] = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, list):
                continue
            for bar in row:
                if isinstance(bar, dict):
                    bars.append(
                        {
                            "chord": str(bar.get("chord") or ""),
                            "degree": str(bar.get("degree") or ""),
                        }
                    )
    if bars:
        return bars
    lead = exports.get("lead_sheet") or {}
    lead_bars = lead.get("bars") if isinstance(lead, dict) else None
    if isinstance(lead_bars, list):
        for bar in lead_bars:
            if isinstance(bar, dict):
                bars.append(
                    {
                        "chord": str(bar.get("chord") or ""),
                        "degree": str(bar.get("degree") or ""),
                    }
                )
    if bars:
        return bars
    display = payload.get("display_chords")
    if isinstance(display, list):
        bars = [{"chord": str(chord), "degree": ""} for chord in display]
    return bars


def draw_progression_strip(
    canvas: Canvas, bars: list[dict[str, str]], x: int, y: int, width: int, columns: int = 4
) -> int:
    """Draw the ordered progression as numbered bar cells. Returns height used."""
    if not bars:
        return 0
    columns = max(1, columns)
    gap = 10
    cell_w = (width - (columns - 1) * gap) // columns
    cell_h = 56
    rows = math.ceil(len(bars) / columns)
    canvas.draw_text(x, y, "Progression", MUTED, 2)
    top = y + 26
    for idx, bar in enumerate(bars):
        row = idx // columns
        col = idx % columns
        cx = x + col * (cell_w + gap)
        cy = top + row * (cell_h + gap)
        canvas.round_rect(cx, cy, cell_w, cell_h, 8, CARD)
        canvas.rect(cx, cy, cell_w, cell_h, BORDER, 2)
        canvas.fill_rect(cx + 2, cy + 2, 26, cell_h - 4, ACCENT)
        canvas.draw_text(cx + 7, cy + cell_h // 2 - 7, str(idx + 1), MUTED, 2)
        chord = bar.get("chord") or ""
        chord_scale = 3 if len(chord) <= 4 else 2
        chord_x = cx + 32 + (cell_w - 32 - canvas.text_width(chord, chord_scale)) // 2
        canvas.draw_text(chord_x, cy + 10, chord, INK, chord_scale)
        degree = bar.get("degree") or ""
        if degree:
            deg_x = cx + 32 + (cell_w - 32 - canvas.text_width(degree, 1)) // 2
            canvas.draw_text(deg_x, cy + 38, degree, BLUE_DARK, 1)
    return top - y + rows * cell_h + (rows - 1) * gap


def render_chord_diagrams_png(
    payload: Any,
    output_path: Path,
    columns: int = 4,
    include_duplicates: bool = False,
    layout: str = "sheet",
) -> Path:
    key = render_key(payload)
    capo = render_capo(payload)
    voicings = add_degree_labels(collect_voicings(payload, include_duplicates=include_duplicates), key)
    if not voicings:
        raise ValueError("No renderable voicings found in input.")
    columns = max(1, columns)
    cell_w = 206
    cell_h = 272
    gap = 18
    margin = 24

    fields = header_fields(payload) if layout == "sheet" else []
    bars = progression_bars(payload) if layout == "sheet" else []

    diagram_rows = math.ceil(len(voicings) / columns)
    grid_w = columns * cell_w + (columns - 1) * gap
    width = margin * 2 + grid_w

    # measure header block height for the sheet layout
    title = str(payload.get("title") or "").strip() if isinstance(payload, dict) else ""
    head_h = 0
    if layout == "sheet":
        head_h += 34 if title else 0
        head_h += 30 if fields else 0
    elif key or capo not in (None, 0, "0"):
        head_h = 64

    # progression strip height (measured with a throwaway pass would be costly;
    # compute geometry directly)
    strip_h = 0
    if bars:
        strip_cols = max(1, min(8, columns * 2))
        strip_gap = 10
        strip_rows = math.ceil(len(bars) / strip_cols)
        strip_h = 26 + strip_rows * 56 + (strip_rows - 1) * strip_gap + 18

    diagrams_label_h = 24 if layout == "sheet" and bars else 0
    top_block = head_h + (12 if head_h else 0) + strip_h + diagrams_label_h
    height = margin * 2 + top_block + diagram_rows * cell_h + (diagram_rows - 1) * gap

    canvas = Canvas(width, height, BG)
    cursor_y = margin

    if layout == "sheet":
        if title:
            canvas.draw_text(margin, cursor_y, title, INK, 3)
            cursor_y += 34
        if fields:
            chip_x = margin
            for label, value in fields:
                text = f"{label} {value}"
                chip_w = canvas.text_width(text, 2) + 20
                canvas.round_rect(chip_x, cursor_y, chip_w, 24, 6, CARD_HEAD)
                canvas.draw_text(chip_x + 10, cursor_y + 5, text, BLUE_DARK, 2)
                chip_x += chip_w + 10
            cursor_y += 30
        if head_h:
            cursor_y += 12
        if bars:
            strip_cols = max(1, min(8, columns * 2))
            used = draw_progression_strip(canvas, bars, margin, cursor_y, grid_w, columns=strip_cols)
            cursor_y += used + 18
            canvas.draw_text(margin, cursor_y, "Chord shapes", MUTED, 2)
            cursor_y += 24
    else:
        if head_h:
            header = f"Capo {capo} - {key}".strip()
            canvas.draw_text(margin, cursor_y + 4, header, INK, 3)
            cursor_y += head_h

    for idx, item in enumerate(voicings):
        row = idx // columns
        col = idx % columns
        x = margin + col * (cell_w + gap)
        y = cursor_y + row * (cell_h + gap)
        draw_chord(canvas, item, x, y, cell_w, cell_h)
    canvas.save_png(output_path)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Render guitar chord diagrams from an arranger JSON result.")
    parser.add_argument("--input-json", help="Inline JSON containing voicings or an arrange_guitar result.")
    parser.add_argument("--input-file", help="Path to JSON containing voicings or an arrange_guitar result.")
    parser.add_argument("--output", required=True, help="PNG output path.")
    parser.add_argument("--columns", type=int, default=4, help="Number of diagram columns.")
    parser.add_argument(
        "--layout",
        choices=["sheet", "grid"],
        default="sheet",
        help="sheet: header + ordered progression + deduped shapes (default). grid: plain diagram grid.",
    )
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="Render every voicing in progression order instead of unique shapes only.",
    )
    parser.add_argument(
        "--include-duplicates",
        action="store_true",
        help="Alias of --show-all (kept for backward compatibility).",
    )
    args = parser.parse_args()

    if not args.input_json and not args.input_file:
        parser.error("Provide --input-json or --input-file.")
    payload = json.loads(args.input_json) if args.input_json else load_json(Path(args.input_file))
    output = render_chord_diagrams_png(
        payload,
        Path(args.output),
        columns=args.columns,
        include_duplicates=args.show_all or args.include_duplicates,
        layout=args.layout,
    )
    print(json.dumps({"output": str(output), "ok": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
