#ifndef RENDERER_H
#define RENDERER_H  

#include <map.h>
#include <camera.h>
#include <constants.h>
#include <texture.h>
#include <texturemanager.h>

extern double z_buffer[SCREEN_WIDTH]; // Store distance to walls for each column for texture mapping

typedef struct {
    int mapX, mapY;
    int side;
    double perpWallDist;
    double rayDirX, rayDirY; // kept for wallX calculation afterward
} RaycastHit;


void draw_camera(Camera* camera, SDL_Renderer* renderer);
void draw_map(SDL_Renderer* renderer, const Grid* g);
void raycaster(CameraView* view, TextureManager* tm, const Grid* g);
Uint32 apply_shade(Uint32 color, float shade);
float compute_shade(double distance, float side_factor);
RaycastHit cast_ray(double posX, double posY, double rayDirX, double rayDirY, const Grid* g);
void render_sprites(Camera* camera, SDL_Renderer* renderer, const Grid* g);
void render_floor_ceiling(CameraView* view, TextureManager* tm, const Grid* g);
double* calculate_sprite_distances(Camera* camera, const Grid* g);
int comp (const void * elem1, const void * elem2);

#endif // RENDERER_H