#!/bin/sh
# Builds the headless bench against the current src/ (no window, no game.c).
# usage: tools/bench/build.sh [out] [extra cflags...]     default out: build/bench
# e.g.   tools/bench/build.sh build/bench_asan -O1 -fsanitize=address,undefined -fno-omit-frame-pointer
set -e
R=$(cd "$(dirname "$0")/../.." && pwd)
OUT=${1:-$R/build/bench}
[ $# -gt 0 ] && shift
mkdir -p "$(dirname "$OUT")"
clang -O2 -g -std=c11 -Wall -Wextra -Wpedantic -I"$R/include" $(sdl2-config --cflags) "$@" \
  "$R/tools/bench/bench.c" "$R/src/renderer.c" "$R/src/framebuffer.c" "$R/src/map.c" \
  "$R/src/texture.c" "$R/src/texturemanager.c" "$R/src/camera.c" \
  -o "$OUT" $(sdl2-config --libs) $(pkg-config --libs SDL2_image) -lm
