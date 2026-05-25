#ifndef FRAMEBUFFER_H
#define FRAMEBUFFER_H

#include <SDL2/SDL.h>
#include <constants.h>

extern Uint32 framebuffer[SCREEN_WIDTH * SCREEN_HEIGHT];

void clear_framebuffer(Uint32 color);
void put_pixel(int x, int y, Uint32 color);

#endif // FRAMEBUFFER_H