#include <framebuffer.h>

Uint32 framebuffer[SCREEN_WIDTH * SCREEN_HEIGHT];

void clear_framebuffer(Uint32 color) {
    for (int i = 0; i < SCREEN_WIDTH * SCREEN_HEIGHT; i++) {
        framebuffer[i] = color;
    }
}


void put_pixel(int x, int y, Uint32 color) {
    if (x < 0 || x >= SCREEN_WIDTH || y < 0 || y >= SCREEN_HEIGHT) {
        return;
    }
    framebuffer[y * SCREEN_WIDTH + x] = color;
}