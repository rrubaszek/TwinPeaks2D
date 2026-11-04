#ifndef CAMERA_H
#define CAMERA_H

#include <SDL2/SDL.h>
#include <stdbool.h>

#include <game.h>

/*
Camera represents a player's view of the game world. Angle is the direction the camera is facing.
moveVel represents the velocity of the camera in the x and y directions, respectively.
Maybe someday there will be different speeds for walking, running etc. but for now keep 1 unit per frame.
*/

typedef struct {
    float x, y;
    float angle;
    float moveVel;
    float rotationVel;
    bool on_exit; // standing on an exit whose map failed to load - don't retry
} Camera;

typedef struct {
    double dirX, dirY;
    double planeX, planeY;
    double posX, posY; // camera position in tile space
} CameraView;

CameraView camera_get_view(Camera* camera, const Grid* g);
void handle_input(Camera* camera, const Uint8* keys);
bool handle_exit(Camera* camera, Game* game);
void move(Camera* camera, Game* game);
bool is_wall(int posX, int posY, Grid* g);
bool is_exit(int posX, int posY, Grid* g);

#endif // CAMERA_H