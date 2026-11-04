"""Map canvas: tile grid, painting tools, sprite markers, zoom and pan."""

from __future__ import annotations

import math
from enum import Enum

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QApplication, QGraphicsEllipseItem, QGraphicsItem,
                               QGraphicsRectItem, QGraphicsScene, QGraphicsSimpleTextItem,
                               QGraphicsView, QStyle, QStyleOptionGraphicsItem)

from tpmap.model import MapData, Sprite, SpriteType, TileType

CELL = 32.0          # scene units per tile
SPRITE_SNAP = 0.5    # sprites snap to half tiles (hold Alt for free placement)
MIN_ZOOM, MAX_ZOOM = 0.1, 8.0

TILE_COLORS = {
    TileType.EMPTY: QColor("#262626"),
    TileType.WALL: QColor("#8d99ae"),
    TileType.LOWWALL: QColor("#b08968"),
    TileType.DOOR: QColor("#e9c46a"),
    TileType.EXIT: QColor("#2a9d8f"),
}
TILE_LETTERS = {TileType.DOOR: "D", TileType.EXIT: "E", TileType.LOWWALL: "L"}

SPRITE_COLORS = {
    SpriteType.STATIC: QColor("#adb5bd"),
    SpriteType.INTERACTIVE: QColor("#ffd166"),
    SpriteType.DOOR: QColor("#ef8354"),
    SpriteType.NPC: QColor("#e63946"),
}
SPRITE_LETTERS = {SpriteType.STATIC: "S", SpriteType.INTERACTIVE: "I",
                  SpriteType.DOOR: "D", SpriteType.NPC: "N"}
GRID_COLOR = QColor("#3a3a3a")


class Tool(Enum):
    SELECT = "select"
    PAINT = "paint"
    SPRITE = "sprite"


