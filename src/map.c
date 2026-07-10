#include <map.h>
#include <stdlib.h>
#include <stdio.h>

Grid* read_map_from_file(const char* filename, TextureManager* tm) {
    FILE* fptr = fopen(filename, "r");

    if (fptr == NULL) {
        return NULL;
    }

    Grid* g = malloc(sizeof(Grid));
    if (!g) { 
        fclose(fptr); return NULL; 
    }

    // Read map parameters
    fscanf(fptr, "%d %d %d", &g->w, &g->h, &g->tile_size);

    // Read map textures
    char wall_name[64], floor_name[64], ceiling_name[64];
    fscanf(fptr, "%s %s %s", wall_name, floor_name, ceiling_name);

    char wall_path[128], floor_path[128], ceilling_path[128];
    snprintf(wall_path, sizeof(wall_path), "%s%s", TEXTURE_PATH, wall_name);
    snprintf(floor_path, sizeof(floor_path), "%s%s", TEXTURE_PATH, floor_name);
    snprintf(ceilling_path, sizeof(ceilling_path), "%s%s", TEXTURE_PATH, ceiling_name);

    g->wall_tex_id    = texman_load(tm, wall_path);
    g->floor_tex_id   = texman_load(tm, floor_path);
    g->ceiling_tex_id = texman_load(tm, ceilling_path);

    // Read map itself
    g->map = malloc(g->h * sizeof(Tile*));
    for(int i = 0; i < g->h; i++) {
        g->map[i] = calloc(g->w, sizeof(Tile));
        for (int j = 0; j < g->w; j++) {
            int type, tex_id;
            float height;
            fscanf(fptr, "%d:%d:%f", &type, &tex_id, &height);
            g->map[i][j].type = (TileType)type;
            g->map[i][j].texture_id = tex_id;
            g->map[i][j].height = height;
        }
    }

    // Read exits to the next possible maps
    fscanf(fptr, "%s %s %s %s", g->exits[0], g->exits[1], g->exits[2], g->exits[3]);

    // Read sprites
    fscanf(fptr, "%d", &g->sprite_count);
    g->sprites = (g->sprite_count > 0) ? malloc(g->sprite_count * sizeof(Sprite)) : NULL;
    for (int i = 0; i < g->sprite_count; i++) {
        int stype;
        fscanf(fptr, "%lf %lf %d %d %f %f",
            &g->sprites[i].x,
            &g->sprites[i].y,
            &stype,
            &g->sprites[i].texture_id,
            &g->sprites[i].scale,
            &g->sprites[i].collision_r
        );
        g->sprites[i].type = (SpriteType)stype;
        g->sprites[i].visible = true;
        g->sprites[i].state = NULL;
    }

    fclose(fptr);

    return g;
}

void free_grid(Grid* g) {
    if (!g) return;
    for (int i = 0; i < g->h; i++)
        free(g->map[i]);
    free(g->map);
    free(g->sprites);
    free(g);
}

bool is_tile_solid(Tile* t) {
    return t->type == TILE_WALL || t->type == TILE_LOWWALL;
}

Tile* get_tile(Grid* g, int x, int y) {
    if (x < 0 || x >= g->w || y < 0 || y >= g->h) return NULL;
    return &g->map[y][x];
}
