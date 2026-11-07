#ifdef PROFILE

#include <stdio.h>

#include <profiler.h>
#include <timer.h>

#define PROF_FRAMES 300

static const char* names[PROF_COUNT] = {
    "clear_framebuffer", "render_floor_ceiling", "raycaster", "render_sprites",
    "upload + present", "frame (no delay)"
};

static double start_ms[PROF_COUNT];
static double sum_ms[PROF_COUNT];
static double max_ms[PROF_COUNT];
static int frames = 0;

void prof_begin(ProfSection s) {
    start_ms[s] = timer_now_ms();
}

void prof_end(ProfSection s) {
    double dt = timer_now_ms() - start_ms[s];
    sum_ms[s] += dt;
    if (dt > max_ms[s]) max_ms[s] = dt;
}

// Prints a table every PROF_FRAMES frames and resets the stats
void prof_frame_done(void) {
    if (++frames < PROF_FRAMES) return;

    double frame_avg = sum_ms[PROF_FRAME] / frames;
    printf("| %-20s | %7s | %7s | %7s |\n", "section", "avg ms", "max ms", "% frame");
    for (int i = 0; i < PROF_COUNT; i++) {
        double avg = sum_ms[i] / frames;
        printf("| %-20s | %7.3f | %7.3f | %6.1f%% |\n",
               names[i], avg, max_ms[i], 100.0 * avg / frame_avg);
        sum_ms[i] = 0.0;
        max_ms[i] = 0.0;
    }
    printf("\n");
    fflush(stdout);
    frames = 0;
}

#else
typedef int profiler_disabled; // ISO C forbids an empty translation unit
#endif
