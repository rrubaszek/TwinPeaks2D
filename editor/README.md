# TwinPeaks2D map editor

PySide6 editor for `maps/*.txt`, in the exact format `read_map_from_file` (`src/map.c`) reads.

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
| Place sprite (`P`) | LMB place (snaps to ½ tile, Alt = free) or select, RMB delete |
| Select / move (`S`) | drag sprites, rubber-band select, Del deletes |
| View | wheel zoom, middle-drag pan, Ctrl+0 fit |

The **Map** panel edits size, tile size, default textures and the 4 exits; the **Sprite** panel
edits the selected sprite. **Problems** shows live validation: errors (the game would reject the
map) block saving, warnings ask for confirmation.

## Format limits enforced (from the C code)
- texture names: no spaces, max 63 chars, files from `maps/textures/`
- exits: map path relative to the game directory or `NULL`, max 15 chars (`char exits[4][16]`)
- tile types 0–4 (`TileType`), sprite types 0–3 (`SpriteType`), sprites inside the map

## Code
- `tpmap/` model + file format, no GUI dependency (`model.py`, `txt_format.py`)
- `tpedit/` GUI: `canvas.py` (grid, tools), `panels.py` (docks, dialogs), `main_window.py`
