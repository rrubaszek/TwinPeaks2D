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

// TODO: Fix issue with walking into two walls if pos is 0. Implement player as circle. Add sliding on walls
void move(Camera* camera) {
    // camera->x += cosf(camera->angle) * camera->moveVel * MOV_SPEED;

    double nextX = camera->x + cosf(camera->angle) * camera->moveVel * MOV_SPEED;
    double nextY = camera->y + sinf(camera->angle) * camera->moveVel * MOV_SPEED;

    int posX = (int) (nextX/ TILE_SIZE);
    int posY = (int) (camera->y / TILE_SIZE);

    if (posX >= 0 && posX < MAP_WIDTH && posY >= 0 && posY < MAP_HEIGHT && map[posY][posX] == 0) {
        camera->x = nextX;
        // printf("Tile: %d %d | value: %d\n", posX, posY, map[posY][posX]);
    }
    
    posX = (int) (camera->x / TILE_SIZE);
    posY = (int) (nextY / TILE_SIZE);

    if (posX >= 0 && posX < MAP_WIDTH && posY >= 0 && posY < MAP_HEIGHT && map[posY][posX] == 0) {
        camera->y = nextY;
        // printf("Tile: %d %d | value: %d\n", posX, posY, map[posY][posX]);
    }

    camera->angle += camera->rotationVel * ROTATION_SPEED;

    if (camera->angle < 0) {
        camera->angle += 2 * M_PI;
    }
    if (camera->angle > 2 * M_PI) {
        camera->angle -= 2 * M_PI;
    }
}
