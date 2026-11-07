#ifndef SPRITE_H
#define SPRITE_H

#include <stdbool.h>

typedef struct {
    int index;
    double distance;   // depth along the view direction (transformY), sort key
    double transformX; // horizontal offset in camera space
    float z;           // tie-break: at equal depth the lower sprite is drawn first
} SpriteOrder;

typedef enum {
    SPRITE_STATIC = 0,  // table, plant, lamp ...
    SPRITE_INTERACTIVE = 1,  // coffee mug, pie — can be picked up / examined
    SPRITE_DOOR = 2,  // animated
    SPRITE_NPC = 3,  // future: Norma, Shelly ...
} SpriteType;

typedef struct {
    double x, y;
    SpriteType type;
    int texture_id;
    float scale; // 1.0 = person-height, 0.3 = mug
    float z; // base height in wall units: 0 = floor, 0.5 = on a 0.5 counter
    float collision_r; // radius for interaction/blocking (0 = no collision)
    bool visible; // can be toggled (picked up item disappears)
    void* state; // type-specific data (door open amount, NPC state...)
} Sprite;

#endif // SPRITE_H