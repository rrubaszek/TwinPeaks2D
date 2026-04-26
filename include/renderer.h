#ifndef RENDERER_H
#define RENDERER_H  

#include <map.h>
#include <camera.h>
#include <constants.h>

void draw_camera(Camera* camera, SDL_Renderer* renderer);
void draw_map(SDL_Renderer* renderer, const Grid* g);
void raycaster(Camera* camera, SDL_Renderer* renderer, const Grid* g);

#endif // RENDERER_H