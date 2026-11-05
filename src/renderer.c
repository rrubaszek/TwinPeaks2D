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

// Integer shade: mul in [0, 256], 256 = full brightness.
// R and B are scaled together in one multiply (8 free bits between them).
static inline Uint32 shade_mul(Uint32 color, Uint32 mul) {
    Uint32 rb = ((color & 0x00FF00FFu) * mul >> 8) & 0x00FF00FFu;
    Uint32 g  = ((color & 0x0000FF00u) * mul >> 8) & 0x0000FF00u;
    return (color & 0xFF000000u) | rb | g;
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

// TODO: Implement specific textures via texture manager
void raycaster(CameraView* view, TextureManager* tm, const Grid* g) {
    Texture* wall_texture = texman_get(tm, g->wall_tex_id);
    if (!wall_texture) return;

    for (int i = 0; i < SCREEN_WIDTH; i++) {

        double cameraX = 2 * i / (double)SCREEN_WIDTH - 1;
        double rayDirX = view->dirX + view->planeX * cameraX;
        double rayDirY = view->dirY + view->planeY * cameraX;

        RaycastHit hit = cast_ray(view->posX, view->posY, rayDirX, rayDirY, g);

        // Guard against division by zero when standing right at a wall
        double dist = hit.perpWallDist;
        if (dist < 1e-4) dist = 1e-4;
        z_buffer[i] = dist;

        // texture X coordinate on the wall
        double wallX = (hit.side == 0)
            ? view->posY + hit.perpWallDist * rayDirY
            : view->posX + hit.perpWallDist * rayDirX;
        wallX -= floor(wallX);

        int texX = (int)(wallX * wall_texture->width);
        if ((hit.side == 0 && rayDirX > 0) || (hit.side == 1 && rayDirY < 0))
            texX = wall_texture->width - texX - 1;

        // Full (unclipped) wall height - only the drawn range is clipped,
        // so the texture is cropped at screen edges instead of squeezed
        int line_height = (int)(SCREEN_HEIGHT / dist);
        if (line_height < 1) line_height = 1;

        int wall_top   = (SCREEN_HEIGHT - line_height) / 2;
        int draw_start = wall_top;
        int draw_end   = (SCREEN_HEIGHT + line_height) / 2;
        if (draw_start < 0) draw_start = 0;
        if (draw_end > SCREEN_HEIGHT) draw_end = SCREEN_HEIGHT;

        float shade = compute_shade(dist, hit.side == 0 ? 0.9f : 0.7f);
        Uint32 mul = (Uint32)(shade * 256.0f);   // shade in [0, 1] -> [0, 256]

        // Texture rows per screen pixel; start offset skips the off-screen part
        int tex_h = wall_texture->height;
        double step = (double)tex_h / line_height;
        double tex_pos = (draw_start - wall_top) * step;

        // Column write: one pixel per row, stride = SCREEN_WIDTH
        Uint32* dst = &framebuffer[draw_start * SCREEN_WIDTH + i];

        for (int y = draw_start; y < draw_end; y++) {
            int texY = (int)tex_pos;
            if (texY >= tex_h) texY = tex_h - 1;
            tex_pos += step;

            Uint32 color = wall_texture->pixels[texY * wall_texture->width + texX];
            *dst = shade_mul(color, mul);
            dst += SCREEN_WIDTH;
        }
    }
}

// TODO: Implement specific textures for sprites
// Draws sprites into the framebuffer, far to near, hidden behind walls via z_buffer.
void render_sprites(CameraView* view, TextureManager* tm, const Grid* g) {
    if (g->sprite_count == 0) return; // zero-length VLA is UB

    SpriteOrder sprite_order[g->sprite_count];
    for (int i = 0; i < g->sprite_count; i++) {
        double dx = g->sprites[i].x - view->posX;
        double dy = g->sprites[i].y - view->posY;
        sprite_order[i].index = i;
        sprite_order[i].distance = dx * dx + dy * dy; // squared is enough for sorting
    }
    qsort(sprite_order, g->sprite_count, sizeof(SpriteOrder), comp); // farthest first

    // Inverse camera matrix - the same for every sprite
    double invDet = 1.0 / (view->planeX * view->dirY - view->dirX * view->planeY);

    for (int i = 0; i < g->sprite_count; i++) {
        const Sprite* sprite = &g->sprites[sprite_order[i].index];
        const Texture* tex = texman_get(tm, sprite->texture_id);
        if (!tex) continue;

        double spriteX = sprite->x - view->posX;
        double spriteY = sprite->y - view->posY;

        double transformX = invDet * ( view->dirY * spriteX - view->dirX * spriteY);
        double transformY = invDet * (-view->planeY * spriteX + view->planeX * spriteY);
        if (transformY < 1e-2) continue; // behind camera or too close (int overflow below)

        // transformY is depth, transformX is horizontal offset
        int sprite_screen_x = (int)((SCREEN_WIDTH / 2) * (1 + transformX / transformY));

        // Full wall height at this depth; the sprite stands on the floor line
        double line_height = SCREEN_HEIGHT / transformY;
        int sprite_height = (int)(line_height * sprite->scale);
        int sprite_width  = (int)((double)sprite_height * tex->width / tex->height);
        if (sprite_height < 1 || sprite_width < 1) continue;

        int bottom = (int)((SCREEN_HEIGHT + line_height) / 2);
        int top    = bottom - sprite_height;
        int left   = sprite_screen_x - sprite_width / 2;

        // Only the drawn range is clipped, so the texture is cropped, not squeezed
        int draw_start_y = top < 0 ? 0 : top;
        int draw_end_y   = bottom > SCREEN_HEIGHT ? SCREEN_HEIGHT : bottom;
        int draw_start_x = left < 0 ? 0 : left;
        int draw_end_x   = left + sprite_width > SCREEN_WIDTH ? SCREEN_WIDTH : left + sprite_width;

        Uint32 mul = (Uint32)(compute_shade(transformY, 1.0f) * 256.0f);
        double step = (double)tex->height / sprite_height;
        double tex_pos_start = (draw_start_y - top) * step;

        for (int col = draw_start_x; col < draw_end_x; col++) {
            if (transformY >= z_buffer[col]) continue; // wall is closer

            int texX = (int)((double)(col - left) * tex->width / sprite_width);
            const Uint32* src = &tex->pixels[texX];
            double tex_pos = tex_pos_start;
            Uint32* dst = &framebuffer[draw_start_y * SCREEN_WIDTH + col];

            for (int y = draw_start_y; y < draw_end_y; y++) {
                int texY = (int)tex_pos;
                if (texY >= tex->height) texY = tex->height - 1;
                tex_pos += step;

                Uint32 color = src[texY * tex->width];
                if (color >> 24) *dst = shade_mul(color, mul); // alpha 0 = transparent
                dst += SCREEN_WIDTH;
            }
        }
    }
}

// TODO: Implement specific textures via texture manager
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
        Uint32 mul = (Uint32)(shade * 256.0f);   // shade in [0, 1] -> [0, 256]

        double floorStepX = rowDistance * (rayDirX1 - rayDirX0) / SCREEN_WIDTH;
        double floorStepY = rowDistance * (rayDirY1 - rayDirY0) / SCREEN_WIDTH;

        double floorX = view->posX + rowDistance * rayDirX0;
        double floorY = view->posY + rowDistance * rayDirY0;

        Texture* tex = is_floor ? floor_tex : ceiling_tex;
        Uint32* row = &framebuffer[y * SCREEN_WIDTH];   // y in [0, SCREEN_HEIGHT), no bounds check needed

        if (tex == NULL) {
            for (int x = 0; x < SCREEN_WIDTH; x++)
                row[x] = shade_mul(0xFF333333, mul);
            continue;
        }

        // Texture coords in 16.16 fixed point, wrapped to [0, size) each step
        const int32_t W = tex->width  << 16;
        const int32_t H = tex->height << 16;

        int32_t u  = (int32_t)((floorX - floor(floorX)) * W);
        int32_t v  = (int32_t)((floorY - floor(floorY)) * H);
        int32_t du = (int32_t)(floorStepX * W);   // |step| < 1 tile, one wrap suffices
        int32_t dv = (int32_t)(floorStepY * H);
        if (u >= W) u -= W;                       // guard against rounding to exactly 1.0
        if (v >= H) v -= H;

        for (int x = 0; x < SCREEN_WIDTH; x++) {
            Uint32 color = tex->pixels[(v >> 16) * tex->width + (u >> 16)];
            row[x] = shade_mul(color, mul);

            u += du; if (u >= W) u -= W; else if (u < 0) u += W;
            v += dv; if (v >= H) v -= H; else if (v < 0) v += H;
        }
    }
}