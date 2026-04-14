#include <camera.h>
#include <constants.h>
#include <math.h>

#define M_PI 3.14159265358979323846

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

void move(Camera* camera) {
    camera->x += cosf(camera->angle) * camera->moveVel * MOV_SPEED;

    if (camera->x < 0 || camera->x > LEVEL_WIDTH) {
        camera->x -= cosf(camera->angle) * camera->moveVel * MOV_SPEED;
    }

    camera->y += sinf(camera->angle) * camera->moveVel * MOV_SPEED;

    if (camera->y < 0 || camera->y > LEVEL_HEIGHT) {
        camera->y -= sinf(camera->angle) * camera->moveVel * MOV_SPEED;
    }

    camera->angle += camera->rotationVel * ROTATION_SPEED;

    if (camera->angle < 0) {
        camera->angle += 2 * M_PI;
    }
    if (camera->angle > 2 * M_PI) {
        camera->angle -= 2 * M_PI;
    }
}
