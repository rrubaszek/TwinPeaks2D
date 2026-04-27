#ifndef MAP_H
#define MAP_H

#include <constants.h>

typedef struct {
    int w;
    int h;
    int tile_size;
    int** map;
    char exits[4][16]; // Maximum 16 chars in filename
} Grid;

Grid* read_map_from_file(const char* filename);
void free_grid(Grid* g);

#endif // MAP_H