#ifndef SPRITE_H
#define SPRITE_H

typedef struct {
    double x, y;
    int texture_id;
} Sprite;

typedef struct {
    int index;
    double distance;
} SpriteOrder;

#endif // SPRITE_H