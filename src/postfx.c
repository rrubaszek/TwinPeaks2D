#include <stdio.h>
#include <string.h>

#include <postfx.h>
#include <constants.h>
#include <framebuffer.h>

// 4x4 Bayer matrix, values 0..15
static const int bayer4[16] = {
     0,  8,  2, 10,
    12,  4, 14,  6,
     3, 11,  1,  9,
    15,  7, 13,  5,
};

// lut[cell][v] = channel value v quantised to fx->levels with the dither offset of Bayer cell
static Uint8 lut[16][256];

void postfx_set_levels(PostFx* fx, int levels) {
    if (levels < 2) levels = 2;
    if (levels > 256) levels = 256;
    fx->levels = levels;

    double step = 255.0 / (levels - 1);
    for (int cell = 0; cell < 16; cell++) {
        double offset = (bayer4[cell] + 0.5) / 16.0 - 0.5;   // -0.47..0.47 of one level
        for (int v = 0; v < 256; v++) {
            int q = (int)(v / step + offset + 0.5);            // nearest level after the offset
            if (q < 0) q = 0;
            if (q > levels - 1) q = levels - 1;
            lut[cell][v] = (Uint8)(q * step + 0.5);
        }
    }
}

void postfx_init(PostFx* fx) {
    fx->enabled = POSTFX_ENABLED;
    fx->pixel = POSTFX_PIXEL;
    postfx_set_levels(fx, POSTFX_LEVELS);
}

// Each block takes the colour of its centre pixel, quantised with the Bayer cell of the block,
// so the dither pattern is as coarse as the pixels. The first row of a block row is written
// pixel by pixel, the other rows are copies of it.
void postfx_apply(const PostFx* fx) {
    if (!fx->enabled) return;
    const int p = fx->pixel < 1 ? 1 : fx->pixel;

    for (int by = 0, cy = 0; by < SCREEN_HEIGHT; by += p, cy++) {
        int rows = by + p <= SCREEN_HEIGHT ? p : SCREEN_HEIGHT - by;
        Uint32* row = &framebuffer[by * SCREEN_WIDTH];
        // Centre row is read before any of the block's rows is overwritten (only row `by` is)
        const Uint32* src = &framebuffer[(by + rows / 2) * SCREEN_WIDTH];
        const Uint8 (*cells)[256] = &lut[(cy & 3) * 4];

        for (int bx = 0, cx = 0; bx < SCREEN_WIDTH; bx += p, cx++) {
            int cols = bx + p <= SCREEN_WIDTH ? p : SCREEN_WIDTH - bx;
            Uint32 c = src[bx + cols / 2];
            const Uint8* l = cells[cx & 3];
            Uint32 out = (c & 0xFF000000u)
                       | (Uint32)l[(c >> 16) & 0xFF] << 16
                       | (Uint32)l[(c >> 8) & 0xFF] << 8
                       | (Uint32)l[c & 0xFF];
            for (int x = bx; x < bx + cols; x++) row[x] = out;
        }
        for (int r = 1; r < rows; r++) {
            memcpy(row + r * SCREEN_WIDTH, row, SCREEN_WIDTH * sizeof(Uint32));
        }
    }
}

static void print_state(const PostFx* fx) {
    printf("post-fx %s: pixel %d, %d levels per channel\n",
           fx->enabled ? "on" : "off", fx->pixel, fx->levels);
}

// F2 on/off, F3 next block size (1..4), F4 next colour depth (256, 32, 16, 8, 4)
bool postfx_handle_key(PostFx* fx, SDL_Keycode key) {
    static const int level_steps[] = { 256, 32, 16, 8, 4 };
    enum { NSTEPS = sizeof level_steps / sizeof level_steps[0] };

    switch (key) {
        case SDLK_F2:
            fx->enabled = !fx->enabled;
            break;
        case SDLK_F3:
            fx->pixel = fx->pixel % 4 + 1;
            break;
        case SDLK_F4: {
            int i = 0;
            while (i < NSTEPS && level_steps[i] != fx->levels) i++;
            postfx_set_levels(fx, level_steps[(i + 1) % NSTEPS]);  // unknown value -> 256
            break;
        }
        default:
            return false;
    }
    print_state(fx);
    return true;
}
