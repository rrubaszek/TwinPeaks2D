#ifndef MAP_H
#define MAP_H

#include <constants.h>
#include <sprite.h>
#include <texture.h>
#include <texturemanager.h>

#include <stdbool.h>

typedef enum {
    TILE_EMPTY   = 0,
    TILE_WALL    = 1,
    TILE_EXIT    = 2,
    TILE_DOOR    = 3,
    TILE_LOWWALL = 4,
} TileType;

typedef struct {
    int texture_id;
    float height;
    TileType type;
} Tile;

typedef struct {
    int w;
    int h;
    int tile_size;

    Tile** map;

    Sprite* sprites;

    int sprite_count;

    // Textures are managed by texturemanager, grid only stores id's for lookup
    int wall_tex_id;
    int floor_tex_id;
    int ceiling_tex_id;

    char exits[4][16];
} Grid;

Grid* read_map_from_file(const char* filename, TextureManager* tm);
void free_grid(Grid* g);

Tile* get_tile(Grid* g, int x, int y);
bool is_tile_solid(Tile* t);

#endif // MAP_H