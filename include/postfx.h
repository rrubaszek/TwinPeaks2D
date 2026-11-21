#ifndef POSTFX_H
#define POSTFX_H

#include <SDL2/SDL.h>
#include <stdbool.h>

// Retro post-process on the finished framebuffer (F1): pixelation (blocks of `pixel` x `pixel`
// screen pixels), fewer colour levels per channel, ordered 4x4 Bayer dithering.
typedef struct {
    bool enabled;
    int pixel;    // block size in screen pixels, 1 = full resolution
    int levels;   // colour levels per channel, 2..256 (256 = no quantisation)
} PostFx;

void postfx_init(PostFx* fx);                    // defaults from constants.h
void postfx_set_levels(PostFx* fx, int levels);  // rebuilds the dither lookup table
void postfx_apply(const PostFx* fx);             // in place on framebuffer; no-op if disabled
bool postfx_handle_key(PostFx* fx, SDL_Keycode key);  // true if the key was a post-fx key

#endif // POSTFX_H
