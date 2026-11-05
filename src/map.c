#include <map.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

Grid* read_map_from_file(const char* filename, TextureManager* tm) {
    FILE* fptr = fopen(filename, "r");

    if (fptr == NULL) {
        fprintf(stderr, "%s: cannot open map file\n", filename);
        return NULL;
    }

    // calloc: pointers start as NULL, so free_grid is safe on partial grids
    Grid* g = calloc(1, sizeof(Grid));
    if (!g) {
        fprintf(stderr, "%s: out of memory\n", filename);
        fclose(fptr);
        return NULL;
    }

    // Read map parameters
    if (fscanf(fptr, "%d %d %d", &g->w, &g->h, &g->tile_size) != 3
        || g->w <= 0 || g->h <= 0 || g->tile_size <= 0) {
        fprintf(stderr, "%s: invalid header (w h tile_size)\n", filename);
        goto fail;
    }

    // Read default map textures
    char wall_name[64], floor_name[64], ceiling_name[64];
    if (fscanf(fptr, "%63s %63s %63s", wall_name, floor_name, ceiling_name) != 3) {
        fprintf(stderr, "%s: missing texture names\n", filename);
        goto fail;
    }

    char wall_path[128], floor_path[128], ceilling_path[128];
    snprintf(wall_path, sizeof(wall_path), "%s%s", TEXTURE_PATH, wall_name);
    snprintf(floor_path, sizeof(floor_path), "%s%s", TEXTURE_PATH, floor_name);
    snprintf(ceilling_path, sizeof(ceilling_path), "%s%s", TEXTURE_PATH, ceiling_name);

    g->wall_tex_id    = texman_load(tm, wall_path);
    g->floor_tex_id   = texman_load(tm, floor_path);
    g->ceiling_tex_id = texman_load(tm, ceilling_path);
    if (g->wall_tex_id < 0 || g->floor_tex_id < 0 || g->ceiling_tex_id < 0) {
        fprintf(stderr, "%s: failed to load default textures\n", filename);
        goto fail;
    }

    // Read map texture table: count, then file names; sprites refer to it by index
    int tex_count;
    if (fscanf(fptr, "%d", &tex_count) != 1 || tex_count < 0 || tex_count > MAX_TEXTURES) {
        fprintf(stderr, "%s: invalid texture table size\n", filename);
        goto fail;
    }
    int tex_ids[MAX_TEXTURES];
    for (int i = 0; i < tex_count; i++) {
        char name[64], path[128];
        if (fscanf(fptr, "%63s", name) != 1) {
            fprintf(stderr, "%s: missing texture name %d\n", filename, i);
            goto fail;
        }
        snprintf(path, sizeof(path), "%s%s", TEXTURE_PATH, name);
        tex_ids[i] = texman_load(tm, path);
        if (tex_ids[i] < 0) {
            fprintf(stderr, "%s: failed to load texture %s\n", filename, name);
            goto fail;
        }
    }

    // Read map itself
    g->map = calloc(g->h, sizeof(Tile*));
    if (!g->map) {
        fprintf(stderr, "%s: out of memory\n", filename);
        goto fail;
    }
    for(int i = 0; i < g->h; i++) {
        g->map[i] = calloc(g->w, sizeof(Tile));
        if (!g->map[i]) {
            fprintf(stderr, "%s: out of memory\n", filename);
            goto fail;
        }
        for (int j = 0; j < g->w; j++) {
            int type, tex_id;
            float height;
            if (fscanf(fptr, "%d:%d:%f", &type, &tex_id, &height) != 3) {
                fprintf(stderr, "%s: invalid tile at row %d, col %d\n", filename, i, j);
                goto fail;
            }
            g->map[i][j].type = (TileType)type;
            // TODO: Where to load specific textures like window, door, painting ... ?
            g->map[i][j].texture_id = tex_id; // Placeholder for specific textures - currently not loaded
            g->map[i][j].height = height;
        }
    }

    // Read exits to the next possible maps
    // Read into a larger buffer to detect names that don't fit exits[i]
    for (int i = 0; i < 4; i++) {
        char buf[128];
        if (fscanf(fptr, "%127s", buf) != 1) {
            fprintf(stderr, "%s: invalid exits line\n", filename);
            goto fail;
        }
        size_t len = strlen(buf);
        if (len >= sizeof(g->exits[i])) {
            fprintf(stderr, "%s: exit name too long (max %zu): %s\n",
                    filename, sizeof(g->exits[i]) - 1, buf);
            goto fail;
        }
        memcpy(g->exits[i], buf, len + 1);
    }

    // Read sprites
    if (fscanf(fptr, "%d", &g->sprite_count) != 1 || g->sprite_count < 0) {
        fprintf(stderr, "%s: invalid sprite count\n", filename);
        goto fail;
    }
    if (g->sprite_count > 0) {
        g->sprites = malloc(g->sprite_count * sizeof(Sprite));
        if (!g->sprites) {
            fprintf(stderr, "%s: out of memory\n", filename);
            goto fail;
        }
    }
    for (int i = 0; i < g->sprite_count; i++) {
        int stype;
        if (fscanf(fptr, "%lf %lf %d %d %f %f",
                   &g->sprites[i].x,
                   &g->sprites[i].y,
                   &stype,
                   &g->sprites[i].texture_id,
                   &g->sprites[i].scale,
                   &g->sprites[i].collision_r) != 6) {
            fprintf(stderr, "%s: invalid sprite %d\n", filename, i);
            goto fail;
        }
        int t = g->sprites[i].texture_id;
        if (t < 0 || t >= tex_count) {
            fprintf(stderr, "%s: sprite %d: texture index %d not in table\n", filename, i, t);
            goto fail;
        }
        g->sprites[i].texture_id = tex_ids[t];
        g->sprites[i].type = (SpriteType)stype;
        g->sprites[i].visible = true;
        g->sprites[i].state = NULL;
    }

    fclose(fptr);

    return g;

fail:
    free_grid(g);
    fclose(fptr);
    return NULL;
}

void free_grid(Grid* g) {
    if (!g) return;
    // Grid may be partially built (parse error) - rows/map can be NULL
    if (g->map) {
        for (int i = 0; i < g->h; i++)
            free(g->map[i]);
    }
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
