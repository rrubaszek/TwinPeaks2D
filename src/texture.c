#include <texture.h>

#include <stdlib.h>
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
    texture->width = formatted_surface->w;
    texture->height = formatted_surface->h;

    int size = texture->width * texture->height;
    texture->pixels = malloc(size * sizeof(Uint32));

    Uint32* src_pixels = (uint32_t*)formatted_surface->pixels;
    for (int i = 0; i < size; i++) {
        texture->pixels[i] = src_pixels[i];
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