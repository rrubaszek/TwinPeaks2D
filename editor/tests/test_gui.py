"""GUI smoke tests: real mouse events on an offscreen window."""

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QMouseEvent
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from tpedit.canvas import CELL, Tool, sprite_below_top
from tpedit.main_window import MAPS_DIR, MainWindow
from tpmap.model import MapData, Sprite, SpriteType, TileType
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


def test_paint_wall_with_texture(win):
    win.tools.wall_texture.addItem("forest.jpeg", "forest.jpeg")   # textures dir may be empty
    win.tools.wall_texture.setCurrentIndex(win.tools.wall_texture.findData("forest.jpeg"))
    assert win.canvas.paint_texture == "forest.jpeg"
    assert "forest.jpeg" not in win.map.textures                   # joins the table on paint
    win.canvas.set_tool(Tool.PAINT, TileType.WALL)
    drag(win, tile_pos(win, 2, 3), tile_pos(win, 4, 3))
    idx = win.map.textures.index("forest.jpeg")
    assert all(win.map.tile(x, 3).texture_id == idx + 1 for x in range(2, 5))

    drag(win, tile_pos(win, 3, 3), tile_pos(win, 3, 3), button=B.RightButton)   # erase
    assert win.map.tile(3, 3).texture_id == 0

    win.tools.wall_texture.setCurrentIndex(0)                       # (map default)
    assert win.canvas.paint_texture is None
    drag(win, tile_pos(win, 2, 3), tile_pos(win, 2, 3))
    assert win.map.tile(2, 3).texture_id == 0


def test_sprite_on_counter_gets_z(win):
    win.canvas.set_tool(Tool.PAINT, TileType.LOWWALL)
    drag(win, tile_pos(win, 3, 4), tile_pos(win, 3, 4))
    win.canvas.set_tool(Tool.SPRITE)
    mouse(win, "press", tile_pos(win, 3, 4))
    mouse(win, "release", tile_pos(win, 3, 4))
    s = win.map.sprites[-1]
    assert (s.x, s.y, s.z) == (3.5, 4.5, 0.5)                     # placed on the counter
    assert win.sprite_panel.z.value() == 0.5

    win.sprite_panel.z.setValue(0.2)                               # field edits the model
    assert s.z == 0.2
    win.sprite_panel.on_tile_top.click()                           # button snaps back to the top
    assert s.z == 0.5


def test_sprite_below_top():
    m = MapData.new(8, 8)
    table = Sprite(2.5, 2.5, scale=0.5)
    pie = Sprite(2.5, 2.5, scale=0.3)
    far = Sprite(4.5, 2.5, scale=2.0)            # not under the pie
    m.sprites += [table, pie, far]
    assert sprite_below_top(m, pie) == 0.5
    table.z = 0.5                                # table on a 0.5 counter
    assert sprite_below_top(m, pie) == 1.0
    assert sprite_below_top(m, far) == 0.0


def test_on_sprite_below_button(win):
    # A click on an existing sprite selects it, so the stack is built via add_sprite
    table = win.canvas.add_sprite(5.5, 5.5)
    table.scale = 0.5
    pie = win.canvas.add_sprite(5.5, 5.5)                # selected -> shown in the panel
    assert win.sprite_panel.sprite is pie
    win.sprite_panel.on_sprite_below.click()
    assert pie.z == 0.5
    assert win.sprite_panel.z.value() == 0.5


def test_sprite_below_top_skips_transparent_rows(app, tmp_path):
    from PySide6.QtGui import QColor, QImage
    img = QImage(8, 4, QImage.Format.Format_ARGB32)
    img.fill(QColor(200, 100, 50, 255))
    for x in range(8):                                   # top row transparent
        img.setPixelColor(x, 0, QColor(0, 0, 0, 0))
    assert img.save(str(tmp_path / "table.png"))

    m = MapData.new(8, 8)
    m.textures = ["table.png"]
    table = Sprite(2.5, 2.5, texture_id=0, scale=0.8)
    pie = Sprite(2.5, 2.5, scale=0.3)
    m.sprites += [table, pie]
    assert sprite_below_top(m, pie, tmp_path) == pytest.approx(0.6)   # 0.8 * 3/4
    assert sprite_below_top(m, pie) == pytest.approx(0.8)             # no textures_dir: full


