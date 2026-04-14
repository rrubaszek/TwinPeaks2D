#include <SDL2/SDL.h>
#include <math.h>

#include <renderer.h>
#include <constants.h>
#include <map.h>

void draw_camera(Camera* camera, SDL_Renderer* renderer) {
    int screen_x = (int)(camera->x); // Add * TILE_SIZE?
    int screen_y = (int)(camera->y);

    SDL_Rect dot = { screen_x, screen_y, 8, 8 };
    SDL_SetRenderDrawColor(renderer, 255, 255, 0 ,255);
    SDL_RenderFillRect(renderer, &dot);

    int line_len = 100;
    int end_x = screen_x + (int)(cosf(camera->angle) * line_len);
    int end_y = screen_y + (int)(sinf(camera->angle) * line_len);

    SDL_SetRenderDrawColor(renderer, 255, 255, 0, 255);
    SDL_RenderDrawLine(renderer, screen_x, screen_y, end_x, end_y);

    printf("x=%.2f y=%.2f angle=%.2f\n", camera->x, camera->y, camera->angle);
}

void draw_map(SDL_Renderer* renderer) {
    for (int i = 0; i < MAP_WIDTH; i++) {
        for (int j = 0; j < MAP_HEIGHT; j++) {
            if (map[j][i] == 1) {
                SDL_Rect wall = { i * TILE_SIZE, j * TILE_SIZE, TILE_SIZE, TILE_SIZE };
                SDL_SetRenderDrawColor(renderer, 255, 255, 255, 1);
                SDL_RenderFillRect(renderer, &wall);
            }
        }
    }
}