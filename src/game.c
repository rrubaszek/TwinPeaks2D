#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <stdbool.h>
#include <SDL2/SDL.h>

#include <map.h>
#include <game.h>
#include <camera.h>
#include <constants.h>
#include <renderer.h>
#include <framebuffer.h>
#include <texture.h>


int main(void) {

    Game game = {
        .renderer = NULL,
        .window = NULL,
        .background = NULL, // Later to add some background texture
        .grid = NULL,
    };

    Camera cam = {
        .x = 400,
        .y = 500,
        .moveVel = 0,
        .angle = 4.7,
        .rotationVel = 0,
    };

    if (sdl_initialize(&game)) {
        sdl_cleanup(&game, EXIT_FAILURE);
    }

    SDL_Event event;
    Texture* forest = load_texture("maps/forest.jpeg");
    SDL_Texture* screen_texture = SDL_CreateTexture(
        game.renderer,
        SDL_PIXELFORMAT_ARGB8888,
        SDL_TEXTUREACCESS_STREAMING,
        SCREEN_WIDTH,
        SCREEN_HEIGHT
    );
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

        // SDL_SetRenderDrawColor(game.renderer, 0, 0, 0, 255);
        // SDL_RenderClear(game.renderer);

        // Handle input
        const Uint8* keys = SDL_GetKeyboardState(NULL);
        handle_input(&cam, keys);

        // Handle move
        move(&cam, &game);

        // Functions used to debug
        // draw_map(game.renderer, game.grid);
        // draw_camera(&cam, game.renderer);

        // Draw celling and floor before raycaster, which draws the walls
        // SDL_SetRenderDrawColor(game.renderer, 50, 50, 50, 255);
        // SDL_RenderFillRect(game.renderer, &floor);

        // SDL_SetRenderDrawColor(game.renderer, 75, 15, 255, 255);
        // SDL_RenderFillRect(game.renderer, &celling);  

        // Handle visuals - rendering
        clear_framebuffer(0x00000000);

        // Floor and celling
        for (int y = 0; y < SCREEN_HEIGHT / 2; y++) {
            for (int x = 0; x < SCREEN_WIDTH; x++)
                put_pixel(x, y, 0xFF111111);
        }

        for (int y = SCREEN_HEIGHT / 2; y < SCREEN_HEIGHT; y++) {
            for (int x = 0; x < SCREEN_WIDTH; x++)
                put_pixel(x, y, 0xFF333333);
        }

        raycaster(&cam, forest, game.grid);
        // render_sprites(&cam, game.renderer, game.grid);

        // Upload framebuffer
        SDL_UpdateTexture(
            screen_texture,
            NULL,
            framebuffer,
            SCREEN_WIDTH * sizeof(Uint32)
        );

        // Present on screen
        SDL_RenderClear(game.renderer);
        SDL_RenderCopy(game.renderer, screen_texture, NULL, NULL);
        SDL_RenderPresent(game.renderer);

        SDL_Delay(16);
    }

    sdl_cleanup(&game, EXIT_SUCCESS);

    return 0;
}


void sdl_cleanup(Game* game, int exit_code) {
    SDL_DestroyRenderer(game->renderer);
    SDL_DestroyWindow(game->window);
    SDL_Quit();

    printf("Window and renderer closed successfully.\n");

    if (game->grid){
        free_grid(game->grid);
        printf("Map destroyed successfully\n");
    }

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

    game->grid = read_map_from_file("maps/map2.txt");
    if (!game->grid) {
        printf("Failed to create game grid: %s\n", strerror(errno));
        return true;
    }

    printf("Window, renderer and grid initialized successfully.\n");

    return false;
}
