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


void move(Camera* camera, Game* game) {

    double dx = cosf(camera->angle) * camera->moveVel * MOV_SPEED;
    double nextX = camera->x + dx;

    int posX = (int)floor((nextX + (dx > 0 ? PLAYER_RADIUS : -PLAYER_RADIUS)) / game->grid->tile_size);
    int posY = (int)floor(camera->y / game->grid->tile_size);

    if (!is_wall(posX, posY, game->grid)) {
        camera->x = nextX;
    }

    if(is_exit(posX, posY, game->grid)) {
        handle_exit(camera, game);
    }
    
    double dy = sinf(camera->angle) * camera->moveVel * MOV_SPEED;
    double nextY = camera->y + dy;

    posX = (int)floor(camera->x / game->grid->tile_size);
    posY = (int)floor((nextY + (dy > 0 ? PLAYER_RADIUS : -PLAYER_RADIUS)) / game->grid->tile_size);

    if (!is_wall(posX, posY, game->grid)) {
        camera->y = nextY;
    }

    if(is_exit(posX, posY, game->grid)) {
        handle_exit(camera, game);
    }

    camera->angle += camera->rotationVel * ROTATION_SPEED;

    if (camera->angle < 0) {
        camera->angle += 2 * M_PI;
    }
    if (camera->angle > 2 * M_PI) {
        camera->angle -= 2 * M_PI;
    }
}

void handle_exit(Camera* camera, Game* game) {
    printf("handle_exit: exits=[%s][%s][%s][%s]\n",
        game->grid->exits[0], game->grid->exits[1],
        game->grid->exits[2], game->grid->exits[3]);

    char next_file[128];
    int dir = -1;

    // determine which exit to use and copy filename safely
    if (strcmp(game->grid->exits[2], "NULL") != 0) { strncpy(next_file, game->grid->exits[2], 128); dir = 2; }
    else if (strcmp(game->grid->exits[3], "NULL") != 0) { strncpy(next_file, game->grid->exits[3], 128); dir = 3; }
    else if (strcmp(game->grid->exits[1], "NULL") != 0) { strncpy(next_file, game->grid->exits[1], 128); dir = 1; }
    else if (strcmp(game->grid->exits[0], "NULL") != 0) { strncpy(next_file, game->grid->exits[0], 128); dir = 0; }

    if (dir == -1) return;

    printf("Loading: %s dir=%d\n", next_file, dir);

    Grid* next = read_map_from_file(next_file, game->texman);
    printf("read_map_from_file returned: %p\n", (void*)next);
    if (!next) {
        printf("Failed to load: %s\n", next_file);
        return;
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