def widget_mouse(w, kind, pos: QPoint, button=B.LeftButton):
    types = {"press": QEvent.Type.MouseButtonPress, "move": QEvent.Type.MouseMove,
             "release": QEvent.Type.MouseButtonRelease}
    ev = QMouseEvent(types[kind], QPointF(pos), QPointF(w.mapToGlobal(pos)),
                     B.NoButton if kind == "move" else button,
                     B.NoButton if kind == "release" else button, NO_MOD)
    QApplication.sendEvent(w, ev)


def test_pixel_canvas_paint_erase_line(app):
    from tpedit.pixel_editor import PixelCanvas
    c = PixelCanvas(zoom=10)
    c.color = QColor(200, 30, 40)
    at = lambda x, y: QPoint(x * 10 + 5, y * 10 + 5)
    widget_mouse(c, "press", at(0, 0))
    widget_mouse(c, "move", at(5, 0))                     # one jump of 5 pixels
    widget_mouse(c, "release", at(5, 0))
    assert all(c.image.pixelColor(x, 0) == QColor(200, 30, 40) for x in range(6))
    widget_mouse(c, "press", at(3, 0), B.RightButton)
    widget_mouse(c, "release", at(3, 0), B.RightButton)
    assert c.image.pixelColor(3, 0).alpha() == 0
    assert c.image.pixelColor(0, 1).alpha() == 0          # untouched pixel stays transparent


def test_pixel_editor_palette(app):
    from tpedit.pixel_editor import PixelEditorDialog, helper_palette
    base = helper_palette()
    assert len(base) == 17                                # PALETTE in helpers/generate_sprites.py
    unique = len({c.rgba() for c in base})                # 'c' and 'B' share (90, 50, 25)
    d = PixelEditorDialog()
    assert d.palette_grid.count() == unique               # empty image adds nothing
    d.palette_grid.itemAt(4).widget().click()
    assert d.canvas.color == d.palette_colors()[4]
    d.canvas.image.setPixelColor(0, 0, QColor(1, 2, 3))   # colour not in PALETTE
    d.refresh_palette()
    assert d.palette_grid.count() == unique + 1


def test_pixel_editor_save_roundtrip(app, tmp_path, monkeypatch):
    from tpedit.pixel_editor import PixelEditorDialog
    d = PixelEditorDialog(textures_dir=tmp_path)
    d.canvas.paint_line(QPoint(1, 2), QPoint(1, 2), QColor(10, 20, 30, 128))
    assert d.dirty
    saved = []
    d.saved.connect(saved.append)
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        lambda *a, **k: (str(tmp_path / "sprite_x"), ""))   # no extension typed
    assert d.save()                                    # no path yet -> Save as
    p = tmp_path / "sprite_x.png"
    assert saved == [p] and not d.dirty

    d2 = PixelEditorDialog(textures_dir=tmp_path)
    assert d2.open_path(p)
    c = d2.canvas.image.pixelColor(1, 2)
    assert (c.red(), c.green(), c.blue(), c.alpha()) == (10, 20, 30, 128)
    assert d2.canvas.image.pixelColor(0, 0).alpha() == 0


def test_pixel_editor_from_sprite_panel(win):
    if not (MAPS_DIR / "textures" / "sprite_mug.png").exists():
        pytest.skip("textures not generated (helpers/generate_sprites.py)")
    s = win.canvas.add_sprite(2.5, 2.5)
    win.sprite_panel.choose_texture("sprite_mug.png")
    win.sprite_panel.set_sprite(s)
    win.sprite_panel.edit_texture.click()
    ed = win.pixel_editor
    assert ed is not None and ed.isVisible()
    assert ed.path == MAPS_DIR / "textures" / "sprite_mug.png"
    assert ed.canvas.image.width() == 16
    ed.dirty = False
    ed.close()


