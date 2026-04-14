#include <renderer.h>
#include <constants.h>
#include <SDL2/SDL.h>
#include <math.h>

void draw_camera(Camera* camera, SDL_Renderer* renderer) {
    int screen_x = (int)(camera->x * TILE_SIZE);
    int screen_y = (int)(camera->y * TILE_SIZE);

    SDL_Rect dot = { screen_x, screen_y, 8, 8 };
    SDL_SetRenderDrawColor(renderer, 255, 255, 0 ,255);
    SDL_RenderFillRect(renderer, &dot);

    int line_len = 20;
    int end_x = screen_x + (int)(cosf(camera->angle) * line_len);
    int end_y = screen_y + (int)(sinf(camera->angle) * line_len);

    SDL_SetRenderDrawColor(renderer, 255, 255, 0, 255);
    SDL_RenderDrawLine(renderer, screen_x, screen_y, end_x, end_y);

    printf("x=%.2f y=%.2f angle=%.2f\n", camera->x, camera->y, camera->angle);
}