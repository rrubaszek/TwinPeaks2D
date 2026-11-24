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

// F1 retro post-process (postfx.c); at runtime: F2 on/off, F3 block size, F4 colour depth
#define POSTFX_ENABLED 1   // on at start
#define POSTFX_PIXEL 2     // pixel block size in screen pixels (2 -> 400x300 look)
#define POSTFX_LEVELS 32   // colour levels per channel (32 = 15-bit colour, as on PS1)

// D5.3 wind sway of sprites with wind > 0 (renderer.c)
#define WIND_AMPLITUDE 0.05      // max top shift, as a fraction of sprite width (wind = 1)
#define WIND_GUST_SPEED 0.8      // rad/s of the travelling gust waves
#define WIND_GUST_K 0.6          // rad/tile; gusts move at SPEED/K ~ 1.3 tiles/s
#define WIND_FLUTTER_SPEED 3.0   // rad/s of the fast per-sprite flutter

#endif // CONSTANTS_H