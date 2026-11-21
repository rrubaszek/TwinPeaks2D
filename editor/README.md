# TwinPeaks2D map editor

PySide6 editor for `maps/*.txt`, in the exact format `read_map_from_file` (`src/map.c`) reads.
Format description: `docs/map-format.md`.

## Setup and run
```
python3 -m venv .venv
.venv/bin/pip install -r editor/requirements.txt
.venv/bin/python editor/run_editor.py               # new map
.venv/bin/python editor/run_editor.py maps/map.txt  # open a map
```
Tests (offscreen, no window): `.venv/bin/python -m pytest editor/tests`

## Controls
| Tool | Mouse |
|---|---|
| Wall / Low wall / Door / Exit / Empty (`1` `2` `3` `4` `0`) | LMB paint, RMB erase, Shift+drag rectangle |
| Floor / Ceiling texture (`5` `6`) | LMB paint the chosen texture, RMB back to the map default, Shift+drag rectangle; the tile type is not changed |
| Place sprite (`P`) | LMB place (snaps to ½ tile, Alt = free) or select, RMB delete |
| Select / move (`S`) | drag sprites, rubber-band select, Del deletes |
| View | wheel zoom, middle-drag pan, Ctrl+0 fit |
| Sprite pixel editor (Tools menu, or **Edit…** in the Sprite panel) | LMB paint, RMB transparent, drag draws a line |

**Floor / ceiling texture** (Tools panel): texture for the Floor / Ceiling tools. While one of
them is active, the grid shows that layer's textures; otherwise small blue marks show tiles with
their own floor (bottom-left) or ceiling (top-right). Painting a wall keeps the tile's floor/ceiling.

**Wall texture** (Tools panel): texture for painted walls / low walls. `(map default)` = the map's
wall texture; another file is added to the map's texture table on first paint. Tiles with their
own texture show a thumbnail on the grid; the status bar shows the texture under the cursor.

The **Map** panel edits size, tile size, default textures and the 4 exits; the **Sprite** panel
edits the selected sprite, including its **Height (z)** — base height in wall units. A sprite
placed on a low wall gets the wall's height automatically; **On tile top** sets it again after
moving; **On sprite below** sets it to the top of the highest sprite within 0.25 tiles (transparent
top rows of its texture are not counted, e.g. a pie on a stool). A click on an existing sprite
selects it, so stacks are built by dragging one sprite onto another. **Problems** shows live validation: errors (the game would reject the
map) block saving, warnings ask for confirmation.

## Sprite pixel editor
Paints RGBA PNG sprites at 20× zoom (checkerboard = transparent). The palette is `PALETTE` from
`helpers/generate_sprites.py` + **Custom…** colours (with alpha) + colours already in the image.
New (up to 256 × 256), Open, Save / Save as (default `maps/textures/sprite_<name>.png`). A file saved
into `maps/textures/` appears in the texture lists at once; tile thumbnails and sprite heights use
the new version. Bottom row of the image = what stands on the floor in the game.

## Format limits enforced (from the C code)
- texture names: no spaces, max 63 chars, files from `maps/textures/`
- exits: map path relative to the game directory or `NULL`, max 15 chars (`char exits[4][16]`)
- tile types 0–4 (`TileType`), sprite types 0–3 (`SpriteType`), sprites inside the map
- tile texture 0..table size (0 = map wall texture), sprite texture = table index
- sprite inside a wall is a warning, except on a low wall with `z ≥` its height

## Code
- `tpmap/` model + file format, no GUI dependency (`model.py`, `txt_format.py`)
- `tpedit/` GUI: `canvas.py` (grid, tools), `panels.py` (docks, dialogs), `main_window.py`,
  `pixel_editor.py` (sprite pixel editor)
