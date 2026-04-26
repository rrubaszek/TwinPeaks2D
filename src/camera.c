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


void move(Camera* camera, Grid* g) {

    double dx = cosf(camera->angle) * camera->moveVel * MOV_SPEED;
    double nextX = camera->x + dx;

    int posX = (int)floor((nextX + (dx > 0 ? PLAYER_RADIUS : -PLAYER_RADIUS)) / g->tile_size);
    int posY = (int)(camera->y / g->tile_size);

    if (!is_wall(posX, posY, g)) {
        camera->x = nextX;
    }
    
    double dy = sinf(camera->angle) * camera->moveVel * MOV_SPEED;
    double nextY = camera->y + dy;

    posX = (int)(camera->x / g->tile_size);
    posY = (int)floor((nextY + (dy > 0 ? PLAYER_RADIUS : -PLAYER_RADIUS)) / g->tile_size);

    if (!is_wall(posX, posY, g)) {
        camera->y = nextY;
    }

    camera->angle += camera->rotationVel * ROTATION_SPEED;

    if (camera->angle < 0) {
        camera->angle += 2 * M_PI;
    }
    if (camera->angle > 2 * M_PI) {
        camera->angle -= 2 * M_PI;
    }
}


bool is_wall(int x, int y, Grid* g) {
    return (x < 0 || x >= g->w || y < 0 || y >= g->h) ? true : g->map[y][x] == 1;
}
