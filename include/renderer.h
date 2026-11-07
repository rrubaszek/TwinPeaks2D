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
// Low wall (tile height < 1) crossed by a ray before it reaches a full wall
typedef struct {
    double dist_near;  // perpendicular distance where the ray enters the tile
    double dist_far;   // ...and where it leaves it (top face spans near..far)
    int side;          // face hit on entry: 0 = x side, 1 = y side
    int mapX, mapY;
} LowSeg;

// segs may be NULL; then low walls are passed through without being recorded
RaycastHit cast_ray(double posX, double posY, double rayDirX, double rayDirY, const Grid* g,
                    LowSeg* segs, int* seg_count);
void render_sprites(CameraView* view, TextureManager* tm, const Grid* g);
void render_floor_ceiling(CameraView* view, TextureManager* tm, const Grid* g);
void render_low_walls(CameraView* view, TextureManager* tm, const Grid* g);

#endif // RENDERER_H