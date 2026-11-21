"""Sprite pixel editor: paints RGBA sprites (PNG) at N-times zoom."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import (QColorDialog, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QGridLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton,
                               QScrollArea, QSpinBox, QToolButton, QVBoxLayout, QWidget)

TRANSPARENT = QColor(0, 0, 0, 0)
CHECKER = (QColor("#3a3a3a"), QColor("#4a4a4a"))   # shows through transparent pixels
GRID = QColor(0, 0, 0, 90)
PROJECT_ROOT = Path(__file__).resolve().parents[2]       # same as main_window.PROJECT_ROOT
SPRITE_HELPER = PROJECT_ROOT / "helpers" / "generate_sprites.py"
TEXTURES_DIR = PROJECT_ROOT / "maps" / "textures"
MAX_SPRITE_SIDE = 256
PALETTE_COLUMNS = 12


def new_image(width: int, height: int) -> QImage:
    img = QImage(width, height, QImage.Format.Format_ARGB32)
    img.fill(TRANSPARENT)
    return img


class PixelCanvas(QWidget):
    """One ARGB32 QImage shown `zoom` times bigger. LMB paints `color`, RMB erases to transparent."""
    changed = Signal()

    def __init__(self, image: QImage | None = None, zoom: int = 20, parent=None):
        super().__init__(parent)
        self.zoom = zoom
        self.color = QColor(0, 0, 0)
        self._stroke: QColor | None = None   # colour of the stroke in progress
        self._last: QPoint | None = None     # last painted pixel of the stroke
        self.set_image(image if image is not None else new_image(16, 16))

    def set_image(self, image: QImage) -> None:
        # Non-premultiplied, so colours of half-transparent pixels survive a save
        self.image = image.convertToFormat(QImage.Format.Format_ARGB32)
        self.setFixedSize(self.image.width() * self.zoom, self.image.height() * self.zoom)
        self.update()

    def pixel_at(self, pos: QPoint) -> QPoint | None:
        p = QPoint(pos.x() // self.zoom, pos.y() // self.zoom)
        return p if self.image.valid(p) else None

    def paint_line(self, a: QPoint, b: QPoint, color: QColor) -> None:
        """Pixels from a to b inclusive, so a fast drag leaves no gaps."""
        n = max(abs(b.x() - a.x()), abs(b.y() - a.y()), 1)
        for i in range(n + 1):
            x = a.x() + round((b.x() - a.x()) * i / n)
            y = a.y() + round((b.y() - a.y()) * i / n)
            self.image.setPixelColor(x, y, color)
        self.update()
        self.changed.emit()

    # ----- mouse ---------------------------------------------------------------------------
    def mousePressEvent(self, event):
        button = event.button()
        p = self.pixel_at(event.position().toPoint())
        if p is None or button not in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            return
        self._stroke = self.color if button == Qt.MouseButton.LeftButton else TRANSPARENT
        self._last = p
        self.paint_line(p, p, self._stroke)

    def mouseMoveEvent(self, event):
        p = self.pixel_at(event.position().toPoint())
        if self._stroke is None or p is None or p == self._last:
            return
        self.paint_line(self._last, p, self._stroke)
        self._last = p

    def mouseReleaseEvent(self, event):
        self._stroke = self._last = None

    # ----- drawing -------------------------------------------------------------------------
    def paintEvent(self, event):
        qp = QPainter(self)
        z, w, h = self.zoom, self.image.width(), self.image.height()
        for y in range(h):
            for x in range(w):
                qp.fillRect(x * z, y * z, z, z, CHECKER[(x + y) & 1])
        qp.drawImage(QRect(0, 0, w * z, h * z), self.image)   # no smoothing hint: hard pixels
        if z >= 6:
            qp.setPen(QPen(GRID, 1))
            for x in range(1, w):
                qp.drawLine(x * z, 0, x * z, h * z)
            for y in range(1, h):
                qp.drawLine(0, y * z, w * z, y * z)


def helper_palette() -> list[QColor]:
    """Colours of PALETTE in helpers/generate_sprites.py, [] if it can't be loaded."""
    try:
        spec = importlib.util.spec_from_file_location("generate_sprites", SPRITE_HELPER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)          # main() is behind __name__ == "__main__"
        return [QColor(*rgb) for rgb in mod.PALETTE.values()]
    except (OSError, ImportError, AttributeError):
        return []


def image_colors(img: QImage) -> list[QColor]:
    """Opaque-ish colours used in the image, in order of first appearance."""
    seen: dict[int, QColor] = {}
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            if c.alpha() > 0:
                seen.setdefault(c.rgba(), c)
    return list(seen.values())


def color_button(c: QColor, size: int = 20) -> QToolButton:
    b = QToolButton()
    b.setFixedSize(size, size)
    b.setStyleSheet(f"background-color: {c.name(QColor.NameFormat.HexArgb)}; border: 1px solid #111;")
    b.setToolTip(f"{c.red()}, {c.green()}, {c.blue()}, a={c.alpha()}")
    return b


class NewImageDialog(QDialog):
    def __init__(self, width: int = 16, height: int = 16, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New sprite")
        form = QFormLayout(self)
        self.w, self.h = QSpinBox(), QSpinBox()
        for spin, v in ((self.w, width), (self.h, height)):
            spin.setRange(1, MAX_SPRITE_SIDE)
            spin.setValue(v)
        form.addRow("Width (px)", self.w)
        form.addRow("Height (px)", self.h)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)

    def image_size(self) -> tuple[int, int]:   # not size(): that is QWidget.size
        return self.w.value(), self.h.value()


