#include <map.h>
#include <stdlib.h>
#include <stdio.h>

Grid* read_map_from_file(const char* filename) {
    FILE* fptr = fopen(filename, "r");

    if (fptr == NULL) {
        return NULL;
    }

    Grid* g = malloc(sizeof(Grid));
    // Read map parameters
    fscanf(fptr, "%d %d %d", &g->w, &g->h, &g->tile_size);

    // Read map itself
    g->map = malloc(g->h * sizeof(int*));
    for(int i = 0; i < g->h; i++) {
        g->map[i] = malloc(g->w * sizeof(int*));
        for(int j = 0; j < g->w; j++) {
            fscanf(fptr, "%d", &g->map[i][j]);
        }
    }

    // Read exits to the next possible maps
    fscanf(fptr, "%s %s %s %s", g->exits[0], g->exits[1], g->exits[2], g->exits[3]);
    
    fclose(fptr);

    return g;
}

void free_grid(Grid *g) {
    for (int r = 0; r < g->h; r++)
        free(g->map[r]);
    free(g->map);
    free(g);
}
