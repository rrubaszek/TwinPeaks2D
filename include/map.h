#ifndef MAP_H
#define MAP_H

#include <constants.h>

typedef struct {
    int w;
    int h;
    int tile_size;
    int** map;
} Grid;

Grid* read_map_from_file(const char* filename);
void free_grid(Grid* g);

#endif // MAP_H