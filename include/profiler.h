#ifndef PROFILER_H
#define PROFILER_H

typedef enum {
    PROF_CLEAR,
    PROF_FLOOR,
    PROF_WALLS,
    PROF_SPRITES,
    PROF_PRESENT,
    PROF_FRAME,
    PROF_COUNT
} ProfSection;

#ifdef PROFILE
void prof_begin(ProfSection s);
void prof_end(ProfSection s);
void prof_frame_done(void);
#else
#define prof_begin(s)     ((void)0)
#define prof_end(s)       ((void)0)
#define prof_frame_done() ((void)0)
#endif

#endif // PROFILER_H
