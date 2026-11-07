"""In-memory map model. Mirrors include/map.h (Tile, Grid) and include/sprite.h (Sprite)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

NO_EXIT = "NULL"
EXIT_COUNT = 4


class TileType(IntEnum):
    EMPTY = 0
    WALL = 1
    EXIT = 2
    DOOR = 3
    LOWWALL = 4


class SpriteType(IntEnum):
    STATIC = 0       # table, plant, lamp ...
    INTERACTIVE = 1  # can be picked up / examined
    DOOR = 2
    NPC = 3


# Default (texture_id, height) per tile type; texture_id 0 = map default wall texture
TILE_DEFAULTS: dict[TileType, tuple[int, float]] = {
    TileType.EMPTY: (0, 0.0),
    TileType.WALL: (0, 1.0),
    TileType.EXIT: (0, 1.0),
    TileType.DOOR: (0, 1.0),
    TileType.LOWWALL: (0, 0.5),
}

# Tiles the game treats as blocking (src/map.c: is_tile_solid)
SOLID_TILES = {TileType.WALL, TileType.LOWWALL}

# Tiles the game draws as walls; only these keep a texture_id
TEXTURED_TILES = SOLID_TILES


@dataclass
class Tile:
    type: TileType = TileType.EMPTY
    texture_id: int = 0
    height: float = 0.0

    @classmethod
    def of(cls, tile_type: TileType, texture_id: int = 0) -> Tile:
        """texture_id: 0 = map wall texture, k = texture table entry k-1 (walls only)."""
        default_tex, height = TILE_DEFAULTS[tile_type]
        return cls(tile_type, texture_id if tile_type in TEXTURED_TILES else default_tex, height)


@dataclass
class Sprite:
    x: float                 # tile units, like Sprite.x/y in the game
    y: float
    type: SpriteType = SpriteType.STATIC
    texture_id: int = 0
    scale: float = 1.0       # 1.0 = person height
    collision_r: float = 0.0  # 0 = no collision
    z: float = 0.0           # base height in wall units: 0 = floor, 0.5 = on a 0.5 counter


@dataclass
class MapData:
    width: int
    height: int
    tile_size: int
    wall_texture: str
    floor_texture: str
    ceiling_texture: str
    tiles: list[list[Tile]]  # tiles[y][x]
    exits: list[str] = field(default_factory=lambda: [NO_EXIT] * EXIT_COUNT)
    sprites: list[Sprite] = field(default_factory=list)
    textures: list[str] = field(default_factory=list)  # sprites: index, tiles: index + 1

    @classmethod
    def new(cls, width: int, height: int, tile_size: int = 100,
            wall_texture: str = "drapes.jpeg", floor_texture: str = "floor.png",
            ceiling_texture: str = "floor.png", walled: bool = True) -> MapData:
        tiles = [[Tile.of(TileType.EMPTY) for _ in range(width)] for _ in range(height)]
        m = cls(width, height, tile_size, wall_texture, floor_texture, ceiling_texture, tiles)
        if walled:
            m.surround_with_walls()
        return m

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def tile(self, x: int, y: int) -> Tile:
        return self.tiles[y][x]

    def texture_index(self, name: str) -> int:
        """Index of `name` in the texture table, appended if missing."""
        if name not in self.textures:
            self.textures.append(name)
        return self.textures.index(name)

    def set_tile(self, x: int, y: int, tile_type: TileType, texture_id: int = 0) -> bool:
        """Sets tile type with its default height. Returns True if anything changed."""
        if not self.in_bounds(x, y):
            return False
        new = Tile.of(tile_type, texture_id)
        if self.tiles[y][x] == new:
            return False
        self.tiles[y][x] = new
        return True

    def surround_with_walls(self) -> None:
        for x in range(self.width):
            self.set_tile(x, 0, TileType.WALL)
            self.set_tile(x, self.height - 1, TileType.WALL)
        for y in range(self.height):
            self.set_tile(0, y, TileType.WALL)
            self.set_tile(self.width - 1, y, TileType.WALL)

    def resize(self, width: int, height: int) -> None:
        """Keeps content anchored at the top-left corner; new tiles are empty."""
        rows = [row[:width] + [Tile.of(TileType.EMPTY) for _ in range(width - len(row[:width]))]
                for row in self.tiles[:height]]
        while len(rows) < height:
            rows.append([Tile.of(TileType.EMPTY) for _ in range(width)])
        self.tiles = rows
        self.width, self.height = width, height

    def sprites_outside(self) -> list[Sprite]:
        return [s for s in self.sprites
                if not (0 <= s.x <= self.width and 0 <= s.y <= self.height)]
