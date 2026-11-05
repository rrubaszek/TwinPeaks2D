"""Reads and writes maps/*.txt exactly as src/map.c (read_map_from_file) expects.

Layout:
    w h tile_size
    wall floor ceiling                 texture file names in maps/textures/
    count name...                      texture table; sprite texture_id = index into it
    type:texture_id:height  x w, h rows
    exit0 exit1 exit2 exit3            map path or NULL
    sprite_count
    x y type texture_id scale collision_r   one line per sprite, x y in tile units
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .model import (EXIT_COUNT, NO_EXIT, SOLID_TILES, MapData, Sprite, SpriteType, Tile,
                    TileType)

# Limits from the C side
TEXTURE_PATH = "maps/textures/"   # constants.h
MAX_TEXTURE_NAME = 63             # fscanf("%63s")
MAX_TEXTURE_PATH = 127            # char path[128] = TEXTURE_PATH + name
MAX_EXIT_NAME = 15                # char exits[4][16]
MAX_TEXTURES = 16                 # constants.h, size of the whole texture cache


class MapFormatError(ValueError):
    pass


@dataclass
class Issue:
    error: bool   # True: the game would reject the map; False: works, but suspicious
    message: str

    def __str__(self) -> str:
        return ("Error: " if self.error else "Warning: ") + self.message


class _Tokens:
    """Whitespace tokenizer, behaves like successive fscanf calls."""

    def __init__(self, text: str):
        self._tokens = text.split()
        self._pos = 0

    def next(self, what: str) -> str:
        if self._pos >= len(self._tokens):
            raise MapFormatError(f"unexpected end of file, expected {what}")
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def int(self, what: str) -> int:
        tok = self.next(what)
        try:
            return int(tok)
        except ValueError:
            raise MapFormatError(f"{what}: expected integer, got '{tok}'") from None

    def float(self, what: str) -> float:
        tok = self.next(what)
        try:
            return float(tok)
        except ValueError:
            raise MapFormatError(f"{what}: expected number, got '{tok}'") from None


def parse_map(text: str) -> MapData:
    t = _Tokens(text)
    width, height, tile_size = t.int("width"), t.int("height"), t.int("tile_size")
    if width <= 0 or height <= 0 or tile_size <= 0:
        raise MapFormatError("invalid header (w h tile_size must be > 0)")

    wall, floor, ceiling = t.next("wall texture"), t.next("floor texture"), t.next("ceiling texture")

    tex_count = t.int("texture table size")
    if not 0 <= tex_count <= MAX_TEXTURES:
        raise MapFormatError(f"invalid texture table size {tex_count}")
    textures = [t.next(f"texture {i}") for i in range(tex_count)]

    tiles: list[list[Tile]] = []
    for y in range(height):
        row = []
        for x in range(width):
            tok = t.next(f"tile at row {y}, col {x}")
            parts = tok.split(":")
            try:
                if len(parts) != 3:
                    raise ValueError
                tile_type, tex_id, h = int(parts[0]), int(parts[1]), float(parts[2])
                tile_type = TileType(tile_type)
            except ValueError:
                raise MapFormatError(f"invalid tile '{tok}' at row {y}, col {x}") from None
            row.append(Tile(tile_type, tex_id, h))
        tiles.append(row)

    exits = [t.next(f"exit {i}") for i in range(EXIT_COUNT)]

    count = t.int("sprite count")
    if count < 0:
        raise MapFormatError("invalid sprite count")
    sprites = []
    for i in range(count):
        what = f"sprite {i}"
        sx, sy = t.float(what), t.float(what)
        stype = t.int(what)
        try:
            stype = SpriteType(stype)
        except ValueError:
            raise MapFormatError(f"{what}: unknown sprite type {stype}") from None
        sprites.append(Sprite(sx, sy, stype, t.int(what), t.float(what), t.float(what)))

    return MapData(width, height, tile_size, wall, floor, ceiling, tiles, exits, sprites,
                   textures)


def _num(v: float) -> str:
    """1.0 -> '1.0', 0.25 -> '0.25' (keeps the style of the existing maps)."""
    v = float(v)
    return f"{v:.1f}" if v.is_integer() else repr(v)


def format_map(m: MapData) -> str:
    lines = [f"{m.width} {m.height} {m.tile_size}",
             f"{m.wall_texture} {m.floor_texture} {m.ceiling_texture}",
             " ".join([str(len(m.textures))] + m.textures)]
    for row in m.tiles:
        lines.append(" ".join(f"{int(t.type)}:{t.texture_id}:{_num(t.height)}" for t in row))
    lines.append(" ".join(m.exits))
    lines.append(str(len(m.sprites)))
    for s in m.sprites:
        lines.append(f"{_num(s.x)} {_num(s.y)} {int(s.type)} {s.texture_id} "
                     f"{_num(s.scale)} {_num(s.collision_r)}")
    return "\n".join(lines) + "\n"


def load_map(path: str | Path) -> MapData:
    return parse_map(Path(path).read_text(encoding="utf-8"))


def save_map(m: MapData, path: str | Path) -> None:
    errors = [i for i in validate(m) if i.error]
    if errors:
        raise MapFormatError("; ".join(i.message for i in errors))
    Path(path).write_text(format_map(m), encoding="utf-8")


def _check_name(value: str, what: str, max_len: int) -> list[Issue]:
    if not value:
        return [Issue(True, f"{what} is empty")]
    if any(c.isspace() for c in value):
        return [Issue(True, f"{what} '{value}' contains whitespace")]
    if len(value) > max_len:
        return [Issue(True, f"{what} '{value}' is longer than {max_len} characters")]
    return []


def validate(m: MapData, textures_dir: Path | None = None) -> list[Issue]:
    """Errors = the game's parser would reject the map. Warnings = likely mistakes."""
    issues: list[Issue] = []

    if m.width <= 0 or m.height <= 0 or m.tile_size <= 0:
        issues.append(Issue(True, "width, height and tile size must be > 0"))

    if len(m.textures) > MAX_TEXTURES:
        issues.append(Issue(True, f"texture table has more than {MAX_TEXTURES} entries"))
    table = [(f"texture {i}", name) for i, name in enumerate(m.textures)]
    for what, name in [("wall texture", m.wall_texture), ("floor texture", m.floor_texture),
                       ("ceiling texture", m.ceiling_texture)] + table:
        found = _check_name(name, what, MAX_TEXTURE_NAME)
        if not found and len(TEXTURE_PATH) + len(name) > MAX_TEXTURE_PATH:
            found = [Issue(True, f"{what} path is longer than {MAX_TEXTURE_PATH} characters")]
        if not found and textures_dir is not None and not (textures_dir / name).is_file():
            found = [Issue(False, f"{what} '{name}' not found in {textures_dir}")]
        issues += found

    if len(m.exits) != EXIT_COUNT:
        issues.append(Issue(True, f"map must have exactly {EXIT_COUNT} exits"))
    for i, e in enumerate(m.exits):
        issues += _check_name(e, f"exit {i}", MAX_EXIT_NAME)

    for i, s in enumerate(m.sprites):
        if not (0 <= s.x <= m.width and 0 <= s.y <= m.height):
            issues.append(Issue(True, f"sprite {i} at ({s.x}, {s.y}) is outside the map"))
        elif m.in_bounds(int(s.x), int(s.y)) and m.tile(int(s.x), int(s.y)).type in SOLID_TILES:
            issues.append(Issue(False, f"sprite {i} at ({s.x}, {s.y}) is inside a wall"))
        if not 0 <= s.texture_id < len(m.textures):
            issues.append(Issue(True, f"sprite {i}: texture index {s.texture_id} not in texture table"))
        if s.scale <= 0:
            issues.append(Issue(False, f"sprite {i} has scale <= 0"))
        if s.collision_r < 0:
            issues.append(Issue(False, f"sprite {i} has negative collision radius"))

    has_exit_tile = any(t.type == TileType.EXIT for row in m.tiles for t in row)
    has_exit_target = any(e != NO_EXIT for e in m.exits)
    if has_exit_tile and not has_exit_target:
        issues.append(Issue(False, "map has exit tiles, but all exits are NULL"))
    if has_exit_target and not has_exit_tile:
        issues.append(Issue(False, "exits are set, but no tile is of type EXIT"))

    border = ([m.tiles[0][x] for x in range(m.width)] + [m.tiles[-1][x] for x in range(m.width)]
              + [m.tiles[y][0] for y in range(m.height)] + [m.tiles[y][-1] for y in range(m.height)])
    if any(t.type == TileType.EMPTY for t in border):
        issues.append(Issue(False, "map border is open (rays will see the void)"))

    return issues
