#ifndef RENDERER_H
#define RENDERER_H  

#include <camera.h>

void draw_camera(Camera* camera, SDL_Renderer* renderer);
void draw_map(SDL_Renderer* renderer);

#endif // RENDERER_H