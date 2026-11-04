#include <SDL2/SDL.h>

#include <timer.h>

double timer_now_ms(void) {
    static Uint64 freq = 0;
    static Uint64 start = 0;

    if (freq == 0) {
        freq  = SDL_GetPerformanceFrequency();
        start = SDL_GetPerformanceCounter();
    }

    return (double)(SDL_GetPerformanceCounter() - start) * 1000.0 / (double)freq;
}