def test_texture_saved_updates_editor(win, tmp_path, monkeypatch):
    import tpedit.main_window as mw
    from tpedit.canvas import _opaque_cache
    monkeypatch.setattr(mw, "TEXTURES_DIR", tmp_path)
    _opaque_cache[tmp_path / "sprite_t.png"] = 0.5               # stale entry
    win._texture_saved(tmp_path / "sprite_t.png")
    assert not _opaque_cache
    assert win.tools.wall_texture.findData("sprite_t.png") >= 0
    assert win.sprite_panel.texture.findText("sprite_t.png") >= 0
    assert win.map_panel.floor_tex.findText("sprite_t.png") >= 0

    win._texture_saved(tmp_path / "elsewhere" / "other.png")      # outside maps/textures
    assert win.sprite_panel.texture.findText("other.png") < 0


def test_pixel_canvas_large_image_zoom(app):
    from tpedit.pixel_editor import PixelCanvas, new_image
    c = PixelCanvas(new_image(512, 512))
    assert c.zoom == 1 and c.width() == 512              # 640 // 512 = 1
    assert PixelCanvas(new_image(64, 32)).zoom == 10     # 640 // 64
    assert PixelCanvas(new_image(16, 16)).zoom == 20     # small sprites keep the max zoom
    assert not c.grab().isNull()                         # paints without the per-pixel loop


def test_image_colors_limit(app):
    from tpedit.pixel_editor import IMAGE_COLORS_TOP, image_colors, new_image
    img = new_image(20, 10)
    img.setPixelColor(5, 5, QColor(9, 9, 9))
    img.setPixelColor(0, 0, QColor(1, 2, 3, 128))
    assert [c.getRgb() for c in image_colors(img)] == [(1, 2, 3, 128), (9, 9, 9, 255)]  # first seen

    for x in range(20):                                   # 200 distinct colours, (0,0,x) most common
        for y in range(10):
            img.setPixelColor(x, y, QColor(x, y, 50))
    for x in range(IMAGE_COLORS_TOP):
        for y in range(x + 1):
            img.setPixelColor(x, y, QColor(0, 0, x))
    got = image_colors(img)
    assert len(got) == IMAGE_COLORS_TOP
    assert got[0].getRgb() == (0, 0, IMAGE_COLORS_TOP - 1, 255)          # most frequent first


def test_floor_ceiling_tools(win):
    win.canvas.plane_texture = "floor.png"
    win.canvas.set_tool(Tool.FLOOR)
    assert win.canvas.tiles.plane == "floor_tex"
    drag(win, tile_pos(win, 2, 2), tile_pos(win, 4, 2))           # LMB stroke
    idx = win.map.textures.index("floor.png") + 1
    assert [win.map.tile(x, 2).floor_tex for x in range(2, 5)] == [idx] * 3
    assert win.map.tile(2, 2).type == TileType.EMPTY                # type unchanged
    drag(win, tile_pos(win, 3, 2), tile_pos(win, 3, 2), B.RightButton)
    assert win.map.tile(3, 2).floor_tex == 0                        # RMB: map default

    win.canvas.set_tool(Tool.CEILING)
    drag(win, tile_pos(win, 2, 3), tile_pos(win, 3, 4), mods=Qt.KeyboardModifier.ShiftModifier)
    assert all(win.map.tile(x, y).ceiling_tex == idx for x in (2, 3) for y in (3, 4))
    assert win.map.tile(2, 3).floor_tex == 0

    win.canvas.set_tool(Tool.PAINT, TileType.WALL)                  # walls keep the planes
    drag(win, tile_pos(win, 2, 3), tile_pos(win, 2, 3))
    assert (win.map.tile(2, 3).type, win.map.tile(2, 3).ceiling_tex) == (TileType.WALL, idx)
    assert win.canvas.tiles.plane is None
