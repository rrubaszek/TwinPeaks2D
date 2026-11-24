#!/usr/bin/env python3
"""Generates a Douglas fir sprite (RGBA PNG with hard transparency), procedurally.

Branches are placed in 3D around the trunk in whorls; each branch rises a little, then
droops towards the tip, carries side twigs, and both are covered with short needle
strokes. Strokes are drawn back to front with a depth buffer, so front branches hide
the trunk and the back of the crown. Each needle is lit by:
  - the crown cone normal against a light from the upper left front,
  - occlusion: darker towards the trunk, under each layer and low in the crown,
  - lighter, yellower new growth at branch tips.
The image is rendered at SS x resolution and averaged down; alpha is hard (the game draws
every pixel with alpha > 0). The bottom row is what stands on the floor.

Usage (no dependencies beyond the standard library):
    python3 helpers/generate_trees.py                     # fir.png 64x64, fir_tall.png 64x192
    python3 helpers/generate_trees.py --height 128 --seed 3 --name fir_mid
    python3 helpers/generate_trees.py --preview 6         # also *_preview.png, enlarged on a sky
"""

from __future__ import annotations

import argparse
import math
import random
import struct
import zlib
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "maps" / "textures"
SS = 4                                   # supersampling factor
LIGHT = (-0.55, 0.55, 0.62)              # x right, y up, z towards the viewer

# Dark blue-green shade -> sunlit yellow-green; new growth; bark
NEEDLES = [(8, 20, 18), (13, 31, 26), (20, 44, 33), (28, 58, 39), (38, 73, 44),
           (51, 89, 49), (68, 106, 54), (92, 126, 60)]
NEW_GROWTH = (128, 152, 72)
BARK = [(34, 18, 14), (58, 31, 22), (86, 46, 30), (116, 63, 40), (146, 84, 54)]


def _unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


LIGHT = _unit(LIGHT)


def _ramp(colors, t):
    t = min(max(t, 0.0), 0.999) * (len(colors) - 1)
    i, f = int(t), t - int(t)
    a, b = colors[i], colors[i + 1]
    return tuple(a[k] + (b[k] - a[k]) * f for k in range(3))


def _mix(a, b, f):
    return tuple(a[k] + (b[k] - a[k]) * f for k in range(3))


