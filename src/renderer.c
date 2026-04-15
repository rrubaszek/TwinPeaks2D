#include <SDL2/SDL.h>
#include <math.h>

#include <renderer.h>
#include <constants.h>
#include <map.h>

// TODO: Add shading and textures

void draw_camera(Camera* camera, SDL_Renderer* renderer) {
    int screen_x = (int)(camera->x);
    int screen_y = (int)(camera->y);

    SDL_Rect dot = { screen_x, screen_y, 8, 8 };
    SDL_SetRenderDrawColor(renderer, 255, 255, 0 ,255);
    SDL_RenderFillRect(renderer, &dot);

    int line_len = 100;
    int end_x = screen_x + (int)(cosf(camera->angle) * line_len);
    int end_y = screen_y + (int)(sinf(camera->angle) * line_len);

    SDL_SetRenderDrawColor(renderer, 255, 255, 0, 255);
    SDL_RenderDrawLine(renderer, screen_x, screen_y, end_x, end_y);

    // printf("x=%.2f y=%.2f angle=%.2f\n", camera->x, camera->y, camera->angle);
}


void draw_map(SDL_Renderer* renderer) {
    for (int i = 0; i < MAP_WIDTH; i++) {
        for (int j = 0; j < MAP_HEIGHT; j++) {
            if (map[j][i] == 1) {
                SDL_Rect wall = { i * TILE_SIZE, j * TILE_SIZE, TILE_SIZE, TILE_SIZE };
                SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255);
                SDL_RenderFillRect(renderer, &wall);
            }
        }
    }

    SDL_SetRenderDrawColor(renderer, 50, 50, 50, 255);

    for (int i = 0; i <= MAP_WIDTH; i++) {
        int x = i * TILE_SIZE;
        SDL_RenderDrawLine(renderer, x, 0, x, MAP_HEIGHT * TILE_SIZE);
    }

    for (int j = 0; j <= MAP_HEIGHT; j++) {
        int y = j * TILE_SIZE;
        SDL_RenderDrawLine(renderer, 0, y, MAP_WIDTH * TILE_SIZE, y);
    }
}


void raycaster(Camera* camera, SDL_Renderer* renderer) {

    // Each ray goes through all columns
    for (int i = 0; i < SCREEN_WIDTH; i++) {
        // double cameraX = 2.0 * i / SCREEN_WIDTH - 1; //x-coordinate in camera space
        // double rayAngle = camera->angle + (cameraX * FOV / 2.0);
        double rayAngle = camera->angle - FOV / 2.0 + (i / (double)SCREEN_WIDTH) * FOV;
        double rayDirX = cosf(rayAngle);
        double rayDirY = sinf(rayAngle);

        double posX = camera->x / TILE_SIZE;
        double posY = camera->y / TILE_SIZE;

        //which box of the map we're in
        int mapX = (int)(posX);
        int mapY = (int)(posY);

        //length of ray from current position to next x or y-side
        double sideDistX;
        double sideDistY;

        //length of ray from one x or y-side to next x or y-side
        double deltaDistX = (rayDirX == 0) ? 1e30 : fabs(1 / rayDirX);
        double deltaDistY = (rayDirY == 0) ? 1e30 : fabs(1 / rayDirY);

        //what direction to step in x or y-direction (either +1 or -1)
        int stepX;
        int stepY;

        int hit = 0; //was there a wall hit?
        int side = 0; //was a NS or a EW wall hit?

        if (rayDirX < 0) {
            stepX = -1;
            sideDistX = (posX - mapX) * deltaDistX;
        } else {
            stepX = 1;
            sideDistX = (mapX + 1.0 - posX) * deltaDistX;
        }

        if (rayDirY < 0) {
            stepY = -1;
            sideDistY = (posY - mapY) * deltaDistY;
        } else {
            stepY = 1;
            sideDistY = (mapY + 1.0 - posY) * deltaDistY;
        }

        while (hit == 0) {
            if (sideDistX < sideDistY) {
                sideDistX += deltaDistX;
                mapX += stepX;
                side = 0;
            } else {
                sideDistY += deltaDistY;
                mapY += stepY;
                side = 1;
            }

            if (mapX < 0 || mapX >= MAP_WIDTH || mapY < 0 || mapY >= MAP_HEIGHT) {
                hit = 1;
                break;
            }

            if (map[mapY][mapX] == 1) {
                hit = 1;
            }
        }

        double perpWallDist;
        if (side == 0)
            perpWallDist = sideDistX - deltaDistX;
        else
            perpWallDist = sideDistY - deltaDistY;

        // double correctedDist = perpWallDist * cos(rayAngle - camera->angle);

        int wall_height = (int)(SCREEN_HEIGHT / perpWallDist);
        int draw_start  = (SCREEN_HEIGHT - wall_height) / 2;
        int draw_end    = (SCREEN_HEIGHT + wall_height) / 2;

        SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255);
        SDL_RenderDrawLine(renderer, i, draw_start, i, draw_end);
    }
}
