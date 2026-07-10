#ifndef TEXTUREMANAGER_H
#define TEXTUREMANAGER_H

#include <texture.h>
#include <constants.h>

typedef struct {
    Texture* slots[MAX_TEXTURES];
    int count;
} TextureManager;

int texman_load(TextureManager* tm, const char* name);
Texture* texman_get(TextureManager* tm, int id);
void texman_free(TextureManager* tm);

#endif // TEXTUREMANAGER_H