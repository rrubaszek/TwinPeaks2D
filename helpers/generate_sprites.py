#!/usr/bin/env python3
"""Generates small pixel-art sprites (RGBA PNG with transparency) from ASCII grids.

Each sprite is a list of equal-length rows; every character is a palette key,
'.' is fully transparent. The bottom row is what stands on the floor in the game.

Usage (from any directory, no dependencies beyond the standard library):
    python3 helpers/generate_sprites.py              # all sprites -> maps/textures/
    python3 helpers/generate_sprites.py --list
    python3 helpers/generate_sprites.py mug pie      # selected sprites only
    python3 helpers/generate_sprites.py --preview 8  # also writes 8x enlarged *_preview.png
"""

from __future__ import annotations

import argparse
import struct
import sys
import zlib
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "maps" / "textures"

# key -> (r, g, b); '.' is reserved for transparent
PALETTE = {
    "k": (30, 20, 15),     # outline
    "w": (235, 235, 225),  # porcelain white
    "g": (170, 170, 165),  # porcelain shadow
    "c": (90, 50, 25),     # coffee
    "C": (130, 80, 40),    # coffee highlight
    "r": (190, 30, 40),    # cherry / vinyl red
    "R": (120, 15, 25),    # dark red
    "y": (215, 160, 80),   # pie crust
    "Y": (165, 110, 50),   # crust shadow
    "m": (200, 205, 215),  # chrome
    "M": (120, 125, 135),  # chrome shadow
    "v": (60, 140, 60),    # leaf
    "V": (30, 90, 40),     # dark leaf
    "b": (140, 80, 40),    # clay pot
    "B": (90, 50, 25),     # pot shadow
    "l": (240, 220, 150),  # lamp shade, lit
    "L": (200, 170, 90),   # lamp shade, shadow
}

SPRITES: dict[str, list[str]] = {
    "mug": [
        "................",
        "................",
        "................",
        "................",
        "................",
        "..kkkkkkkkk.....",
        "..kcCccccck.....",
        "..kwwwwwwwkkkk..",
        "..kwwwwwwgk..k..",
        "..kwwwwwwgk..k..",
        "..kwwwwwwgkkkk..",
        "..kwwwwwwgk.....",
        "..kwwwwwwgk.....",
        "...kwwwwgk......",
        "...kkkkkkk......",
        "..kgggggggk.....",
    ],
    "pie": [
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "......kk........",
        "....kkyykk......",
        "..kkyyyyyykk....",
        "kkyyyyyyyyyykk..",
        "kRrrrrrrrrrrrk..",
        "krRrrrRrrrRrrk..",
        "kYyYyYyYyYyYyk..",
        "kYYYYYYYYYYYYk..",
        "kkkkkkkkkkkkkk..",
    ],
    "stool": [
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "..kkkkkkkkkkkk..",
        ".krrrrrrrrrrrrk.",
        ".kRRRRRRRRRRRRk.",
        "..kkkkkkkkkkkk..",
        ".......mM.......",
        ".......mM.......",
        ".......mM.......",
        ".......mM.......",
        ".......mM.......",
        ".......mM.......",
        ".......mM.......",
        ".......mM.......",
        "....kmmmmMMk....",
        ".......mM.......",
        ".......mM.......",
        ".......mM.......",
        ".....kmmmMMk....",
        "...kkkkkkkkkk...",
    ],
    "plant": [
        "......V.........",
        ".....VvV....V...",
        "..V..VvV...VvV..",
        ".VvV.VvV..VvvV..",
        ".VvvVVvVVVvvV...",
        "..VvvvvvvvvV....",
        "VvVVvvvvvvvVVvV.",
        ".VvvvVvvvVvvvV..",
        "..VVvvvvvvvVV...",
        "....VVvvvVV.....",
        "......VV........",
        "......Vv........",
        "...kkkkkkkkkk...",
        "...kbbbbbbbbk...",
        "....kbbbbbbk....",
        "....kbBbbbBk....",
        "....kbbbbbbk....",
        "....kbbbbbbk....",
        ".....kbbbbk.....",
        ".....kBBBBk.....",
        ".....kkkkkk.....",
    ],
    "lamp": [
        "....kkkkkkk.....",
        "...klllllllk....",
        "...klllllllk....",
        "..kllllllllLk...",
        "..klllllllLLk...",
        ".kllllllllLLLk..",
        ".kkkkkkkkkkkkk..",
    ] + [".......mM......."] * 22 + [
        ".....kMMMMk.....",
        "....kMMMMMMk....",
        "...kkkkkkkkkk...",
    ],
}


def check(name: str, rows: list[str]) -> None:
    widths = {len(r) for r in rows}
    if len(widths) != 1:
        sys.exit(f"{name}: rows have different widths {sorted(widths)}")
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != "." and ch not in PALETTE:
                sys.exit(f"{name}: unknown palette key '{ch}' at row {y}, col {x}")


def to_rgba(rows: list[str], scale: int = 1) -> tuple[int, int, list[bytes]]:
    out = []
    for row in rows:
        line = bytearray()
        for ch in row:
            px = bytes((0, 0, 0, 0)) if ch == "." else bytes((*PALETTE[ch], 255))
            line += px * scale
        out += [bytes(line)] * scale
    return len(rows[0]) * scale, len(rows) * scale, out


def write_png(path: Path, width: int, height: int, rows: list[bytes]) -> None:
    """Minimal RGBA8 PNG writer: one IDAT, filter type 0 on every row."""
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    raw = b"".join(b"\x00" + r for r in rows)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                     + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("names", nargs="*", help="sprites to generate (default: all)")
    ap.add_argument("--list", action="store_true", help="list sprites and exit")
    ap.add_argument("--out", type=Path, default=OUT_DIR, help=f"output dir (default {OUT_DIR})")
    ap.add_argument("--preview", type=int, metavar="N", help="also write N-times enlarged previews")
    args = ap.parse_args()

    if args.list:
        for name, rows in SPRITES.items():
            print(f"{name:8} {len(rows[0])}x{len(rows)}  -> sprite_{name}.png")
        return

    unknown = [n for n in args.names if n not in SPRITES]
    if unknown:
        sys.exit(f"unknown sprite(s): {', '.join(unknown)} (see --list)")

    args.out.mkdir(parents=True, exist_ok=True)
    for name in args.names or SPRITES:
        rows = SPRITES[name]
        check(name, rows)
        write_png(args.out / f"sprite_{name}.png", *to_rgba(rows))
        if args.preview:
            write_png(args.out / f"sprite_{name}_preview.png", *to_rgba(rows, args.preview))
        print(f"sprite_{name}.png  {len(rows[0])}x{len(rows)}")


if __name__ == "__main__":
    main()
