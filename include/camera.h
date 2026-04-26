#ifndef CAMERA_H
#define CAMERA_H

#include <SDL2/SDL.h>
#include <stdbool.h>

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
} Camera;

void handle_input(Camera* camera, const Uint8* keys);
void move(Camera* camera, Grid* g);
bool is_wall(int posX, int posY, Grid* g);

#endif // CAMERA_H