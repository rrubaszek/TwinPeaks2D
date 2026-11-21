"""Sprite pixel editor: paints RGBA sprites (PNG) at N-times zoom."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QWidget

TRANSPARENT = QColor(0, 0, 0, 0)
CHECKER = (QColor("#3a3a3a"), QColor("#4a4a4a"))   # shows through transparent pixels
GRID = QColor(0, 0, 0, 90)


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