class PixelEditorDialog(QDialog):
    """Pixel editor window: palette, zoomed canvas, PNG files."""
    saved = Signal(Path)   # P3: editor refreshes texture lists and caches

    def __init__(self, parent=None, textures_dir: Path = TEXTURES_DIR):
        super().__init__(parent)
        self.textures_dir = textures_dir
        self.path: Path | None = None
        self.dirty = False
        self.canvas = PixelCanvas()
        self.canvas.changed.connect(self._mark_dirty)
        self._custom: list[QColor] = []        # colours picked with "Custom..."
        self._base = helper_palette()

        self.current = QLabel()
        self.current.setFixedSize(32, 32)
        custom = QPushButton("Custom…")
        custom.setAutoDefault(False)           # Enter in a QDialog would "click" it
        custom.clicked.connect(self.pick_custom)
        top = QHBoxLayout()
        top.addWidget(QLabel("Colour"))
        top.addWidget(self.current)
        top.addWidget(custom)
        top.addStretch()

        self.palette_box = QWidget()
        self.palette_grid = QGridLayout(self.palette_box)
        self.palette_grid.setSpacing(2)

        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)

        files = QHBoxLayout()
        for text, slot in (("New…", self.new_image), ("Open…", self.open_dialog),
                           ("Save", self.save), ("Save as…", self.save_as)):
            b = QPushButton(text)
            b.setAutoDefault(False)
            b.clicked.connect(slot)
            files.addWidget(b)
        files.addStretch()

        lay = QVBoxLayout(self)
        lay.addLayout(files)
        lay.addLayout(top)
        lay.addWidget(self.palette_box)
        lay.addWidget(scroll, 1)
        self.resize(560, 640)

        self.refresh_palette()
        self.set_color(self._base[0] if self._base else QColor(0, 0, 0))
        self._update_title()

    def palette_colors(self) -> list[QColor]:
        """Helper palette, then custom picks, then image colours; no duplicates."""
        out: dict[int, QColor] = {}
        for c in self._base + self._custom + image_colors(self.canvas.image):
            out.setdefault(c.rgba(), c)
        return list(out.values())

    def refresh_palette(self) -> None:
        while (item := self.palette_grid.takeAt(0)) is not None:
            item.widget().deleteLater()
        for i, c in enumerate(self.palette_colors()):
            b = color_button(c)
            b.clicked.connect(lambda _=False, c=c: self.set_color(c))
            self.palette_grid.addWidget(b, i // PALETTE_COLUMNS, i % PALETTE_COLUMNS)

    def set_color(self, c: QColor) -> None:
        self.canvas.color = QColor(c)
        self.current.setStyleSheet(f"background-color: {c.name(QColor.NameFormat.HexArgb)};"
                                   " border: 1px solid #111;")

    def pick_custom(self) -> None:
        c = QColorDialog.getColor(self.canvas.color, self, "Sprite colour",
                                  QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if c.isValid():
            self._custom.append(c)
            self.refresh_palette()
            self.set_color(c)

    # ----- files ---------------------------------------------------------------------------
    def _mark_dirty(self) -> None:
        if not self.dirty:
            self.dirty = True
            self._update_title()

    def _update_title(self) -> None:
        name = self.path.name if self.path else "untitled"
        self.setWindowTitle(f"Sprite pixel editor — {name}{' *' if self.dirty else ''}")

    def maybe_discard(self) -> bool:
        if not self.dirty:
            return True
        return QMessageBox.question(self, "Unsaved sprite", "Discard changes to the sprite?") \
            == QMessageBox.StandardButton.Yes

    def load_image(self, img: QImage, path: Path | None) -> None:
        self.canvas.set_image(img)
        self.path, self.dirty = path, False
        self.refresh_palette()
        self._update_title()

    def new_image(self) -> None:
        if not self.maybe_discard():
            return
        dlg = NewImageDialog(self.canvas.image.width(), self.canvas.image.height(), self)
        if dlg.exec():
            self.load_image(new_image(*dlg.image_size()), None)

    def open_dialog(self) -> None:
        if not self.maybe_discard():
            return
        fn, _ = QFileDialog.getOpenFileName(self, "Open sprite", str(self.textures_dir), "PNG (*.png)")
        if fn:
            self.open_path(Path(fn))

    def open_path(self, path: Path) -> bool:
        img = QImage(str(path))
        if img.isNull():
            QMessageBox.warning(self, "Open sprite", f"Cannot read {path}")
            return False
        self.load_image(img, path)
        return True

    def save(self) -> bool:
        return self._write(self.path) if self.path else self.save_as()

    def save_as(self) -> bool:
        start = self.path or self.textures_dir / "sprite_new.png"
        fn, _ = QFileDialog.getSaveFileName(self, "Save sprite", str(start), "PNG (*.png)")
        if not fn:
            return False
        p = Path(fn)
        if p.suffix.lower() != ".png":
            p = p.with_name(p.name + ".png")   # not with_suffix: "sprite.v2" keeps its name
        return self._write(p)

    def _write(self, path: Path) -> bool:
        if not self.canvas.image.save(str(path), "PNG"):
            QMessageBox.warning(self, "Save sprite", f"Cannot write {path}")
            return False
        self.path, self.dirty = path, False
        self._update_title()
        self.saved.emit(path)
        return True

    def reject(self) -> None:                  # Esc and the window's close button both end here
        if self.maybe_discard():
            super().reject()
