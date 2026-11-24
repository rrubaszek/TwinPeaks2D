#!/usr/bin/env python3
"""Generates outdoor textures procedurally (stdlib only):

  sky.png           1024x256 panorama, wraps around 360 degrees (left edge meets right edge):
                    overcast gradient, cloud bands, hazy mountain ridges and two layers of
                    fir treeline at the bottom (the bottom row meets the horizon).
  forest_floor.png  64x64 seamless ground: moss, soil, fallen needles, cones.
  forest_edge.png   64x64 wall of the forest edge, wraps horizontally: undergrowth in the
                    colours of the forest floor at the bottom, shaded trunks, a ragged line
                    of fir tips at the top; above it the texture is transparent (sky shows).

Usage:
    python3 helpers/generate_outdoor.py               # both -> maps/textures/
    python3 helpers/generate_outdoor.py sky --seed 3  # only the sky, another variant
    python3 helpers/generate_outdoor.py edge --seed 3 --name forest_edge2   # another wall
    python3 helpers/generate_outdoor.py --preview 2   # also *_preview.png, enlarged
"""

from __future__ import annotations

import argparse
import math
import random
import sys
import struct
import zlib
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "maps" / "textures"


# --- periodic value noise -------------------------------------------------------------------

class Noise:
    """2D value noise that wraps with period (px, py) cells; fbm sums octaves."""

    def __init__(self, rnd: random.Random, px: int, py: int):
        self.px, self.py = px, py
        self.v = [[rnd.random() for _ in range(px)] for _ in range(py)]

    def at(self, x: float, y: float) -> float:
        x0, y0 = math.floor(x), math.floor(y)
        fx, fy = x - x0, y - y0
        fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        x0 %= self.px
        y0 %= self.py
        x1, y1 = (x0 + 1) % self.px, (y0 + 1) % self.py
        a = self.v[y0][x0] + (self.v[y0][x1] - self.v[y0][x0]) * fx
        b = self.v[y1][x0] + (self.v[y1][x1] - self.v[y1][x0]) * fx
        return a + (b - a) * fy


def fbm(layers: list[Noise], u: float, v: float) -> float:
    """u, v in [0, 1) of the texture; layer k has 2^k times more cells; result ~[0, 1]."""
    s, amp, tot = 0.0, 1.0, 0.0
    for n in layers:
        s += amp * n.at(u * n.px, v * n.py)
        tot += amp
        amp *= 0.5
    return s / tot


def _mix(a, b, f):
    f = min(max(f, 0.0), 1.0)
    return tuple(a[k] + (b[k] - a[k]) * f for k in range(3))


# --- sky --------------------------------------------------------------------------------------

def render_sky(w: int, h: int, seed: int) -> list[list[tuple]]:
    rnd = random.Random(seed)
    clouds = [Noise(rnd, 6 * 2 ** k, 2 * 2 ** k) for k in range(5)]
    ridge_far = [Noise(rnd, 5 * 2 ** k, 1) for k in range(4)]
    ridge_near = [Noise(rnd, 9 * 2 ** k, 1) for k in range(4)]

    zenith, horizon = (46, 56, 72), (150, 158, 166)
    cloud_lit, cloud_dark = (176, 180, 186), (78, 84, 96)
    mount_far, mount_near = (66, 78, 92), (50, 62, 72)
    trees_far, trees_near = (52, 66, 70), (22, 34, 32)

    # Ridge heights per column (rows from the bottom), both wrap around
    far = [h * (0.30 + 0.22 * fbm(ridge_far, x / w, 0.0)) for x in range(w)]
    near = [h * (0.20 + 0.16 * fbm(ridge_near, x / w, 0.5)) for x in range(w)]

    def treeline(base_rows: float, spacing: float, tall: float, phase: float) -> list[float]:
        """Jagged fir silhouettes: a spire every ~spacing px, random height, wraps around."""
        line = [base_rows] * w
        n = int(w / spacing)
        for i in range(n):
            cx = (i + rnd.uniform(-0.35, 0.35)) * w / n + phase
            ht = tall * rnd.uniform(0.45, 1.0)
            half = ht * rnd.uniform(0.22, 0.32)
            for dx in range(-int(half) - 1, int(half) + 2):
                x = int(cx + dx) % w
                top = base_rows + ht * max(0.0, 1 - abs(dx) / half)
                # little branch notches on the sides of the spire
                if abs(dx) > 1 and (int(top) + dx) % 3 == 0:
                    top -= 1.5
                line[x] = max(line[x], top)
        return line

    t_far = treeline(h * 0.07, 7.0, h * 0.13, 0.0)
    t_near = treeline(h * 0.02, 11.0, h * 0.17, 3.0)

    img = []
    for y in range(h):
        row = []
        up = (h - 1 - y)                                   # rows above the horizon
        t = y / (h - 1)                                    # 0 top .. 1 horizon
        for x in range(w):
            c = _mix(zenith, horizon, t ** 1.6)
            sky_row = c
            # Overcast: soft cloud bands, stretched horizontally, thinning towards the horizon
            n = fbm(clouds, x / w, y / h)
            cover = max(0.0, (n - 0.42) * 2.4) * (1 - 0.6 * t)
            shade = fbm(clouds, x / w + 0.37, y / h + 0.21)
            c = _mix(c, _mix(cloud_dark, cloud_lit, shade * 1.2 - 0.1), cover)
            # Mountains, then treelines; haze lightens what is farther away
            if up < far[x]:
                c = _mix(mount_far, sky_row, 0.45 - 0.25 * (up / far[x]))
            if up < near[x]:
                c = _mix(mount_near, sky_row, 0.25 - 0.15 * (up / near[x]))
            if up < t_far[x]:
                c = _mix(trees_far, sky_row, 0.2)
            if up < t_near[x]:
                c = trees_near
            c = tuple(int(min(255, max(0, v + rnd.uniform(-2, 2)))) for v in c)
            row.append(c)
        img.append(row)
    return img


