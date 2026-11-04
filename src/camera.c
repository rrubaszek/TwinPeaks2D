#include <math.h>

#include <map.h>
#include <camera.h>
#include <constants.h>


CameraView camera_get_view(Camera* camera, const Grid* g) {
    CameraView v;
    v.dirX = cos(camera->angle);
    v.dirY = sin(camera->angle);
    v.planeX = -v.dirY * tan(FOV / 2);
    v.planeY =  v.dirX * tan(FOV / 2);
    v.posX = camera->x / g->tile_size;
    v.posY = camera->y / g->tile_size;
    return v;
}

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


void move(Camera* camera, Game* game, double dt) {

    double dx = cos(camera->angle) * camera->moveVel * MOV_SPEED * dt;
    double nextX = camera->x + dx;

    int posX = (int)floor((nextX + (dx > 0 ? PLAYER_RADIUS : -PLAYER_RADIUS)) / game->grid->tile_size);
    int posY = (int)floor(camera->y / game->grid->tile_size);

    if (!is_wall(posX, posY, game->grid)) {
        camera->x = nextX;
    }

    bool touching_exit = is_exit(posX, posY, game->grid);

    double dy = sin(camera->angle) * camera->moveVel * MOV_SPEED * dt;
    double nextY = camera->y + dy;

    posX = (int)floor(camera->x / game->grid->tile_size);
    posY = (int)floor((nextY + (dy > 0 ? PLAYER_RADIUS : -PLAYER_RADIUS)) / game->grid->tile_size);

    if (!is_wall(posX, posY, game->grid)) {
        camera->y = nextY;
    }

    touching_exit = touching_exit || is_exit(posX, posY, game->grid);

    // One load attempt per entry onto an exit; after a failed load wait
    // until the player steps off the exit tile before trying again
    bool changed_map = false;
    if (touching_exit && !camera->on_exit) {
        changed_map = handle_exit(camera, game);
    }
    camera->on_exit = touching_exit && !changed_map;

    camera->angle += camera->rotationVel * ROTATION_SPEED * dt;

    if (camera->angle < 0) {
        camera->angle += 2 * M_PI;
    }
    if (camera->angle > 2 * M_PI) {
        camera->angle -= 2 * M_PI;
    }
}

bool handle_exit(Camera* camera, Game* game) {
    printf("handle_exit: exits=[%s][%s][%s][%s]\n",
        game->grid->exits[0], game->grid->exits[1],
        game->grid->exits[2], game->grid->exits[3]);

    char next_file[128];
    int dir = -1;

    // determine which exit to use
    if (strcmp(game->grid->exits[2], "NULL") != 0) dir = 2;
    else if (strcmp(game->grid->exits[3], "NULL") != 0) dir = 3;
    else if (strcmp(game->grid->exits[1], "NULL") != 0) dir = 1;
    else if (strcmp(game->grid->exits[0], "NULL") != 0) dir = 0;

    if (dir == -1) return false;

    snprintf(next_file, sizeof(next_file), "%s", game->grid->exits[dir]);

    printf("Loading: %s dir=%d\n", next_file, dir);

    Grid* next = read_map_from_file(next_file, game->texman);
    printf("texman count: %d\n", game->texman->count);
    printf("read_map_from_file returned: %p\n", (void*)next);
    if (!next) {
        fprintf(stderr, "Failed to load: %s\n", next_file);
        return false;
    }

    printf("Freeing old grid...\n");

    free_grid(game->grid);
    printf("Assigning new grid...\n");
    game->grid = next;

    printf("Repositioning camera...\n");
    switch (dir) {
        case 2:  // came from west, spawn on west side
            camera->x = 1.5 * game->grid->tile_size;
            camera->y = camera->y;  // preserve Y
            break;
        case 3:  // came from east, spawn on east side
            camera->x = (game->grid->w - 1.5) * game->grid->tile_size;
            camera->y = camera->y;  // preserve Y
            break;
        case 1:  // came from south, spawn on south side
            camera->x = camera->x;  // preserve X
            camera->y = (game->grid->h - 1.5) * game->grid->tile_size;
            break;
        case 0:  // came from north, spawn on north side
            camera->x = camera->x;  // preserve X
            camera->y = 1.5 * game->grid->tile_size;
            break;
    }
    printf("handle_exit complete\n");
    return true;
}


bool is_wall(int x, int y, Grid* g) {
    Tile* t = get_tile(g, x, y);
    if (!t) return true;  // out of bounds blocks movement
    return is_tile_solid(t);
}


bool is_exit(int x, int y, Grid* g) {
    Tile* t = get_tile(g, x, y);
    if (!t) return false;
    return t->type == TILE_EXIT;
}