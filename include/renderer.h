#ifndef RENDERER_H
#define RENDERER_H  

#include <map.h>
#include <camera.h>
#include <constants.h>
#include <texture.h>

extern double z_buffer[SCREEN_WIDTH]; // Store distance to walls for each column for texture mapping

void draw_camera(Camera* camera, SDL_Renderer* renderer);
void draw_map(SDL_Renderer* renderer, const Grid* g);
void raycaster(Camera* camera, Texture* wall_texture, const Grid* g);
void render_sprites(Camera* camera, SDL_Renderer* renderer, const Grid* g);
void render_floor_ceiling(Camera* camera, Texture* floor_tex, Texture* ceiling_tex, const Grid* g);
double* calculate_sprite_distances(Camera* camera, const Grid* g);
int comp (const void * elem1, const void * elem2);

#endif // RENDERER_H