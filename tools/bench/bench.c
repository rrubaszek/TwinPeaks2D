// Headless bench: renders fixed camera poses without a window (no SDL video, no Mesa).
// Mirrors the frame order in src/game.c - keep them in sync.
//
//   bench time [N]     per-section ms (mean, min) over N frames per pose (default 300)
//   bench once P       one frame of pose index P (for callgrind / sanitizers)
//   bench png DIR      saves each pose as DIR/<name>.png (byte-identical before/after checks)
//
// Map: maps/map.txt, or the path in $BENCH_MAP. Run from the repo root (textures are relative).
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <SDL2/SDL.h>
#include <SDL2/SDL_image.h>
#include <map.h>
#include <camera.h>
#include <renderer.h>
#include <framebuffer.h>

typedef struct { const char* name; double x, y, a; } Pose;   // world pixels, radians
static const Pose poses[] = {
    { "start",    400, 500, 4.7 },          // game start position
    { "near",     150, 650, 3.14159265 },   // 0.5 tile from west wall: walls cover the screen
    { "open",     150, 650, 0.0 },          // looking along row 6: mostly floor/ceiling
    { "counter",  350, 690, 4.71 },         // between low-wall tiles (2,5) and (4,5)
    { "counter2", 150, 650, -0.5 },         // both low-wall tiles at an angle
    { "pie",      250, 670, 4.71 },         // facing counter (2,5) from the south
    { "table",    650, 680, 4.71 },         // sprite table + pie at (6.5, 5.5) in sprite_z.txt
    { "behind",   570, 550, 3.14159265 },   // plant (3.5,5.5) behind counter (4,5), from the east
    { "l3front",  550, 560, 4.71 },         // 0.3 tables (5,3),(6,3) in low_tables.txt, from the south
    { "l3angle",  350, 560, -0.75 },        // the same at an angle
    { "l3far",    550, 690, 4.71 },         // farther: pie partly behind the near edge
    { "l3close",  550, 430, 4.71 },         // close: top face reaches the screen bottom
    { "tooclose", 750, 652, 4.71 },         // 0.02 from sprite (7.5,6.5): sprite top below the screen
};
enum { NPOSES = sizeof poses / sizeof poses[0] };

static void frame(CameraView* v, TextureManager* tm, Grid* g) {
    clear_framebuffer(0x00000000);
    raycaster(v, tm, g);            // walls first: records wall spans and low walls
    render_floor_ceiling(v, tm, g);
    render_low_walls(v, tm, g);
    render_sprites(v, tm, g);
}

static double now_ms(void) {
    return SDL_GetPerformanceCounter() * 1000.0 / SDL_GetPerformanceFrequency();
}

int main(int argc, char** argv) {
    const char* mode = argc > 1 ? argv[1] : "time";
    IMG_Init(IMG_INIT_PNG | IMG_INIT_JPG);
    TextureManager* tm = calloc(1, sizeof *tm);
    const char* map_path = getenv("BENCH_MAP") ? getenv("BENCH_MAP") : "maps/map.txt";
    Grid* g = tm ? read_map_from_file(map_path, tm) : NULL;
    if (!g) return 1;

    for (int p = 0; p < NPOSES; p++) {
        Camera cam = { .x = poses[p].x, .y = poses[p].y, .angle = poses[p].a };
        CameraView v = camera_get_view(&cam, g);

        if (!strcmp(mode, "once")) {
            if (argc > 2 && p == atoi(argv[2])) frame(&v, tm, g);
        } else if (!strcmp(mode, "png")) {
            frame(&v, tm, g);
            SDL_Surface* s = SDL_CreateRGBSurfaceWithFormatFrom(framebuffer, SCREEN_WIDTH,
                SCREEN_HEIGHT, 32, SCREEN_WIDTH * 4, SDL_PIXELFORMAT_ARGB8888);
            char path[512];
            snprintf(path, sizeof path, "%s/%s.png", argc > 2 ? argv[2] : ".", poses[p].name);
            if (!s || IMG_SavePNG(s, path)) fprintf(stderr, "save %s: %s\n", path, SDL_GetError());
            SDL_FreeSurface(s);
        } else {
            int frames = argc > 2 ? atoi(argv[2]) : 300;
            if (frames < 1) frames = 1;
            const char* names[] = { "clear", "raycaster", "floor_ceiling", "low_walls", "sprites" };
            enum { NSEC = sizeof names / sizeof names[0] };
            double sum[NSEC] = {0}, mn[NSEC];
            for (int k = 0; k < NSEC; k++) mn[k] = 1e9;
            for (int f = 0; f < frames; f++) {
                double t[NSEC + 1];
                t[0] = now_ms(); clear_framebuffer(0);
                t[1] = now_ms(); raycaster(&v, tm, g);
                t[2] = now_ms(); render_floor_ceiling(&v, tm, g);
                t[3] = now_ms(); render_low_walls(&v, tm, g);
                t[4] = now_ms(); render_sprites(&v, tm, g);
                t[5] = now_ms();
                for (int k = 0; k < NSEC; k++) {
                    double d = t[k + 1] - t[k];
                    sum[k] += d;
                    if (d < mn[k]) mn[k] = d;
                }
            }
            for (int k = 0; k < NSEC; k++)
                printf("%-9s %-14s mean %.3f  min %.3f ms\n",
                       poses[p].name, names[k], sum[k] / frames, mn[k]);
        }
    }
    free_grid(g);
    texman_free(tm);
    free(tm);
    IMG_Quit();
    return 0;
}