class TileLayer(QGraphicsItem):
    """All tiles in one item; repaints only the exposed area."""

    def __init__(self, map_data: MapData):
        super().__init__()
        self.map = map_data
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemUsesExtendedStyleOption)
        self._font = QFont()
        self._font.setPixelSize(int(CELL * 0.45))
        self._font.setBold(True)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.map.width * CELL, self.map.height * CELL)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        r = option.exposedRect
        x0, x1 = max(0, int(r.left() // CELL)), min(self.map.width, math.ceil(r.right() / CELL))
        y0, y1 = max(0, int(r.top() // CELL)), min(self.map.height, math.ceil(r.bottom() / CELL))

        painter.setFont(self._font)
        for y in range(y0, y1):
            for x in range(x0, x1):
                t = self.map.tile(x, y).type
                cell = QRectF(x * CELL, y * CELL, CELL, CELL)
                painter.fillRect(cell, TILE_COLORS[t])
                letter = TILE_LETTERS.get(t)
                if letter:
                    painter.setPen(QColor("#1b1b1b"))
                    painter.drawText(cell, Qt.AlignmentFlag.AlignCenter, letter)

        pen = QPen(GRID_COLOR)
        pen.setCosmetic(True)
        painter.setPen(pen)
        for x in range(x0, x1 + 1):
            painter.drawLine(QPointF(x * CELL, y0 * CELL), QPointF(x * CELL, y1 * CELL))
        for y in range(y0, y1 + 1):
            painter.drawLine(QPointF(x0 * CELL, y * CELL), QPointF(x1 * CELL, y * CELL))

    def update_tile(self, x: int, y: int) -> None:
        self.update(QRectF(x * CELL, y * CELL, CELL, CELL))

    def resized(self) -> None:
        self.prepareGeometryChange()
        self.update()


class SpriteItem(QGraphicsEllipseItem):
    """Marker for one Sprite; position is kept in sync with the model."""

    def __init__(self, sprite: Sprite, canvas: MapCanvas):
        super().__init__()
        self.sprite = sprite
        self._canvas = canvas
        self._syncing = False
        self.label = QGraphicsSimpleTextItem(self)
        font = QFont()
        font.setPixelSize(int(CELL * 0.35))
        font.setBold(True)
        self.label.setFont(font)
        self.setZValue(10)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.sync_from_model()

    def sync_from_model(self) -> None:
        self._syncing = True
        s = self.sprite
        r = max(s.collision_r, 0.2) * CELL
        self.setRect(-r, -r, 2 * r, 2 * r)
        color = SPRITE_COLORS[s.type]
        self.setBrush(QBrush(color))
        pen = QPen(color.darker(250), 0)
        self.setPen(pen)
        self.label.setText(SPRITE_LETTERS[s.type])
        b = self.label.boundingRect()
        self.label.setPos(-b.width() / 2, -b.height() / 2)
        self.setToolTip(f"{s.type.name.lower()} sprite\ntexture {s.texture_id}, scale {s.scale}, "
                        f"collision {s.collision_r}")
        self.setPos(s.x * CELL, s.y * CELL)
        self._syncing = False

    def paint(self, painter, option, widget=None):
        # Own selection marker instead of Qt's default dashed bounding box
        opt = QStyleOptionGraphicsItem(option)
        opt.state &= ~QStyle.StateFlag.State_Selected
        super().paint(painter, opt, widget)
        if self.isSelected():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor("#ffffff"), 0, Qt.PenStyle.DashLine))
            painter.drawEllipse(self.rect().adjusted(-3, -3, 3, 3))

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and not self._syncing:
            return self._canvas.constrain_sprite_pos(value)
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and not self._syncing:
            self.sprite.x = round(self.pos().x() / CELL, 4)
            self.sprite.y = round(self.pos().y() / CELL, 4)
            self._canvas.sprite_moved.emit(self.sprite)
            self._canvas.changed.emit()
        return super().itemChange(change, value)


class MapCanvas(QGraphicsView):
    changed = Signal()                 # map content modified
    sprite_selected = Signal(object)   # Sprite or None
    sprite_moved = Signal(object)      # Sprite
    hover = Signal(int, int)           # tile under cursor, (-1, -1) outside

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QColor("#121212"))
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setMouseTracking(True)
        self.scene().selectionChanged.connect(self._on_selection_changed)

        self.map: MapData | None = None
        self.tiles: TileLayer | None = None
        self.sprite_items: dict[int, SpriteItem] = {}   # id(Sprite) -> item

        self.tool = Tool.PAINT
        self.paint_type = TileType.WALL
        self.sprite_type = SpriteType.STATIC

        self._pan_from: QPointF | None = None
        self._stroke_type: TileType | None = None
        self._last_tile: tuple[int, int] | None = None
        self._rect_start: tuple[int, int] | None = None
        self._preview: QGraphicsRectItem | None = None
        self._hover_item: QGraphicsRectItem | None = None

    # ----- model ---------------------------------------------------------------------------
    def set_map(self, m: MapData) -> None:
        self.scene().clear()
        self.sprite_items.clear()
        self.map = m
        self.tiles = TileLayer(m)
        self.scene().addItem(self.tiles)
        for s in m.sprites:
            self._add_sprite_item(s)

        self._preview = QGraphicsRectItem()
        self._preview.setPen(QPen(QColor("#ffffff"), 0, Qt.PenStyle.DashLine))
        self._preview.setZValue(20)
        self._preview.hide()
        self.scene().addItem(self._preview)

        self._hover_item = QGraphicsRectItem(0, 0, CELL, CELL)
        self._hover_item.setPen(QPen(QColor("#ffffff"), 0))
        self._hover_item.setZValue(15)
        self._hover_item.hide()
        self.scene().addItem(self._hover_item)

        self._update_scene_rect()
        self.set_tool(self.tool)
        self.fit()

    def map_resized(self) -> None:
        """Call after MapData.resize. Sprites left outside stay visible; validation flags them."""
        self.tiles.resized()
        self._update_scene_rect()
        self.changed.emit()

    def _update_scene_rect(self) -> None:
        margin = 4 * CELL
        self.setSceneRect(QRectF(-margin, -margin, self.map.width * CELL + 2 * margin,
                                 self.map.height * CELL + 2 * margin))

    def _add_sprite_item(self, s: Sprite) -> SpriteItem:
        item = SpriteItem(s, self)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, self.tool == Tool.SELECT)
        self.scene().addItem(item)
        self.sprite_items[id(s)] = item
        return item

    def refresh_sprite(self, s: Sprite) -> None:
        item = self.sprite_items.get(id(s))
        if item:
            item.sync_from_model()

    def selected_sprites(self) -> list[Sprite]:
        return [i.sprite for i in self.scene().selectedItems() if isinstance(i, SpriteItem)]

    def delete_sprites(self, sprites: list[Sprite]) -> None:
        if not sprites:
            return
        ids = {id(s) for s in sprites}
        self.map.sprites[:] = [s for s in self.map.sprites if id(s) not in ids]
        for i in ids:
            item = self.sprite_items.pop(i, None)
            if item:
                self.scene().removeItem(item)
        self.changed.emit()
        self._on_selection_changed()

    def add_sprite(self, x: float, y: float) -> Sprite:
        s = Sprite(x, y, self.sprite_type, scale=0.3 if self.sprite_type == SpriteType.INTERACTIVE else 1.0)
        self.map.sprites.append(s)
        item = self._add_sprite_item(s)
        self.scene().clearSelection()
        item.setSelected(True)
        self.changed.emit()
        return s

    def constrain_sprite_pos(self, p: QPointF, free: bool | None = None) -> QPointF:
        """Snaps a scene position to the sprite grid and clamps it inside the map."""
        if free is None:
            free = bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.AltModifier)
        x, y = p.x() / CELL, p.y() / CELL
        if not free:
            x, y = round(x / SPRITE_SNAP) * SPRITE_SNAP, round(y / SPRITE_SNAP) * SPRITE_SNAP
        x = min(max(x, 0.0), float(self.map.width))
        y = min(max(y, 0.0), float(self.map.height))
        return QPointF(x * CELL, y * CELL)

    # ----- tools -----------------------------------------------------------------------------
    def set_tool(self, tool: Tool, paint_type: TileType | None = None) -> None:
        self.tool = tool
        if paint_type is not None:
            self.paint_type = paint_type
        movable = tool == Tool.SELECT
        for item in self.sprite_items.values():
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, movable)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag if movable
                         else QGraphicsView.DragMode.NoDrag)
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor if movable
                                  else Qt.CursorShape.CrossCursor)

    def tile_at(self, view_pos) -> tuple[int, int]:
        p = self.mapToScene(view_pos)
        return math.floor(p.x() / CELL), math.floor(p.y() / CELL)

    def _paint_tile(self, x: int, y: int, tile_type: TileType) -> bool:
        if self.map.set_tile(x, y, tile_type):
            self.tiles.update_tile(x, y)
            return True
        return False

    def _paint_line(self, a: tuple[int, int], b: tuple[int, int], tile_type: TileType) -> None:
        """Bresenham, so fast drags leave no gaps."""
        (x0, y0), (x1, y1) = a, b
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        changed = False
        while True:
            changed |= self._paint_tile(x0, y0, tile_type)
            if (x0, y0) == (x1, y1):
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy
        if changed:
            self.changed.emit()

    def fill_rect(self, a: tuple[int, int], b: tuple[int, int], tile_type: TileType) -> None:
        x0, x1 = sorted((a[0], b[0]))
        y0, y1 = sorted((a[1], b[1]))
        changed = False
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                changed |= self._paint_tile(x, y, tile_type)
        if changed:
            self.changed.emit()

    def _show_rect_preview(self, a: tuple[int, int], b: tuple[int, int]) -> None:
        x0, x1 = sorted((a[0], b[0]))
        y0, y1 = sorted((a[1], b[1]))
        self._preview.setRect(QRectF(x0 * CELL, y0 * CELL, (x1 - x0 + 1) * CELL, (y1 - y0 + 1) * CELL))
        color = QColor(TILE_COLORS[self._stroke_type])
        color.setAlpha(110)
        self._preview.setBrush(color)
        self._preview.show()

    # ----- view ------------------------------------------------------------------------------
    def fit(self) -> None:
        if self.map:
            self.fitInView(QRectF(0, 0, self.map.width * CELL, self.map.height * CELL).adjusted(
                -CELL, -CELL, CELL, CELL), Qt.AspectRatioMode.KeepAspectRatio)

    def zoom(self, factor: float) -> None:
        current = self.transform().m11()
        factor = min(max(current * factor, MIN_ZOOM), MAX_ZOOM) / current
        self.scale(factor, factor)

    def wheelEvent(self, event):
        self.zoom(1.15 ** (event.angleDelta().y() / 120))

    # ----- mouse -------------------------------------------------------------------------------
    def mousePressEvent(self, event):
        if self.map is None:
            return
        button = event.button()
        if button == Qt.MouseButton.MiddleButton:
            self._pan_from = event.position()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        tile = self.tile_at(event.position().toPoint())
        if self.tool == Tool.PAINT and button in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            self._stroke_type = self.paint_type if button == Qt.MouseButton.LeftButton else TileType.EMPTY
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self._rect_start = tile
                self._show_rect_preview(tile, tile)
            else:
                self._last_tile = tile
                self._paint_line(tile, tile, self._stroke_type)
            return

        if self.tool == Tool.SPRITE:
            item = self._sprite_item_at(event.position().toPoint())
            if button == Qt.MouseButton.LeftButton:
                if item:
                    self.scene().clearSelection()
                    item.setSelected(True)
                else:
                    p = self.constrain_sprite_pos(self.mapToScene(event.position().toPoint()))
                    self.add_sprite(p.x() / CELL, p.y() / CELL)
            elif button == Qt.MouseButton.RightButton and item:
                self.delete_sprites([item.sprite])
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.map is None:
            return
        if self._pan_from is not None:
            delta = event.position() - self._pan_from
            self._pan_from = event.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))
            return

        tile = self.tile_at(event.position().toPoint())
        self._update_hover(tile)
        if self._rect_start is not None:
            self._show_rect_preview(self._rect_start, tile)
            return
        if self._last_tile is not None:
            self._paint_line(self._last_tile, tile, self._stroke_type)
            self._last_tile = tile
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._pan_from is not None and event.button() == Qt.MouseButton.MiddleButton:
            self._pan_from = None
            self.set_tool(self.tool)  # restores the tool cursor
            return
        if self._rect_start is not None:
            self.fill_rect(self._rect_start, self.tile_at(event.position().toPoint()), self._stroke_type)
            self._rect_start = None
            self._preview.hide()
            return
        if self._last_tile is not None:
            self._last_tile = None
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        self._update_hover((-1, -1))
        super().leaveEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_sprites(self.selected_sprites())
            return
        super().keyPressEvent(event)

    def _sprite_item_at(self, view_pos) -> SpriteItem | None:
        for item in self.items(view_pos):
            while item is not None and not isinstance(item, SpriteItem):
                item = item.parentItem()
            if item is not None:
                return item
        return None

    def _update_hover(self, tile: tuple[int, int]) -> None:
        if self.map is None or self._hover_item is None:
            return
        x, y = tile
        inside = self.map.in_bounds(x, y)
        self._hover_item.setVisible(inside and self.tool == Tool.PAINT)
        if inside:
            self._hover_item.setPos(x * CELL, y * CELL)
            self.hover.emit(x, y)
        else:
            self.hover.emit(-1, -1)

    def _on_selection_changed(self) -> None:
        try:
            selected = self.selected_sprites()
        except RuntimeError:  # scene is being torn down
            return
        self.sprite_selected.emit(selected[0] if len(selected) == 1 else None)
