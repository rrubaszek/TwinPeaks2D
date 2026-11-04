#include <texturemanager.h>
#include <stdio.h>
#include <string.h>

int texman_load(TextureManager* tm, const char* name) {
    // check if already loaded
    for (int i = 0; i < tm->count; i++) {
        if (strcmp(tm->slots[i]->name, name) == 0)
            return i;
    }
    if (tm->count >= MAX_TEXTURES) {
        fprintf(stderr, "Texture cache full (%d), cannot load %s\n", MAX_TEXTURES, name);
        return -1;
    }
    // load new; failed loads do not take a slot
    Texture* tex = load_texture(name);
    if (!tex)
        return -1;
    tm->slots[tm->count] = tex;
    return tm->count++;
}


Texture* texman_get(TextureManager* tm, int id) {
    if (id < 0 || id >= tm->count)
        return NULL;
    return tm->slots[id];
}


void texman_free(TextureManager* tm) {
    for (int i = 0; i < tm->count; i++) {
        free_texture(tm->slots[i]);
    }
}