def render_fir(w: int, h: int, seed: int) -> list[list[tuple | None]]:
    """Returns h rows of w pixels: (r, g, b) or None for transparent."""
    rnd = random.Random(seed)
    S_w, S_h = w * SS, h * SS
    col = [[None] * S_w for _ in range(S_h)]
    depth = [[-1e9] * S_w for _ in range(S_h)]

    def plot(x, y, z, c):
        xi, yi = int(x), int(y)
        if 0 <= xi < S_w and 0 <= yi < S_h and z >= depth[yi][xi]:
            depth[yi][xi] = z
            col[yi][xi] = c

    u = S_w / 64                         # 1 unit = 1 px of a 64 px wide sprite, supersampled
    cx = S_w / 2
    ground = S_h - 1
    top = 1.0 * u
    bare = (10 if h <= 64 else 7 + h * 0.06) * u   # trunk visible below the crown
    crown_bottom = ground - bare
    max_r = (23 + 3 * (h / 64 - 1)) * u

    def crown_r(y):                      # cone, slightly convex, narrow spire at the top
        t = (y - top) / (crown_bottom - top)
        return max_r * (0.06 + 0.94 * t ** 0.85)

    # Trunk: a cylinder lit from the left, with vertical bark furrows. z = 0 (the axis), so any
    # branch on the front half covers it and it shows only through gaps in the foliage.
    phases = [rnd.uniform(0, 2 * math.pi) for _ in range(4)]
    for y in range(int(top), ground + 1):
        t = (y - top) / (ground - top)
        hw = (0.8 + 2.6 * t ** 1.5) * u
        if y > ground - 3 * u:
            hw += (y - (ground - 3 * u)) * 0.5          # root flare
        for x in range(int(cx - hw), int(cx + hw) + 1):
            s = (x - cx) / hw
            if abs(s) > 1:
                continue
            nz = math.sqrt(1 - s * s)
            lam = max(0.0, s * LIGHT[0] + nz * LIGHT[2])
            groove = sum(math.sin(p + s * 8 + y * 0.015) for p in phases) / len(phases)
            v = 0.12 + 0.7 * lam + 0.2 * groove + rnd.uniform(-0.05, 0.05)
            # Inside the crown the trunk is in deep shade; it brightens just below it
            v *= 0.35 + 0.65 * min(1.0, max(0.0, (y - crown_bottom + 4 * u) / (6 * u)))
            plot(x, y, -0.01, _ramp(BARK, v))

    strokes = []                          # (z, x, y, dx, dy, length, colour)

    def needles(px, py, pz, theta, d, layer_t, along, count, length):
        """Needle tuft at 3D point (px, py, pz) of a branch at angle theta.
        d: 0 at trunk .. 1 at branch tip; layer_t: 0 top .. 1 bottom of crown;
        along: projected direction of the branch (dx, dy) in the image."""
        n = _unit((math.cos(theta), 0.5, math.sin(theta)))          # crown cone normal
        lam = max(0.0, sum(n[k] * LIGHT[k] for k in range(3)))
        occl = (0.12 + 0.88 * d ** 0.9) * (1.0 - 0.3 * layer_t)
        back = 0.7 + 0.3 * (math.sin(theta) + 1) / 2
        for _ in range(count):
            # Needles stick out on both sides of the twig and hang a little
            side = 1 if rnd.random() < 0.5 else -1
            dx = along[0] * 0.5 + side * (-along[1]) * 0.9 + rnd.uniform(-0.3, 0.3)
            dy = along[1] * 0.5 + side * along[0] * 0.9 + rnd.uniform(0.0, 0.6)
            ln = math.hypot(dx, dy) or 1
            dx, dy = dx / ln, dy / ln
            hang = dy                                                 # up: lit, down: shadowed
            b = (0.1 + 0.9 * lam) * occl * back * (1 - 0.45 * hang) + rnd.uniform(-0.1, 0.1)
            c = _ramp(NEEDLES, b)
            if d > 0.82 and rnd.random() < 0.55:                      # new growth at tips
                c = _mix(c, NEW_GROWTH, 0.3 + 0.4 * lam)
            strokes.append((pz + rnd.uniform(-0.5, 0.5), px, py, dx, dy,
                            length * rnd.uniform(0.6, 1.2), c))

    # Whorls from the bottom of the crown to the top; spacing shrinks near the top
    y0 = crown_bottom
    while y0 > top + 2.5 * u:
        layer_t = (y0 - top) / (crown_bottom - top)
        r = crown_r(y0)
        n_br = 5 + int(3 * layer_t)
        base = rnd.uniform(0, 2 * math.pi)
        for b in range(n_br):
            theta = base + b * 2 * math.pi / n_br + rnd.uniform(-0.35, 0.35)
            length = r * rnd.uniform(0.6, 1.15)
            rise, droop = length * 0.18, length * rnd.uniform(0.28, 0.42)
            steps = max(2, int(length / (0.45 * u)))
            prev = None
            for s in range(steps + 1):
                d = s / steps
                rad = length * d
                # Rises from the trunk, then droops; the very tip turns up a little
                by = y0 - rise * d + droop * d * d - 0.8 * u * max(0.0, d - 0.85) / 0.15
                bx, bz = cx + math.cos(theta) * rad, math.sin(theta) * rad
                if prev:
                    along = (bx - prev[0], by - prev[1])
                    ln = math.hypot(*along) or 1
                    along = (along[0] / ln, along[1] / ln)
                    size = (1.4 + 2.2 * d) * u
                    if rnd.random() < 0.25 + 0.75 * d:
                        needles(bx, by, bz, theta, d, layer_t, along, 3, size)
                    # Side twigs in the branch's horizontal plane, hanging slightly
                    if s % 3 == 0 and d > 0.35:
                        for side in (-1, 1):
                            tw_len = (1.0 + 4.0 * d * (1 - d)) * u * rnd.uniform(0.7, 1.3)
                            tx = -math.sin(theta) * side
                            tz = math.cos(theta) * side
                            for k in range(1, 4):
                                f = k / 3 * tw_len
                                needles(bx + tx * f, by + 0.25 * f, bz + tz * f, theta, d,
                                        layer_t, (tx * 0.9, 0.4), 2, size * 0.8)
                prev = (bx, by)
        y0 -= rnd.uniform(4.2, 6.0) * u * (h / 64) ** 0.35 * (0.5 + 0.5 * layer_t)

    # Leader: a short upright spire at the very top
    for i in range(int(4 * u)):
        strokes.append((0.0, cx + rnd.uniform(-0.4, 0.4) * u, top + i, rnd.uniform(-0.6, 0.6),
                        1.0, 1.2 * u, _ramp(NEEDLES, 0.55 + rnd.uniform(-0.1, 0.1))))

    strokes.sort(key=lambda st: st[0])   # back to front
    for z, x, y, dx, dy, ln, c in strokes:
        for k in range(int(ln) + 1):
            plot(x + dx * k, y + dy * k, z, c)

    # Average SS x SS blocks; a pixel is opaque when at least 45% of it is covered
    img = []
    for y in range(h):
        row = []
        for x in range(w):
            acc, cnt = [0.0, 0.0, 0.0], 0
            for sy in range(SS):
                line = col[y * SS + sy]
                for sx in range(SS):
                    c = line[x * SS + sx]
                    if c:
                        cnt += 1
                        acc[0] += c[0]; acc[1] += c[1]; acc[2] += c[2]
            row.append(tuple(int(a / cnt) for a in acc) if cnt >= 0.45 * SS * SS else None)
        img.append(row)
    return img


def write_png(path: Path, img: list[list[tuple | None]], scale: int = 1, bg=None) -> None:
    """RGBA PNG; with scale > 1 and bg, an enlarged preview on an opaque background."""
    h, w = len(img), len(img[0])
    raw = bytearray()
    for y in range(h * scale):
        raw.append(0)                                    # filter type 0
        for x in range(w * scale):
            p = img[y // scale][x // scale]
            if p:
                raw += bytes(p) + b"\xff"
            else:
                raw += bytes(bg) + b"\xff" if bg else b"\0\0\0\0"

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w * scale, h * scale,
                                                         8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--height", type=int, help="height in px (width is 64); default: both 64 and 192")
    ap.add_argument("--seed", type=int, default=7, help="random seed (another tree shape)")
    ap.add_argument("--name", help="output name without .png (default fir / fir_tall)")
    ap.add_argument("--out", type=Path, default=OUT_DIR, help="output directory")
    ap.add_argument("--preview", type=int, metavar="N", help="also write N x enlarged *_preview.png")
    args = ap.parse_args()

    jobs = [(args.height, args.name or "fir")] if args.height else [(64, "fir"), (192, "fir_tall")]
    args.out.mkdir(parents=True, exist_ok=True)
    for height, name in jobs:
        img = render_fir(64, height, args.seed)
        write_png(args.out / f"{name}.png", img)
        print(f"{args.out / name}.png  64x{height}")
        if args.preview:
            write_png(args.out / f"{name}_preview.png", img, args.preview, bg=(150, 170, 190))


if __name__ == "__main__":
    main()
