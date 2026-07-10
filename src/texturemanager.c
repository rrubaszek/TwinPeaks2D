#include <texturemanager.h>

int texman_load(TextureManager* tm, const char* name) {
    // check if already loaded
    for (int i = 0; i < tm->count; i++) {
        if (strcmp(tm->slots[i]->name, name) == 0)
            return i;
    }
    // load new
    tm->slots[tm->count] = load_texture(name);
    return tm->count++;
}


Texture* texman_get(TextureManager* tm, int id) {
    return tm->slots[id];
}


void texman_free(TextureManager* tm) {
    for (int i = 0; i < tm->count; i++) {
        free_texture(tm->slots[i]);
    }
}