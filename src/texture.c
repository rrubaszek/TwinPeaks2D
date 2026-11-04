#include <texture.h>

#include <stdlib.h>
#include <string.h>
#include <SDL2/SDL_image.h>

Texture* load_texture(const char* path) {
    SDL_Surface* surface = IMG_Load(path);
    if (!surface) {
        fprintf(stderr, "Failed to load texture from %s: %s\n", path, SDL_GetError());
        return NULL;
    }

    SDL_Surface* formatted_surface = SDL_ConvertSurfaceFormat(surface, SDL_PIXELFORMAT_ARGB8888, 0);

    if (!formatted_surface) {
        fprintf(stderr, "Failed to convert surface format: %s\n", SDL_GetError());
        SDL_FreeSurface(surface);
        return NULL;
    }

    Texture* texture = malloc(sizeof(Texture));
    if (!texture) {
        fprintf(stderr, "Out of memory loading texture %s\n", path);
        SDL_FreeSurface(formatted_surface);
        SDL_FreeSurface(surface);
        return NULL;
    }
    texture->width = formatted_surface->w;
    texture->height = formatted_surface->h;
    snprintf(texture->name, sizeof(texture->name), "%s", path);

    int size = texture->width * texture->height;
    texture->pixels = malloc(size * sizeof(Uint32));
    if (!texture->pixels) {
        fprintf(stderr, "Out of memory loading texture pixels %s\n", path);
        free(texture);
        SDL_FreeSurface(formatted_surface);
        SDL_FreeSurface(surface);
        return NULL;
    }

    // Copy row by row: surface rows may be padded (pitch >= width * 4)
    const Uint8* src = (const Uint8*)formatted_surface->pixels;
    for (int y = 0; y < texture->height; y++) {
        memcpy(&texture->pixels[y * texture->width],
               src + y * formatted_surface->pitch,
               texture->width * sizeof(Uint32));
    }

    SDL_FreeSurface(formatted_surface);
    SDL_FreeSurface(surface); // I think we need to free the original surface as well
    return texture;
}


void free_texture(Texture* texture) {
    if (texture) {
        free(texture->pixels);
        free(texture);
    }
}