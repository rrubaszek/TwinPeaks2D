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
#include <profiler.h>
#include <timer.h>


int main(void) {

    Game game = {
        .renderer = NULL,
        .window = NULL,
        .background = NULL, // Later to add some background texture
        .grid = NULL,
        .texman = NULL,
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
    CameraView view;
    SDL_Texture* screen_texture = SDL_CreateTexture(
        game.renderer,
        SDL_PIXELFORMAT_ARGB8888,
        SDL_TEXTUREACCESS_STREAMING,
        SCREEN_WIDTH,
        SCREEN_HEIGHT
    );
    if (!screen_texture) {
        fprintf(stderr, "Failed to create screen texture: %s\n", SDL_GetError());
        sdl_cleanup(&game, EXIT_FAILURE);
    }

    double last_ms = timer_now_ms();
    while (true) {
        double now_ms = timer_now_ms();
        double dt = (now_ms - last_ms) / 1000.0;
        last_ms = now_ms;
        if (dt > MAX_DT) dt = MAX_DT;

        prof_begin(PROF_FRAME);

        while (SDL_PollEvent(&event)) {

            switch (event.type) {
                case SDL_QUIT:
                    sdl_cleanup(&game, EXIT_SUCCESS);
                    break;
                case SDL_KEYDOWN:
                    if (event.key.keysym.sym == SDLK_ESCAPE) {
                        sdl_cleanup(&game, EXIT_SUCCESS);
                    }
                    if (event.key.keysym.sym == SDLK_F11 && !event.key.repeat) {
                        toggle_fullscreen(&game);
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
        move(&cam, &game, dt);

        view = camera_get_view(&cam, game.grid);

        // Functions used to debug
        // draw_map(game.renderer, game.grid);
        // draw_camera(&cam, game.renderer);

        // Old SDL_Renderer floor/ceiling fill (unused, framebuffer path below)
        // SDL_SetRenderDrawColor(game.renderer, 50, 50, 50, 255);
        // SDL_RenderFillRect(game.renderer, &floor);

        // SDL_SetRenderDrawColor(game.renderer, 75, 15, 255, 255);
        // SDL_RenderFillRect(game.renderer, &celling);  

        // Handle visuals - rendering
        prof_begin(PROF_CLEAR);
        clear_framebuffer(0x00000000);
        prof_end(PROF_CLEAR);

        // Walls first: raycaster records each column's wall span, and the floor pass
        // skips those pixels. This order is required.
        prof_begin(PROF_WALLS);
        raycaster(&view, game.texman, game.grid);
        prof_end(PROF_WALLS);

        prof_begin(PROF_FLOOR);
        render_floor_ceiling(&view, game.texman, game.grid);
        prof_end(PROF_FLOOR);

        prof_begin(PROF_SPRITES);
        render_sprites(&view, game.texman, game.grid);
        prof_end(PROF_SPRITES);

        // Upload framebuffer
        prof_begin(PROF_PRESENT);
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
        prof_end(PROF_PRESENT);

        prof_end(PROF_FRAME);
        prof_frame_done();

        // Frame cap: sleep only for what is left of the frame budget
        double frame_ms = timer_now_ms() - now_ms;
        if (frame_ms < FRAME_DELAY) {
            SDL_Delay((Uint32)(FRAME_DELAY - frame_ms));
        }
    }

    sdl_cleanup(&game, EXIT_SUCCESS);

    return 0;
}


void sdl_cleanup(Game* game, int exit_code) {
    // Release in reverse order of initialization
    if (game->grid){
        free_grid(game->grid);
        printf("Map destroyed successfully\n");
    }

    if (game->texman) {
        texman_free(game->texman);
        free(game->texman);
        printf("Textures destroyed succcessfully\n");
    }

    // Destroying the renderer also frees textures created with it
    SDL_DestroyRenderer(game->renderer);
    SDL_DestroyWindow(game->window);
    SDL_Quit();

    printf("Window and renderer closed successfully.\n");

    exit(exit_code);
}


bool sdl_initialize(Game* game) {
    if (SDL_Init(SDL_INIT_VIDEO)) {
        fprintf(stderr, "Failed to initialize SDL: %s\n", SDL_GetError());
        return true;
    }
    
    game->window = SDL_CreateWindow("Twin Peaks", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, SCREEN_WIDTH, SCREEN_HEIGHT, 0);
    if (!game->window) {
        fprintf(stderr, "Failed to create window: %s\n", SDL_GetError());
        return true;
    }

    game->renderer = SDL_CreateRenderer(game->window, -1, 0);
    if (!game->renderer) {
        fprintf(stderr, "Failed to create renderer: %s\n", SDL_GetError());
        return true;
    }

    // Nearest-neighbour scaling: crisp pixels when the window is larger than the render
    SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "0");

    // Fixed 800x600 render, scaled to the window with aspect ratio kept (letterbox)
    if (SDL_RenderSetLogicalSize(game->renderer, SCREEN_WIDTH, SCREEN_HEIGHT)) {
        fprintf(stderr, "Failed to set logical size: %s\n", SDL_GetError());
        return true;
    }

    game->texman = calloc(1, sizeof(TextureManager));
    if (!game->texman) {
        fprintf(stderr, "Failed to allocate texture manager\n");
        return true;
    }
    game->grid = read_map_from_file("maps/map.txt", game->texman);
    if (!game->grid) {
        // read_map_from_file already printed the reason
        fprintf(stderr, "Failed to create game grid\n");
        return true;
    }

    printf("Window, renderer and grid initialized successfully.\n");

    return false;
}


// Switches between windowed and desktop fullscreen; on failure keeps the current mode
void toggle_fullscreen(Game* game) {
    Uint32 flags = SDL_GetWindowFlags(game->window);
    bool is_fullscreen = flags & SDL_WINDOW_FULLSCREEN_DESKTOP;

    if (SDL_SetWindowFullscreen(game->window, is_fullscreen ? 0 : SDL_WINDOW_FULLSCREEN_DESKTOP)) {
        fprintf(stderr, "Failed to toggle fullscreen: %s\n", SDL_GetError());
    }
}
