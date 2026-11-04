"""Dock panels: tool palette, map properties, sprite properties, validation issues."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRegularExpression, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QKeySequence, QPixmap, QRegularExpressionValidator
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
                               QSizePolicy, QSpinBox, QToolButton, QVBoxLayout, QWidget)

from tpmap.model import EXIT_COUNT, NO_EXIT, MapData, Sprite, SpriteType, TileType
from tpmap.txt_format import MAX_EXIT_NAME, MAX_TEXTURE_NAME, Issue

from .canvas import SPRITE_COLORS, TILE_COLORS, Tool

MAX_MAP_SIDE = 256

# Where the player appears in the next map after using exit i (src/camera.c: handle_exit)
EXIT_LABELS = ["Exit 0 (spawn N)", "Exit 1 (spawn S)", "Exit 2 (spawn W)", "Exit 3 (spawn E)"]


def swatch(color: QColor, size: int = 14) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(color)
    return QIcon(pm)


def texture_names(textures_dir: Path) -> list[str]:
    exts = {".png", ".jpg", ".jpeg", ".bmp"}
    if not textures_dir.is_dir():
        return []
    return sorted(p.name for p in textures_dir.iterdir() if p.suffix.lower() in exts)


def texture_combo(textures_dir: Path) -> QComboBox:
    combo = QComboBox()
    combo.setEditable(True)  # textures may be generated later (maps/textures is gitignored)
    combo.addItems(texture_names(textures_dir))
    combo.lineEdit().setValidator(QRegularExpressionValidator(
        QRegularExpression(rf"\S{{0,{MAX_TEXTURE_NAME}}}")))
    return combo


class ToolPanel(QWidget):
    tool_changed = Signal(object, object)    # Tool, TileType | None
    sprite_type_changed = Signal(object)     # SpriteType

    TOOLS = [  # label, shortcut, tool, tile type
        ("Select / move", "S", Tool.SELECT, None),
        ("Wall", "1", Tool.PAINT, TileType.WALL),
        ("Low wall", "2", Tool.PAINT, TileType.LOWWALL),
        ("Door", "3", Tool.PAINT, TileType.DOOR),
        ("Exit", "4", Tool.PAINT, TileType.EXIT),
        ("Empty (erase)", "0", Tool.PAINT, TileType.EMPTY),
        ("Place sprite", "P", Tool.SPRITE, None),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: list[QToolButton] = []

        for i, (label, key, tool, tile_type) in enumerate(self.TOOLS):
            b = QToolButton()
            b.setText(f"{label}   [{key}]")
            b.setCheckable(True)
            b.setShortcut(QKeySequence(key))
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            if tile_type is not None:
                b.setIcon(swatch(TILE_COLORS[tile_type]))
            self.group.addButton(b, i)
            self.buttons.append(b)
            layout.addWidget(b)

        layout.addWidget(QLabel("Sprite type:"))
        self.sprite_type = QComboBox()
        for st in SpriteType:
            self.sprite_type.addItem(swatch(SPRITE_COLORS[st]), st.name.capitalize(), st)
        layout.addWidget(self.sprite_type)

        hint = QLabel(
            "<small><b>Paint:</b> LMB draw, RMB erase, Shift+drag rectangle<br>"
            "<b>Sprite:</b> LMB place/select, RMB delete, Alt = no snap<br>"
            "<b>Select:</b> drag to move, Del to delete<br>"
            "<b>View:</b> wheel zoom, MMB drag pan, Ctrl+0 fit</small>")
        hint.setWordWrap(True)
        hint.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(hint)
        layout.addStretch()

        self.group.idToggled.connect(self._on_toggled)
        self.sprite_type.currentIndexChanged.connect(
            lambda: self.sprite_type_changed.emit(self.sprite_type.currentData()))
        self.buttons[1].setChecked(True)

    def _on_toggled(self, idx: int, checked: bool) -> None:
        if checked:
            _, _, tool, tile_type = self.TOOLS[idx]
            self.tool_changed.emit(tool, tile_type)


class MapPanel(QWidget):
    changed = Signal()
    resize_requested = Signal(int, int)

    def __init__(self, project_root: Path, textures_dir: Path, parent=None):
        super().__init__(parent)
        self.project_root = project_root
        self.map: MapData | None = None
        form = QFormLayout(self)

        self.size_label = QLabel()
        self.width_spin, self.height_spin = QSpinBox(), QSpinBox()
        for s in (self.width_spin, self.height_spin):
            s.setRange(1, MAX_MAP_SIDE)
        resize_btn = QPushButton("Resize")
        resize_btn.setToolTip("Keeps content anchored at the top-left corner")
        row = QHBoxLayout()
        row.addWidget(self.width_spin)
        row.addWidget(QLabel("×"))
        row.addWidget(self.height_spin)
        row.addWidget(resize_btn)
        form.addRow("Size (tiles)", row)

        self.tile_size = QSpinBox()
        self.tile_size.setRange(1, 1000)
        self.tile_size.setToolTip("World pixels per tile (game uses 100)")
        form.addRow("Tile size", self.tile_size)

        self.wall_tex = texture_combo(textures_dir)
        self.floor_tex = texture_combo(textures_dir)
        self.ceiling_tex = texture_combo(textures_dir)
        form.addRow("Wall texture", self.wall_tex)
        form.addRow("Floor texture", self.floor_tex)
        form.addRow("Ceiling texture", self.ceiling_tex)

        exit_validator = QRegularExpressionValidator(QRegularExpression(rf"\S{{0,{MAX_EXIT_NAME}}}"))
        self.exit_edits: list[QLineEdit] = []
        for i in range(EXIT_COUNT):
            edit = QLineEdit()
            edit.setPlaceholderText(NO_EXIT)
            edit.setValidator(exit_validator)
            edit.setToolTip(f"Map path relative to the game directory, max {MAX_EXIT_NAME} chars, "
                            "empty = NULL.\nNote: the game currently uses the first non-NULL exit "
                            "in order 2, 3, 1, 0 for every exit tile.")
            browse = QToolButton()
            browse.setText("…")
            browse.clicked.connect(lambda _=False, e=edit: self._browse_exit(e))
            r = QHBoxLayout()
            r.addWidget(edit)
            r.addWidget(browse)
            form.addRow(EXIT_LABELS[i], r)
            self.exit_edits.append(edit)
            edit.textEdited.connect(self._commit)

        resize_btn.clicked.connect(
            lambda: self.resize_requested.emit(self.width_spin.value(), self.height_spin.value()))
        self.tile_size.valueChanged.connect(self._commit)
        for combo in (self.wall_tex, self.floor_tex, self.ceiling_tex):
            combo.currentTextChanged.connect(self._commit)

    def set_map(self, m: MapData) -> None:
        self.map = None  # block _commit while filling widgets
        self.width_spin.setValue(m.width)
        self.height_spin.setValue(m.height)
        self.tile_size.setValue(m.tile_size)
        self.wall_tex.setCurrentText(m.wall_texture)
        self.floor_tex.setCurrentText(m.floor_texture)
        self.ceiling_tex.setCurrentText(m.ceiling_texture)
        for edit, value in zip(self.exit_edits, m.exits):
            edit.setText("" if value == NO_EXIT else value)
        self.map = m

    def _commit(self, *_):
        m = self.map
        if m is None:
            return
        m.tile_size = self.tile_size.value()
        m.wall_texture = self.wall_tex.currentText()
        m.floor_texture = self.floor_tex.currentText()
        m.ceiling_texture = self.ceiling_tex.currentText()
        m.exits = [e.text() or NO_EXIT for e in self.exit_edits]
        self.changed.emit()

    def _browse_exit(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Target map", str(self.project_root / "maps"),
                                              "Maps (*.txt)")
        if not path:
            return
        try:
            rel = Path(path).resolve().relative_to(self.project_root).as_posix()
        except ValueError:
            QMessageBox.warning(self, "Exit", "The map must be inside the game directory.")
            return
        if len(rel) > MAX_EXIT_NAME:
            QMessageBox.warning(self, "Exit", f"'{rel}' is longer than {MAX_EXIT_NAME} characters "
                                "(game limit: char exits[4][16]). Use a shorter file name.")
            return
        edit.setText(rel)
        self._commit()


class SpritePanel(QWidget):
    sprite_edited = Signal(object)   # Sprite

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sprite: Sprite | None = None
        form = QFormLayout(self)
        self.info = QLabel("No sprite selected")
        form.addRow(self.info)

        self.type = QComboBox()
        for st in SpriteType:
            self.type.addItem(swatch(SPRITE_COLORS[st]), st.name.capitalize(), st)
        self.x, self.y = self._dspin(0, MAX_MAP_SIDE, 0.5), self._dspin(0, MAX_MAP_SIDE, 0.5)
        self.texture_id = QSpinBox()
        self.texture_id.setRange(0, 9999)
        self.texture_id.setToolTip("Stored in the file; the game does not map it to a texture yet")
        self.scale = self._dspin(0.01, 10, 0.05)
        self.scale.setToolTip("1.0 = person height, 0.3 = mug")
        self.collision_r = self._dspin(0, 5, 0.05)
        self.collision_r.setToolTip("Radius in tiles for interaction/blocking, 0 = none")

        form.addRow("Type", self.type)
        form.addRow("X (tiles)", self.x)
        form.addRow("Y (tiles)", self.y)
        form.addRow("Texture id", self.texture_id)
        form.addRow("Scale", self.scale)
        form.addRow("Collision radius", self.collision_r)

        self.type.currentIndexChanged.connect(self._commit)
        for w in (self.x, self.y, self.scale, self.collision_r, self.texture_id):
            w.valueChanged.connect(self._commit)
        self.set_sprite(None)

    @staticmethod
    def _dspin(lo: float, hi: float, step: float) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setDecimals(3)
        s.setSingleStep(step)
        return s

    def set_sprite(self, s: Sprite | None) -> None:
        self.sprite = None  # block _commit while filling widgets
        for w in (self.type, self.x, self.y, self.texture_id, self.scale, self.collision_r):
            w.setEnabled(s is not None)
        if s is not None:
            self.info.setText("Selected sprite")
            self.type.setCurrentIndex(self.type.findData(s.type))
            self.x.setValue(s.x)
            self.y.setValue(s.y)
            self.texture_id.setValue(s.texture_id)
            self.scale.setValue(s.scale)
            self.collision_r.setValue(s.collision_r)
        else:
            self.info.setText("No sprite selected")
        self.sprite = s

    def _commit(self, *_):
        s = self.sprite
        if s is None:
            return
        s.type = self.type.currentData()
        s.x, s.y = self.x.value(), self.y.value()
        s.texture_id = self.texture_id.value()
        s.scale = self.scale.value()
        s.collision_r = self.collision_r.value()
        self.sprite_edited.emit(s)


class IssuesPanel(QListWidget):
    """Live result of tpmap.txt_format.validate."""

    def show_issues(self, issues: list[Issue]) -> None:
        self.clear()
        if not issues:
            item = QListWidgetItem("No problems found")
            item.setForeground(QColor("#2a9d8f"))
            self.addItem(item)
            return
        for issue in sorted(issues, key=lambda i: not i.error):
            item = QListWidgetItem(str(issue))
            item.setForeground(QColor("#e63946" if issue.error else "#e9c46a"))
            self.addItem(item)


class NewMapDialog(QDialog):
    def __init__(self, textures_dir: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New map")
        form = QFormLayout(self)
        self.width_spin, self.height_spin = QSpinBox(), QSpinBox()
        for s, v in ((self.width_spin, 16), (self.height_spin, 12)):
            s.setRange(3, MAX_MAP_SIDE)
            s.setValue(v)
        self.tile_size = QSpinBox()
        self.tile_size.setRange(1, 1000)
        self.tile_size.setValue(100)
        self.wall_tex = texture_combo(textures_dir)
        self.floor_tex = texture_combo(textures_dir)
        self.ceiling_tex = texture_combo(textures_dir)
        self.wall_tex.setCurrentText("drapes.jpeg")
        self.floor_tex.setCurrentText("floor.png")
        self.ceiling_tex.setCurrentText("floor.png")
        self.walled = QCheckBox("Surround with walls")
        self.walled.setChecked(True)

        form.addRow("Width (tiles)", self.width_spin)
        form.addRow("Height (tiles)", self.height_spin)
        form.addRow("Tile size", self.tile_size)
        form.addRow("Wall texture", self.wall_tex)
        form.addRow("Floor texture", self.floor_tex)
        form.addRow("Ceiling texture", self.ceiling_tex)
        form.addRow(self.walled)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def create_map(self) -> MapData:
        return MapData.new(self.width_spin.value(), self.height_spin.value(), self.tile_size.value(),
                           self.wall_tex.currentText(), self.floor_tex.currentText(),
                           self.ceiling_tex.currentText(), walled=self.walled.isChecked())
