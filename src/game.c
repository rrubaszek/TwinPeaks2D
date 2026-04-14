#include <stdio.h>
#include <stdbool.h>
#include <SDL2/SDL.h>

#include <game.h>
#include <camera.h>
#include <constants.h>
#include <renderer.h>

int main(void) {
    Game game = {
        .renderer = NULL,
        .window = NULL,
        .background = NULL, // Later to add some background texture
    };

    Camera cam = {
        .x = 0,
        .y = 0,
        .moveVel = 0,
        .angle = 0,
        .rotationVel = 0,
    };

    if (sdl_initialize(&game)) {
        sdl_cleanup(&game, EXIT_FAILURE);
    }

    SDL_Event event;
    while (true) {

        while (SDL_PollEvent(&event)) {

            switch (event.type) {
                case SDL_QUIT:
                    sdl_cleanup(&game, EXIT_SUCCESS);
                    break;
                case SDL_KEYDOWN:
                    if (event.key.keysym.sym == SDLK_ESCAPE) {
                        sdl_cleanup(&game, EXIT_SUCCESS);
                    }
                    break;
            }

        }

        SDL_SetRenderDrawColor(game.renderer, 0, 0, 0, 255);
        SDL_RenderClear(game.renderer);

        const Uint8* keys = SDL_GetKeyboardState(NULL);
        handle_input(&cam, keys);
        move(&cam);

        draw_camera(&cam, game.renderer);
        draw_map(game.renderer);
        SDL_RenderPresent(game.renderer);

        SDL_Delay(16);
    }

    sdl_cleanup(&game, EXIT_SUCCESS);

    printf("Hello, World!\n");
    return 0;
}

void sdl_cleanup(Game* game, int exit_code) {
    SDL_DestroyRenderer(game->renderer);
    SDL_DestroyWindow(game->window);
    SDL_Quit();
    exit(exit_code);
}

bool sdl_initialize(Game* game) {
    if (SDL_Init(SDL_INIT_EVERYTHING)) {
        fprintf(stderr, "Failed to initialize SDL: %s\n", SDL_GetError());
        return true;
    }
    
    game->window = SDL_CreateWindow("Twin Peaks", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, SCREEN_WIDTH, SCREEN_HEIGHT, 0);
    if (!game->window) {
        printf("Failed to create window: %s\n", SDL_GetError());
        return true;
    }

    game->renderer = SDL_CreateRenderer(game->window, -1, 0);
    if (!game->renderer) {
        printf("Failed to create renderer: %s\n", SDL_GetError());
        return true;
    }

    printf("Window and renderer initialized successfully.\n");

    return false;
}