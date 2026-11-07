from pathlib import Path

import pytest

from tpmap.model import MapData, Sprite, SpriteType, TileType
from tpmap.txt_format import MapFormatError, format_map, load_map, parse_map, validate

MAPS_DIR = Path(__file__).resolve().parents[2] / "maps"
GAME_MAPS = sorted(MAPS_DIR.glob("*.txt"))


@pytest.mark.parametrize("path", GAME_MAPS, ids=lambda p: p.name)
def test_roundtrip_game_maps(path):
    original = path.read_text()
    # Identical except the trailing newline the editor always writes
    assert format_map(load_map(path)) == original.rstrip("\n") + "\n"


@pytest.mark.parametrize("path", GAME_MAPS, ids=lambda p: p.name)
def test_game_maps_have_no_errors(path):
    assert [i for i in validate(load_map(path)) if i.error] == []


def test_new_map_roundtrip_with_sprites():
    m = MapData.new(6, 5)
    m.textures = ["sprite_coffee.bmp", "sprite_pie.bmp"]
    m.sprites.append(Sprite(2.5, 2.5, SpriteType.INTERACTIVE, 1, 0.3, 0.25))
    m.exits[2] = "maps/map.txt"
    m.set_tile(5, 2, TileType.EXIT)
    assert parse_map(format_map(m)) == m


def test_new_map_is_walled():
    m = MapData.new(4, 3)
    assert m.tile(0, 0).type == TileType.WALL
    assert m.tile(1, 1).type == TileType.EMPTY


def test_resize_keeps_top_left():
    m = MapData.new(4, 4)
    m.resize(6, 2)
    assert (m.width, m.height) == (6, 2)
    assert len(m.tiles) == 2 and all(len(r) == 6 for r in m.tiles)
    assert m.tile(0, 0).type == TileType.WALL
    assert m.tile(5, 1).type == TileType.EMPTY


@pytest.mark.parametrize("text, msg", [
    ("0 5 100", "invalid header"),
    ("1 1 100 a b c 17", "invalid texture table size"),
    ("2 1 100 a b c 0 1:1:1.0", "unexpected end"),
    ("1 1 100 a b c 0 9:0:0.0 NULL NULL NULL NULL 0", "invalid tile"),
    ("1 1 100 a b c 0 0:0:0.0 NULL NULL NULL NULL 1 0.5 0.5 7 0 1.0 0.0", "unknown sprite type"),
])
def test_parse_errors(text, msg):
    with pytest.raises(MapFormatError, match=msg):
        parse_map(text)


def test_validate_limits():
    m = MapData.new(3, 3)
    m.exits[0] = "maps/very_long_name.txt"
    m.wall_texture = "has space.png"
    m.sprites.append(Sprite(10.0, 1.0))
    m.sprites.append(Sprite(1.5, 1.5, texture_id=0))  # empty texture table
    errors = [i.message for i in validate(m) if i.error]
    assert any("texture index 0 not in texture table" in e for e in errors)
    assert any("exit 0" in e for e in errors)
    assert any("whitespace" in e for e in errors)
    assert any("outside the map" in e for e in errors)


def test_tile_texture_roundtrip_and_validate():
    m = MapData.new(4, 3)
    m.textures = ["forest.jpeg", "drapes.jpeg"]
    m.set_tile(1, 1, TileType.LOWWALL, texture_id=2)   # table entry 1
    m.set_tile(2, 1, TileType.EXIT, texture_id=2)      # not a wall: texture dropped
    assert m.tile(1, 1).texture_id == 2 and m.tile(2, 1).texture_id == 0
    assert parse_map(format_map(m)) == m
    assert [i for i in validate(m) if i.error] == []

    m.tiles[0][0].texture_id = 3                       # table has only 2 entries
    errors = [i.message for i in validate(m) if i.error]
    assert any("row 0, col 0: texture 3 not in texture table" in e for e in errors)


def _with_sprite_lines(lines: str) -> str:
    m = MapData.new(4, 4)
    m.textures = ["sprite_pie.png"]
    m.set_tile(1, 1, TileType.LOWWALL)
    return format_map(m).rsplit("\n0\n", 1)[0] + "\n" + lines


def test_sprite_z_optional_field():
    m = parse_map(_with_sprite_lines("2\n1.5 1.5 1 0 0.3 0.0 0.5\n2.5 2.5 0 0 1.0 0.0\n"))
    assert [s.z for s in m.sprites] == [0.5, 0.0]
    assert format_map(m).endswith("1.5 1.5 1 0 0.3 0.0 0.5\n2.5 2.5 0 0 1.0 0.0\n")  # z only if != 0
    assert parse_map(format_map(m)) == m


def test_sprite_z_is_not_read_from_next_line():
    # 6 fields, then the next sprite line: its first number must not become z
    m = parse_map(_with_sprite_lines("2\n1.5 1.5 1 0 0.3 0.0\n2.5 2.5 0 0 1.0 0.0\n"))
    assert [(s.x, s.z) for s in m.sprites] == [(1.5, 0.0), (2.5, 0.0)]


def test_validate_sprite_on_counter():
    m = parse_map(_with_sprite_lines("1\n1.5 1.5 1 0 0.3 0.0 0.5\n"))
    assert not any("inside a wall" in i.message for i in validate(m))
    m.sprites[0].z = 0.0
    assert any("inside a wall" in i.message for i in validate(m))
    m.sprites[0].z = -0.1
    assert any("negative height" in i.message for i in validate(m))
