#include <SDL2/SDL.h>
#include <math.h>

#include <renderer.h>

// TODO: Add shading and textures

double z_buffer[SCREEN_WIDTH]; // Store distance to walls for each column for texture mapping

void draw_camera(Camera* camera, SDL_Renderer* renderer) {
    int screen_x = (int)camera->x;
    int screen_y = (int)camera->y;

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


void draw_map(SDL_Renderer* renderer, const Grid* g) {
    for (int i = 0; i < g->w; i++) {
        for (int j = 0; j < g->h; j++) {
            if (g->map[j][i] == 1) {
                SDL_Rect wall = { i * g->tile_size, j * g->tile_size, g->tile_size, g->tile_size };
                SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255);
                SDL_RenderFillRect(renderer, &wall);
            }
        }
    }

    SDL_SetRenderDrawColor(renderer, 50, 50, 50, 255);

    for (int i = 0; i <= g->w; i++) {
        int x = i * g->tile_size;
        SDL_RenderDrawLine(renderer, x, 0, x, g->h * g->tile_size);
    }

    for (int j = 0; j <= g->h; j++) {
        int y = j * g->tile_size;
        SDL_RenderDrawLine(renderer, 0, y, g->w * g->tile_size, y);
    }
}


void raycaster(Camera* camera, SDL_Renderer* renderer, const Grid* g) {

    // Each ray goes through all columns
    for (int i = 0; i < SCREEN_WIDTH; i++) {

        double cameraX = 2 * i / (double)SCREEN_WIDTH - 1;

        double dirX = cos(camera->angle);
        double dirY = sin(camera->angle);

        double planeX = -dirY * tan(FOV / 2);
        double planeY =  dirX * tan(FOV / 2);

        double rayDirX = dirX + planeX * cameraX;
        double rayDirY = dirY + planeY * cameraX;

        double posX = camera->x / g->tile_size;
        double posY = camera->y / g->tile_size;

        //which box of the map we're in
        int mapX = (int)posX;
        int mapY = (int)posY;

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

            if (mapX < 0 || mapX >= g->w || mapY < 0 || mapY >= g->h) {
                hit = 1;
                break;
            }

            if (g->map[mapY][mapX] == 1) {
                hit = 1;
            }
        }

        double perpWallDist;
        if (side == 0)
            perpWallDist = sideDistX - deltaDistX;
        else
            perpWallDist = sideDistY - deltaDistY;

        z_buffer[i] = perpWallDist; // Store distance for texture mapping

        int wall_height = (int)(SCREEN_HEIGHT / perpWallDist);

        if (wall_height > SCREEN_HEIGHT) wall_height = SCREEN_HEIGHT;

        int draw_start  = (SCREEN_HEIGHT - wall_height) / 2;
        int draw_end    = (SCREEN_HEIGHT + wall_height) / 2;

        // printf("Wall distance: %f", perpWallDist);
        // Adjust brightness depending on distance
        float brightness = 1.0f - (perpWallDist / 10.0f);
        if (brightness < 0.0f) brightness = 0.0f;

        // Right-sided walls should has darker shade than left-sided walls
        // Check if ray has hit vertical wall
        float shade = (side == 0 ? 0.9f : 0.7f) * brightness;

        SDL_SetRenderDrawColor(renderer, 255 * shade, 255 * shade, 255 * shade, 255);
        SDL_RenderDrawLine(renderer, i, draw_start, i, draw_end);

    }
}

int comp (const void * elem1, const void * elem2) {
    double f = (*(SpriteOrder*)elem1).distance;
    double s = (*(SpriteOrder*)elem2).distance;
    if (f > s) return -1; // descending order
    if (f < s) return 1;
    return 0;
}

void render_textures(Camera* camera, SDL_Renderer* renderer, const Grid* g) {
    double* distances = calculate_sprite_distances(camera, g);

    SpriteOrder sprite_order[g->sprite_count];
    for (int i = 0; i < g->sprite_count; i++) {
        sprite_order[i].index = i;
        sprite_order[i].distance = distances[i];
    }

    qsort(sprite_order, g->sprite_count, sizeof(SpriteOrder), comp); // Sort sprites by distance from camera (farthest to closest)

    double camTileX = camera->x / g->tile_size;
    double camTileY = camera->y / g->tile_size;
    for(int i = 0; i < g->sprite_count; i++) {
        Sprite* sprite = &g->sprites[sprite_order[i].index];

        double spriteX = sprite->x - camTileX;
        double spriteY = sprite->y - camTileY;

        double dirX   = cos(camera->angle);
        double dirY   = sin(camera->angle);
        double planeX = -dirY * tan(FOV / 2);
        double planeY =  dirX * tan(FOV / 2);

        // inverse camera matrix
        double invDet = 1.0 / (planeX * dirY - dirX * planeY);

        double transformX = invDet * ( dirY * spriteX - dirX * spriteY);
        double transformY = invDet * (-planeY * spriteX + planeX * spriteY);

        if (transformY <= 0) continue;  // behind camera, skip

        // transformY is depth, transformX is horizontal offset
        int sprite_screen_x = (int)((SCREEN_WIDTH / 2) * (1 + transformX / transformY));

        int sprite_height = (int)(SCREEN_HEIGHT / transformY);
        if (sprite_height > SCREEN_HEIGHT) sprite_height = SCREEN_HEIGHT;
        int sprite_width = sprite_height / 2; // Assuming square sprites for now

        int draw_start_y = (SCREEN_HEIGHT - sprite_height) / 2;
        int draw_end_y = (SCREEN_HEIGHT + sprite_height) / 2;   
        int draw_start_x = sprite_screen_x - sprite_width / 2;
        int draw_end_x = sprite_screen_x + sprite_width / 2;

        for (int col = draw_start_x; col < draw_end_x; col++) {
            if (col < 0 || col >= SCREEN_WIDTH) continue;

            if (transformY >= z_buffer[col]) continue;

            SDL_SetRenderDrawColor(renderer, 255, 0, 0, 255); // Red color for sprites
            SDL_RenderDrawLine(renderer, col, draw_start_y, col, draw_end_y);
        }
    }

    free(distances);
}

double* calculate_sprite_distances(Camera* camera, const Grid* g) {
    double* distances = malloc(g->sprite_count * sizeof(double));
    double camTileX = camera->x / g->tile_size;
    double camTileY = camera->y / g->tile_size;
    for (int i = 0; i < g->sprite_count; i++) {
        double dx = g->sprites[i].x - camTileX;
        double dy = g->sprites[i].y - camTileY;
        distances[i] = dx*dx + dy*dy;
    }
    return distances;
}