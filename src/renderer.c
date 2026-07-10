#include <SDL2/SDL.h>
#include <math.h>

#include <renderer.h>
#include <framebuffer.h>

// TODO: Add shading and textures

double z_buffer[SCREEN_WIDTH]; // Store distance to walls for each column for texture mapping

float compute_shade(double distance, float side_factor) {
    float brightness = 1.0f - (float)(distance / 10.0);
    if (brightness < 0.0f) brightness = 0.0f;
    return side_factor * brightness;
}

int comp (const void * elem1, const void * elem2) {
    double f = (*(SpriteOrder*)elem1).distance;
    double s = (*(SpriteOrder*)elem2).distance;
    if (f > s) return -1; // descending order
    if (f < s) return 1;
    return 0;
}

Uint32 apply_shade(Uint32 color, float shade) {
    Uint8 a = (color >> 24) & 0xFF;
    Uint8 r = (Uint8)(((color >> 16) & 0xFF) * shade);
    Uint8 g = (Uint8)(((color >> 8)  & 0xFF) * shade);
    Uint8 b = (Uint8)((color & 0xFF) * shade);
    return (a << 24) | (r << 16) | (g << 8) | b;
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
    for (int row = 0; row < g->h; row++) {
        for (int col = 0; col < g->w; col++) {
            Tile* t = get_tile(g, col, row);
            if (t && is_tile_solid(t)) {
                SDL_Rect wall = { col * g->tile_size, row * g->tile_size, g->tile_size, g->tile_size };
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

RaycastHit cast_ray(double posX, double posY, double rayDirX, double rayDirY, const Grid* g) {
    RaycastHit result;
    result.rayDirX = rayDirX;
    result.rayDirY = rayDirY;

    int mapX = (int)posX;
    int mapY = (int)posY;

    double deltaDistX = (rayDirX == 0) ? 1e30 : fabs(1 / rayDirX);
    double deltaDistY = (rayDirY == 0) ? 1e30 : fabs(1 / rayDirY);

    double sideDistX, sideDistY;
    int stepX, stepY;
    int side = 0;
    int hit = 0;

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

    while (!hit) {
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
        Tile* t = get_tile(g, mapX, mapY);
        if (t && is_tile_solid(t)) {
            hit = 1;
        }
    }

    result.mapX = mapX;
    result.mapY = mapY;
    result.side = side;
    result.perpWallDist = (side == 0) ? (sideDistX - deltaDistX) : (sideDistY - deltaDistY);

    return result;
}

void raycaster(CameraView* view, TextureManager* tm, const Grid* g) {
    Texture* wall_texture = texman_get(tm, g->wall_tex_id);

    for (int i = 0; i < SCREEN_WIDTH; i++) {

        double cameraX = 2 * i / (double)SCREEN_WIDTH - 1;
        double rayDirX = view->dirX + view->planeX * cameraX;
        double rayDirY = view->dirY + view->planeY * cameraX;

        RaycastHit hit = cast_ray(view->posX, view->posY, rayDirX, rayDirY, g);
        z_buffer[i] = hit.perpWallDist;

        // texture X coordinate on the wall
        double wallX = (hit.side == 0)
            ? view->posY + hit.perpWallDist * rayDirY
            : view->posX + hit.perpWallDist * rayDirX;
        wallX -= floor(wallX);

        int texX = (int)(wallX * wall_texture->width);
        if ((hit.side == 0 && rayDirX > 0) || (hit.side == 1 && rayDirY < 0))
            texX = wall_texture->width - texX - 1;

        int wall_height = (int)(SCREEN_HEIGHT / hit.perpWallDist);
        if (wall_height > SCREEN_HEIGHT) wall_height = SCREEN_HEIGHT;

        int draw_start = (SCREEN_HEIGHT - wall_height) / 2;
        int draw_end   = (SCREEN_HEIGHT + wall_height) / 2;

        float shade = compute_shade(hit.perpWallDist, hit.side == 0 ? 0.9f : 0.7f);

        for (int y = draw_start; y < draw_end; y++) {
            int d = y * 256 - SCREEN_HEIGHT * 128 + wall_height * 128;
            int texY = ((d * wall_texture->height) / wall_height) / 256;

            Uint32 color = wall_texture->pixels[texY * wall_texture->width + texX];
            put_pixel(i, y, apply_shade(color, shade));
        }
    }
}

void render_sprites(Camera* camera, SDL_Renderer* renderer, const Grid* g) {
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

void render_floor_ceiling(CameraView* view, TextureManager* tm, const Grid* g) {
    Texture* floor_tex = texman_get(tm, g->floor_tex_id);
    Texture* ceiling_tex = texman_get(tm, g->ceiling_tex_id);

    double rayDirX0 = view->dirX - view->planeX;
    double rayDirY0 = view->dirY - view->planeY;
    double rayDirX1 = view->dirX + view->planeX;
    double rayDirY1 = view->dirY + view->planeY;

    for (int y = 0; y < SCREEN_HEIGHT; y++) {

        bool is_floor = y > SCREEN_HEIGHT / 2;
        int p = is_floor ? (y - SCREEN_HEIGHT / 2) : (SCREEN_HEIGHT / 2 - y);
        if (p == 0) continue;

        double rowDistance = (SCREEN_HEIGHT / 2.0) / p;

        float shade = compute_shade(rowDistance, is_floor ? 1.0f : 0.85f);

        double floorStepX = rowDistance * (rayDirX1 - rayDirX0) / SCREEN_WIDTH;
        double floorStepY = rowDistance * (rayDirY1 - rayDirY0) / SCREEN_WIDTH;

        double floorX = view->posX + rowDistance * rayDirX0;
        double floorY = view->posY + rowDistance * rayDirY0;

        Texture* tex = is_floor ? floor_tex : ceiling_tex;

        for (int x = 0; x < SCREEN_WIDTH; x++) {

            if (tex == NULL) {
                put_pixel(x, y, apply_shade(0xFF333333, shade));
                floorX += floorStepX;
                floorY += floorStepY;
                continue;
            }

            int cellX = (int)floor(floorX);
            int cellY = (int)floor(floorY);

            double fracX = floorX - cellX;
            double fracY = floorY - cellY;

            int texX = (int)(fracX * tex->width)  % tex->width;
            int texY = (int)(fracY * tex->height) % tex->height;

            Uint32 color = tex->pixels[texY * tex->width + texX];

            put_pixel(x, y, apply_shade(color, shade));

            floorX += floorStepX;
            floorY += floorStepY;
        }
    }
}