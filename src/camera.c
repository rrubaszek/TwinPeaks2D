#include <math.h>

#include <map.h>
#include <camera.h>
#include <constants.h>


void handle_input(Camera* camera, const Uint8* keys) {
    camera->moveVel     = 0;
    camera->rotationVel = 0;

    if (keys[SDL_SCANCODE_UP]) {
        camera->moveVel = 1;
    }
    if (keys[SDL_SCANCODE_DOWN]) {
        camera->moveVel = -1;
    }
    if (keys[SDL_SCANCODE_LEFT]) {
        camera->rotationVel = -1;
    }
    if (keys[SDL_SCANCODE_RIGHT]) {
        camera->rotationVel = 1;
    }
}


void move(Camera* camera, Game* game) {

    double dx = cosf(camera->angle) * camera->moveVel * MOV_SPEED;
    double nextX = camera->x + dx;

    int posX = (int)floor((nextX + (dx > 0 ? PLAYER_RADIUS : -PLAYER_RADIUS)) / game->grid->tile_size);
    int posY = (int)(camera->y / game->grid->tile_size);

    if (!is_wall(posX, posY, game->grid)) {
        camera->x = nextX;
    }

    if(is_exit(posX, posY, game->grid)) {
        handle_exit(camera, game, posX, posY);
    }
    
    double dy = sinf(camera->angle) * camera->moveVel * MOV_SPEED;
    double nextY = camera->y + dy;

    posX = (int)(camera->x / game->grid->tile_size);
    posY = (int)floor((nextY + (dy > 0 ? PLAYER_RADIUS : -PLAYER_RADIUS)) / game->grid->tile_size);

    if (!is_wall(posX, posY, game->grid)) {
        camera->y = nextY;
    }

    if(is_exit(posX, posY, game->grid)) {
        handle_exit(camera, game, posX, posY);
    }

    camera->angle += camera->rotationVel * ROTATION_SPEED;

    if (camera->angle < 0) {
        camera->angle += 2 * M_PI;
    }
    if (camera->angle > 2 * M_PI) {
        camera->angle -= 2 * M_PI;
    }
}

// TODO: Fix placing a player on new map
void handle_exit(Camera* camera, Game* game, int x, int y) {
    if (strcmp(game->grid->exits[2], "NULL") != 0) {
        Grid* next = read_map_from_file(game->grid->exits[2]);
        free_grid(game->grid);
        game->grid = next;
        camera->x = (game->grid->w + 1) * game->grid->tile_size;
    } else if (strcmp(game->grid->exits[3], "NULL") != 0) {
        Grid* next = read_map_from_file(game->grid->exits[3]);
        free_grid(game->grid);
        game->grid = next;
        camera->x = (game->grid->w - 1) * game->grid->tile_size;
    } else if (strcmp(game->grid->exits[1], "NULL") != 0) {
        Grid* next = read_map_from_file(game->grid->exits[1]);
        free_grid(game->grid);
        game->grid = next;
        camera->y = (game->grid->h + 1) * game->grid->tile_size;
    } else if (strcmp(game->grid->exits[0], "NULL") != 0) {
        Grid* next = read_map_from_file(game->grid->exits[0]);
        free_grid(game->grid);
        game->grid = next;
        camera->y = (game->grid->h - 1) * game->grid->tile_size;
    }
}


bool is_wall(int x, int y, Grid* g) {
    return (x < 0 || x >= g->w || y < 0 || y >= g->h) ? true : g->map[y][x] == 1;
}


bool is_exit(int x, int y, Grid* g) {
    return (x < 0 || x >= g->w || y < 0 || y >= g->h) ? false : g->map[y][x] == 2;
}