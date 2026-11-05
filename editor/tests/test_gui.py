"""GUI smoke tests: real mouse events on an offscreen window."""

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QMessageBox

from tpedit.canvas import CELL, Tool
from tpedit.main_window import MAPS_DIR, MainWindow
from tpmap.model import SpriteType, TileType
from tpmap.txt_format import load_map, validate

B = Qt.MouseButton
NO_MOD = Qt.KeyboardModifier.NoModifier


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(app, monkeypatch):
    # Never block on dialogs
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    w = MainWindow()
    w.resize(1200, 800)
    w.show()
    app.processEvents()
    w.canvas.resetTransform()   # 1 scene unit = 1 pixel, map fully visible
    w.canvas.centerOn(8 * CELL, 6 * CELL)
    app.processEvents()
    yield w
    w.dirty = False
    w.close()


def tile_pos(win, x, y, dx=0.5, dy=0.5) -> QPoint:
    return win.canvas.mapFromScene(QPointF((x + dx) * CELL, (y + dy) * CELL))


def mouse(win, kind, pos: QPoint, button=B.LeftButton, mods=NO_MOD):
    types = {"press": QEvent.Type.MouseButtonPress, "move": QEvent.Type.MouseMove,
             "release": QEvent.Type.MouseButtonRelease}
    vp = win.canvas.viewport()
    held = B.NoButton if kind == "release" else button
    ev = QMouseEvent(types[kind], QPointF(pos), QPointF(vp.mapToGlobal(pos)),
                     B.NoButton if kind == "move" else button, held, mods)
    QApplication.sendEvent(vp, ev)
    QApplication.processEvents()


def drag(win, a: QPoint, b: QPoint, button=B.LeftButton, mods=NO_MOD, steps=4):
    mouse(win, "press", a, button, mods)
    for i in range(1, steps + 1):
        mouse(win, "move", a + (b - a) * (i / steps), button, mods)
    mouse(win, "release", b, button, mods)


def test_starts_with_walled_map(win):
    assert (win.map.width, win.map.height) == (16, 12)
    assert win.map.tile(0, 0).type == TileType.WALL
    assert "untitled" in win.windowTitle()


def test_paint_stroke_and_erase(win):
    win.canvas.set_tool(Tool.PAINT, TileType.WALL)
    drag(win, tile_pos(win, 2, 3), tile_pos(win, 9, 3))   # horizontal wall, no gaps
    assert all(win.map.tile(x, 3).type == TileType.WALL for x in range(2, 10))
    assert win.dirty and win.windowTitle().startswith("untitled *")
    drag(win, tile_pos(win, 4, 3), tile_pos(win, 5, 3), button=B.RightButton)
    assert win.map.tile(4, 3).type == TileType.EMPTY
    assert win.map.tile(6, 3).type == TileType.WALL


def test_rectangle_fill(win):
    win.canvas.set_tool(Tool.PAINT, TileType.LOWWALL)
    drag(win, tile_pos(win, 2, 2), tile_pos(win, 4, 5), mods=Qt.KeyboardModifier.ShiftModifier)
    assert all(win.map.tile(x, y).type == TileType.LOWWALL
               for x in range(2, 5) for y in range(2, 6))
    assert win.map.tile(5, 2).type == TileType.EMPTY


def test_place_select_move_delete_sprite(win):
    win.canvas.set_tool(Tool.SPRITE)
    win.canvas.sprite_type = SpriteType.NPC
    mouse(win, "press", tile_pos(win, 3, 4, 0.45, 0.55))
    mouse(win, "release", tile_pos(win, 3, 4, 0.45, 0.55))
    assert len(win.map.sprites) == 1
    s = win.map.sprites[0]
    assert (s.x, s.y, s.type) == (3.5, 4.5, SpriteType.NPC)       # snapped to half tile
    assert win.sprite_panel.sprite is s                            # selected -> panel shows it

    # Edit in the panel updates the model
    win.sprite_panel.scale.setValue(0.5)
    assert s.scale == 0.5

    # Move with the select tool
    win.canvas.set_tool(Tool.SELECT)
    drag(win, tile_pos(win, 3, 4), tile_pos(win, 6, 2))
    assert (s.x, s.y) == (6.5, 2.5)
    assert win.sprite_panel.x.value() == 6.5

    # Delete via the sprite tool's right click
    win.canvas.set_tool(Tool.SPRITE)
    mouse(win, "press", tile_pos(win, 6, 2), B.RightButton)
    mouse(win, "release", tile_pos(win, 6, 2), B.RightButton)
    assert win.map.sprites == []
    assert win.sprite_panel.sprite is None


def test_resize(win):
    win.map_panel.width_spin.setValue(20)
    win.map_panel.height_spin.setValue(8)
    win.map_panel.resize_requested.emit(20, 8)
    assert (win.map.width, win.map.height) == (20, 8)
    assert win.canvas.tiles.boundingRect().width() == 20 * CELL


def test_save_and_reload(win, tmp_path):
    win.canvas.set_tool(Tool.PAINT, TileType.EXIT)
    mouse(win, "press", tile_pos(win, 15, 5))
    mouse(win, "release", tile_pos(win, 15, 5))
    win.map_panel.exit_edits[2].setText("maps/map.txt")
    win.map_panel.exit_edits[2].textEdited.emit("maps/map.txt")
    win.canvas.set_tool(Tool.SPRITE)
    mouse(win, "press", tile_pos(win, 5, 5))
    mouse(win, "release", tile_pos(win, 5, 5))
    assert any("not in texture table" in i.message for i in validate(win.map))
    win.sprite_panel.choose_texture("sprite_pie.bmp")
    assert win.map.textures == ["sprite_pie.bmp"] and win.map.sprites[0].texture_id == 0

    out = tmp_path / "m.txt"
    assert win._write(out)
    assert not win.dirty
    m = load_map(out)
    assert m == win.map
    assert m.tile(15, 5).type == TileType.EXIT and m.exits[2] == "maps/map.txt"


def test_save_blocked_by_errors(win, tmp_path, monkeypatch):
    shown = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: shown.append(a[2]))
    win.map.exits[0] = "maps/far_too_long_name.txt"
    assert not win._write(tmp_path / "bad.txt")
    assert shown and "exit 0" in shown[0]
    assert not (tmp_path / "bad.txt").exists()


def test_open_game_map(win):
    assert win.open_path(MAPS_DIR / "map.txt")
    assert win.map.exits[2] == "maps/map2.txt"
    assert win.map_panel.exit_edits[2].text() == "maps/map2.txt"
    assert win.issues.item(0).text() == "No problems found"
