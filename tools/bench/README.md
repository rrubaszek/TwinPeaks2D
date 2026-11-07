# Headless bench

Renders fixed camera poses with the game's renderer, without a window (no SDL video, no Mesa).
Used for: byte-identical before/after checks, per-function timing, callgrind, sanitizers.
Mirrors the frame order of `src/game.c` (`frame()` in `bench.c`) — keep them in sync.

## Build and run (from the repo root)
```
tools/bench/build.sh                          # -> build/bench (-O2 -g)
build/bench png /tmp/frames                   # each pose -> /tmp/frames/<pose>.png
build/bench time 500                          # ms per section (mean, min), 500 frames per pose
BENCH_MAP=tools/bench/maps/low_tables.txt build/bench png /tmp/frames
valgrind --tool=callgrind --cache-sim=yes build/bench once 0      # one frame of pose 0
tools/bench/build.sh build/bench_asan -O1 -fsanitize=address,undefined -fno-omit-frame-pointer
```
`make clean` deletes `build/`, including the bench binaries.

## Poses and test maps
Poses are in `poses[]` in `bench.c` (world pixels, radians); indexes are used by `once`.
Comments there say which map each pose was made for.

| Map | Content |
|---|---|
| `maps/map.txt` (default) | the game's start map |
| `maps/tile_textures.txt` | four walls with their own texture (forest, table entry 3) — D2 |
| `maps/sprite_z.txt` | pie on counter (2,5) with `z = 0.5`; pie on a plant "table" at the same point — D7 |
| `maps/low_tables.txt` | two adjacent 0.3 tables (5,3), (6,3) with a pie at `z = 0.3` — F5 top faces |

The test maps are copies of `maps/map.txt` from 2026-11-07 with the changes above; they use
textures from `maps/textures/`.

## Measuring a change (see `docs/perf-log.md`)
- Callgrind Ir is deterministic — use it as the main metric.
- Milliseconds: consecutive calls influence each other (~0.1 ms call-order effect seen in B2).
  For old-vs-new timing, put a copy of the old function into the bench and time both in the
  same run, alternating, in both orders (as in B1.4/M2).
- Check the image: `png` before and after into two directories, then `cmp` the files.
