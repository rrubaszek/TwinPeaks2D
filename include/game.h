#ifndef GAME_H
#define GAME_H

#include <SDL2/SDL.h>
#include <stdbool.h>
#include <map.h>

typedef struct {
    SDL_Window* window;
    SDL_Renderer* renderer;
    SDL_Texture* background;
    Grid* grid;
} Game;

bool sdl_initialize(Game* game);
void sdl_cleanup(Game* game, int exit_code);

#endif // GAME_H