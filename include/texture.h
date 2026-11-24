#ifndef TEXTURE_H
#define TEXTURE_H

#include <SDL2/SDL.h>

typedef struct texture_s {
    int width;
    int height;
    Uint32* pixels;
    int* top_opaque;   // per column: first row with alpha > 0 (height if none)

    char name[128];
} Texture;

Texture* load_texture(const char* path);
void free_texture(Texture* texture);

#endif // TEXTURE_H