# --- forest floor -----------------------------------------------------------------------------

def render_floor(w: int, h: int, seed: int) -> list[list[tuple]]:
    """Seamless: every feature wraps around both edges."""
    rnd = random.Random(seed)
    SS = 2
    W, H = w * SS, h * SS
    moss = [Noise(rnd, 4 * 2 ** k, 4 * 2 ** k) for k in range(4)]
    soil, moss_dark, moss_lit = (72, 54, 36), (44, 64, 30), (96, 118, 52)
    needle_cols = [(112, 74, 40), (138, 96, 52), (92, 60, 34), (150, 116, 70)]

    base = [[None] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            m = fbm(moss, x / W, y / H)
            fine = fbm(moss[2:], x / W + 0.5, y / H + 0.5)
            if m > 0.46:
                c = _mix(moss_dark, moss_lit, (m - 0.46) * 3 * fine + 0.25)
            else:
                c = _mix(soil, moss_dark, max(0.0, (m - 0.35) * 5))
            base[y][x] = _mix(c, (0, 0, 0), 0.15 * (1 - fine))

    def put(x, y, c):
        base[int(y) % H][int(x) % W] = c

    # Fallen needles: short strokes in random directions, more on bare soil
    for _ in range(int(W * H / 28)):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        a = rnd.uniform(0, math.pi)
        ln = rnd.uniform(2, 5)
        c = rnd.choice(needle_cols)
        c = _mix(c, (0, 0, 0), rnd.uniform(0, 0.25))
        for k in range(int(ln)):
            put(x + math.cos(a) * k, y + math.sin(a) * k, c)
    # A few cones: small dark ovals with a lit edge
    for _ in range(2):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        a = rnd.uniform(0, math.pi)
        for i in range(-7, 8):
            for j in range(-4, 5):
                if (i / 7.5) ** 2 + (j / 4.2) ** 2 <= 1:
                    px = x + i * math.cos(a) - j * math.sin(a)
                    py = y + i * math.sin(a) + j * math.cos(a)
                    lit = 0.5 + 0.5 * (-(i + j) / 8)
                    put(px, py, _mix((44, 26, 16), (128, 84, 48), lit + rnd.uniform(-0.15, 0.15)))

    img = []
    for y in range(h):
        row = []
        for x in range(w):
            acc = [0, 0, 0]
            for sy in range(SS):
                for sx in range(SS):
                    c = base[y * SS + sy][x * SS + sx]
                    for k in range(3):
                        acc[k] += c[k]
            row.append(tuple(int(a / (SS * SS)) for a in acc))
        img.append(row)
    return img


# --- forest edge wall -------------------------------------------------------------------------

def render_edge(w: int, h: int, seed: int, ground: tuple) -> list[list[tuple | None]]:
    """Forest edge built from the same Douglas firs as the tree sprites (generate_trees.py):
    dark forest interior, a hazy back row of firs, a front row, undergrowth fading into the
    ground colour in the bottom rows. Everything wraps in x. None = transparent (sky)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from generate_trees import render_fir

    rnd = random.Random(seed)
    img: list[list[tuple | None]] = [[None] * w for _ in range(h)]
    deep = (10, 18, 16)

    # Forest interior: opaque below the lowest fir tips, darker towards the ground
    interior_top = int(h * 0.38)
    for y in range(interior_top, h):
        t = (y - interior_top) / (h - interior_top)
        for x in range(w):
            img[y][x] = _mix((22, 32, 32), deep, 0.4 + 0.6 * t + rnd.uniform(-0.08, 0.08))

    def paste(tree, x0: int, top: int, haze: float, dark: float):
        for ty, row in enumerate(tree):
            y = top + ty
            if not 0 <= y < h:
                continue
            for tx, c in enumerate(row):
                if c is not None:
                    c = _mix(_mix(c, deep, dark), (64, 76, 86), haze)
                    img[y][(x0 + tx - len(row) // 2) % w] = c

    # Only the upper part of tall firs is visible: slender spires make the ragged skyline.
    # Back row: hazy and darker; front row: as the sprites, a little darker (in the shade)
    n_back, n_front = 5, 4
    for i in range(n_back):
        tree = render_fir(64, rnd.choice((128, 144, 160)), seed * 100 + i)
        paste(tree, int((i + rnd.uniform(-0.25, 0.25)) * w / n_back), int(rnd.uniform(4, 16)),
              0.3, 0.35)
    for i in range(n_front):
        tree = render_fir(64, rnd.choice((144, 160, 192)), seed * 100 + 50 + i)
        paste(tree, int((i + 0.5 + rnd.uniform(-0.25, 0.25)) * w / n_front), int(rnd.uniform(0, 10)),
              0.0, 0.15)

    # Undergrowth: ferns and young firs along the bottom, ragged top edge, fine speckle
    under = [Noise(rnd, 6 * 2 ** k, 4 * 2 ** k) for k in range(3)]
    for x in range(w):
        top = h * (0.76 + 0.12 * fbm(under, x / w, 0.3))
        for y in range(int(top), h):
            n = fbm(under, x / w, y / h)
            c = _mix((14, 28, 16), (62, 86, 40), n * 1.4 - 0.3 + rnd.uniform(-0.15, 0.15))
            img[y][x] = c

    # Below the skyline every pixel must be opaque: the game cuts only the top of a wall
    # (texture column -> first opaque row), holes lower down would show as black
    for x in range(w):
        filled = False
        for y in range(h):
            if img[y][x] is not None:
                filled = True
            elif filled:
                img[y][x] = _mix((22, 32, 32), deep, 0.4 + 0.6 * y / h)   # hazy forest interior

    # Bottom rows fade into the forest floor colour, so the wall meets the floor smoothly
    fade = int(h * 0.12)
    for y in range(h - fade, h):
        f = (y - (h - fade)) / fade
        for x in range(w):
            img[y][x] = tuple(int(v) for v in _mix(img[y][x], ground, f ** 1.5))
    return [[tuple(int(v) for v in c) if c else None for c in row] for row in img]


def average(img: list[list[tuple]]) -> tuple:
    px = [p for row in img for p in row]
    return tuple(sum(p[k] for p in px) / len(px) for k in range(3))


# --- output -----------------------------------------------------------------------------------

def write_png(path: Path, img: list[list[tuple | None]], scale: int = 1, tile: int = 1,
              tile_y: int | None = None, bg=None) -> None:
    """PNG, RGBA if any pixel is None (transparent); scale enlarges, the image repeats
    tile x tile_y times (to check seams); bg(x, y) paints transparent pixels in previews."""
    h, w = len(img), len(img[0])
    tile_y = tile if tile_y is None else tile_y
    rgba = bg is None and any(p is None for row in img for p in row)
    raw = bytearray()
    for y in range(h * tile_y * scale):
        raw.append(0)
        src = img[(y // scale) % h]
        for x in range(w * tile * scale):
            p = src[(x // scale) % w]
            if p is None:
                p = bg(x, y) if bg else (0, 0, 0)
            raw += bytes(int(c) for c in p) + (b"" if not rgba else
                                                 (b"\xff" if src[(x // scale) % w] else b"\0"))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w * tile * scale,
                                                         h * tile_y * scale, 8, 6 if rgba else 2,
                                                         0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("which", nargs="*", choices=["sky", "floor", "edge"], help="default: all")
    ap.add_argument("--seed", type=int, default=7, help="random seed (another variant)")
    ap.add_argument("--name", help="output name without .png (one texture only)")
    ap.add_argument("--out", type=Path, default=OUT_DIR, help="output directory")
    ap.add_argument("--preview", type=int, metavar="N", help="also write N x enlarged *_preview.png")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    for which in args.which or ["sky", "floor", "edge"]:
        bg, tile_y = None, None
        if which == "sky":
            name, img, tile = "sky", render_sky(1024, 256, args.seed), 1
        elif which == "floor":
            name, img, tile = "forest_floor", render_floor(64, 64, args.seed), 3
        else:
            # The ground colour is the average of the floor generated with the default seed
            ground = average(render_floor(64, 64, 7))
            name, img, tile, tile_y = "forest_edge", render_edge(64, 64, args.seed, ground), 4, 1
            sky = render_sky(1024, 256, 7)
            n = args.preview or 1
            bg = lambda x, y: sky[256 - 64 * n + y if 64 * n <= 256 else 192 + y // n][x // n]
        name = args.name or name
        write_png(args.out / f"{name}.png", img)
        print(f"{args.out / name}.png  {len(img[0])}x{len(img)}")
        if args.preview:
            write_png(args.out / f"{name}_preview.png", img, args.preview, tile, tile_y, bg)


if __name__ == "__main__":
    main()
