"""Main editor window: menus, docks, file handling."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QDockWidget, QFileDialog, QLabel, QMainWindow, QMessageBox,
                               QScrollArea)

from tpmap.model import MapData
from tpmap.txt_format import MapFormatError, format_map, load_map, validate

from .canvas import MapCanvas
from .panels import IssuesPanel, MapPanel, NewMapDialog, SpritePanel, ToolPanel

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAPS_DIR = PROJECT_ROOT / "maps"
TEXTURES_DIR = MAPS_DIR / "textures"


class MainWindow(QMainWindow):
    def __init__(self, path: str | None = None):
        super().__init__()
        self.path: Path | None = None
        self.dirty = False
        self.map: MapData | None = None

        self.canvas = MapCanvas()
        self.setCentralWidget(self.canvas)

        self.tools = ToolPanel()
        self.map_panel = MapPanel(PROJECT_ROOT, TEXTURES_DIR)
        self.sprite_panel = SpritePanel()
        self.issues = IssuesPanel()
        self._dock("Tools", self.tools, Qt.DockWidgetArea.LeftDockWidgetArea)
        self._dock("Map", self.map_panel, Qt.DockWidgetArea.RightDockWidgetArea)
        self._dock("Sprite", self.sprite_panel, Qt.DockWidgetArea.RightDockWidgetArea)
        problems = self._dock("Problems", self.issues, Qt.DockWidgetArea.BottomDockWidgetArea)

        self.status = QLabel()
        self.statusBar().addWidget(self.status)

        # Validation is debounced: painting a stroke triggers many changes
        self._validate_timer = QTimer(self, singleShot=True, interval=250)
        self._validate_timer.timeout.connect(self._run_validation)

        self._create_menus()
        self._connect()

        settings = QSettings("TwinPeaks2D", "MapEditor")
        if geometry := settings.value("geometry"):
            self.restoreGeometry(geometry)
        if state := settings.value("state"):
            self.restoreState(state)
        if not geometry:
            self.resize(1400, 900)
        if not state:
            self.resizeDocks([problems], [110], Qt.Orientation.Vertical)

        if path:
            self.open_path(Path(path))
        if self.map is None:
            self.set_map(MapData.new(16, 12), None)

    def _dock(self, title: str, widget, area) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setObjectName(title)
        if not isinstance(widget, IssuesPanel):
            scroll = QScrollArea()
            scroll.setWidget(widget)
            scroll.setWidgetResizable(True)
            widget = scroll
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        return dock

    def _create_menus(self) -> None:
        def action(menu, text, slot, shortcut=None):
            a = QAction(text, self)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            a.triggered.connect(slot)
            menu.addAction(a)
            return a

        file_menu = self.menuBar().addMenu("&File")
        action(file_menu, "&New…", self.new_map, QKeySequence.StandardKey.New)
        action(file_menu, "&Open…", self.open_dialog, QKeySequence.StandardKey.Open)
        file_menu.addSeparator()
        action(file_menu, "&Save", self.save, QKeySequence.StandardKey.Save)
        action(file_menu, "Save &As…", self.save_as, QKeySequence.StandardKey.SaveAs)
        file_menu.addSeparator()
        action(file_menu, "&Quit", self.close, QKeySequence.StandardKey.Quit)

        edit_menu = self.menuBar().addMenu("&Edit")
        action(edit_menu, "Delete selected sprites",
               lambda: self.canvas.delete_sprites(self.canvas.selected_sprites()),
               QKeySequence.StandardKey.Delete)

        view_menu = self.menuBar().addMenu("&View")
        action(view_menu, "Zoom in", lambda: self.canvas.zoom(1.25), QKeySequence.StandardKey.ZoomIn)
        action(view_menu, "Zoom out", lambda: self.canvas.zoom(0.8), QKeySequence.StandardKey.ZoomOut)
        action(view_menu, "Fit map", self.canvas.fit, "Ctrl+0")
        view_menu.addSeparator()
        for dock in self.findChildren(QDockWidget):
            view_menu.addAction(dock.toggleViewAction())

    def _connect(self) -> None:
        self.tools.tool_changed.connect(self.canvas.set_tool)
        self.tools.sprite_type_changed.connect(lambda st: setattr(self.canvas, "sprite_type", st))
        self.canvas.changed.connect(self._mark_dirty)
        self.canvas.hover.connect(self._show_hover)
        self.canvas.sprite_selected.connect(self.sprite_panel.set_sprite)
        self.canvas.sprite_moved.connect(self._sprite_moved)
        self.sprite_panel.sprite_edited.connect(self._sprite_edited)
        self.map_panel.changed.connect(self._mark_dirty)
        self.map_panel.resize_requested.connect(self._resize_map)

    # ----- state ---------------------------------------------------------------------------
    def set_map(self, m: MapData, path: Path | None) -> None:
        self.map = m
        self.path = path
        self.canvas.set_map(m)
        self.map_panel.set_map(m)
        self.sprite_panel.set_sprite(None)
        self.dirty = False
        self._update_title()
        self._run_validation()

    def _mark_dirty(self) -> None:
        if not self.dirty:
            self.dirty = True
            self._update_title()
        self._validate_timer.start()

    def _update_title(self) -> None:
        name = self.path.name if self.path else "untitled"
        self.setWindowTitle(f"{name}{' *' if self.dirty else ''} — TwinPeaks2D Map Editor")

    def _run_validation(self) -> None:
        if self.map is not None:
            self.issues.show_issues(validate(self.map, TEXTURES_DIR))

    def _show_hover(self, x: int, y: int) -> None:
        m = self.map
        if m is None or x < 0:
            self.status.setText(f"{m.width} × {m.height} tiles, {len(m.sprites)} sprites" if m else "")
            return
        t = m.tile(x, y)
        self.status.setText(f"Tile ({x}, {y})  {t.type.name.lower()}  "
                            f"[{int(t.type)}:{t.texture_id}:{t.height}]")

    def _sprite_moved(self, s) -> None:
        if self.sprite_panel.sprite is s:
            self.sprite_panel.set_sprite(s)

    def _sprite_edited(self, s) -> None:
        self.canvas.refresh_sprite(s)
        self._mark_dirty()

    def _resize_map(self, w: int, h: int) -> None:
        m = self.map
        if (w, h) == (m.width, m.height):
            return
        if w < m.width or h < m.height:
            answer = QMessageBox.question(self, "Resize map",
                                          f"Shrinking to {w} × {h} removes tiles outside. Continue?")
            if answer != QMessageBox.StandardButton.Yes:
                self.map_panel.set_map(m)
                return
        m.resize(w, h)
        self.canvas.map_resized()

    # ----- files ---------------------------------------------------------------------------
    def maybe_discard(self) -> bool:
        """True if it's OK to drop the current map (saved, or user agreed)."""
        if not self.dirty:
            return True
        answer = QMessageBox.question(
            self, "Unsaved changes", "Save changes to the current map?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel)
        if answer == QMessageBox.StandardButton.Save:
            return self.save()
        return answer == QMessageBox.StandardButton.Discard

    def new_map(self) -> None:
        if not self.maybe_discard():
            return
        dialog = NewMapDialog(TEXTURES_DIR, self)
        if dialog.exec():
            self.set_map(dialog.create_map(), None)
            self._mark_dirty()

    def open_dialog(self) -> None:
        if not self.maybe_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open map", str(MAPS_DIR), "Maps (*.txt)")
        if path:
            self.open_path(Path(path))

    def open_path(self, path: Path) -> bool:
        try:
            m = load_map(path)
        except (OSError, MapFormatError) as e:
            QMessageBox.critical(self, "Open map", f"Cannot open {path}:\n{e}")
            return False
        self.set_map(m, path)
        return True

    def save(self) -> bool:
        if self.path is None:
            return self.save_as()
        return self._write(self.path)

    def save_as(self) -> bool:
        start = str(self.path or MAPS_DIR / "new_map.txt")
        path, _ = QFileDialog.getSaveFileName(self, "Save map", start, "Maps (*.txt)")
        if not path:
            return False
        path = Path(path)
        if path.suffix != ".txt":
            path = path.with_suffix(".txt")
        return self._write(path)

    def _write(self, path: Path) -> bool:
        issues = validate(self.map, TEXTURES_DIR)
        errors = [str(i) for i in issues if i.error]
        warnings = [str(i) for i in issues if not i.error]
        if errors:
            QMessageBox.critical(self, "Cannot save",
                                 "The game would reject this map:\n\n" + "\n".join(errors))
            return False
        if warnings:
            answer = QMessageBox.question(self, "Save with warnings",
                                          "\n".join(warnings) + "\n\nSave anyway?")
            if answer != QMessageBox.StandardButton.Yes:
                return False
        try:
            path.write_text(format_map(self.map), encoding="utf-8")
        except OSError as e:
            QMessageBox.critical(self, "Save map", f"Cannot write {path}:\n{e}")
            return False
        self.path = path
        self.dirty = False
        self._update_title()
        self.statusBar().showMessage(f"Saved {path}", 4000)
        return True

    def closeEvent(self, event) -> None:
        if not self.maybe_discard():
            event.ignore()
            return
        settings = QSettings("TwinPeaks2D", "MapEditor")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("state", self.saveState())
        event.accept()
