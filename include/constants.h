#ifndef CONSTANTS_H
#define CONSTANTS_H

// TODO: Write dependent constants as results of others, because now a lot require change if one thing changes

#define SCREEN_WIDTH 800
#define SCREEN_HEIGHT 600

#define FPS 60
#define FRAME_DELAY (1000 / FPS)

#define MOV_SPEED 300.0      // world pixels per second
#define ROTATION_SPEED 2.0   // radians per second
#define MAX_DT 0.05          // seconds; caps the step after a frame hitch

#define M_PI 3.14159265358979323846
#define FOV (M_PI / 3)   // 60 degrees in radians

#define PLAYER_RADIUS 10

#define MAX_RENDER_DISTANCE 1600

#define TEXTURE_PATH "maps/textures/"

#define MAX_TEXTURES 16

#define MAX_LOW_SEGS 8   // low walls remembered per screen column (farther ones are skipped)

#endif // CONSTANTS_H