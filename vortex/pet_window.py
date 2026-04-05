import time
from collections import deque

from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QColor, QBrush, QMouseEvent
from PyQt6.QtWidgets import QWidget, QApplication, QMenu

from vortex.config import SPRITE_SIZE, FLOOR_OFFSET


class PetWindow(QWidget):
    """Frameless, transparent overlay widget that renders the desktop pet."""

    # Signals
    petted = pyqtSignal()
    double_clicked = pyqtSignal()
    drag_started = pyqtSignal()
    drag_released = pyqtSignal(float, float)  # vx, vy in px/sec
    position_changed = pyqtSignal(int, int)

    # Ring buffer size for velocity tracking
    _VELOCITY_SAMPLES = 5

    def __init__(self, parent=None):
        super().__init__(parent)

        # Window setup: frameless, always-on-top, tool (no taskbar entry), transparent
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(SPRITE_SIZE, SPRITE_SIZE)

        # Current sprite pixmap (None = draw placeholder)
        self._pixmap: QPixmap | None = None

        # Drag state
        self._drag_offset: QPoint | None = None
        self._dragging = False
        self._drag_history: deque = deque(maxlen=self._VELOCITY_SAMPLES)

        # Position at bottom-right of available screen area
        self._place_initial()

    # ------------------------------------------------------------------ #
    # Placement
    # ------------------------------------------------------------------ #

    def _place_initial(self):
        """Position the pet at bottom-right of the primary screen, above the taskbar."""
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        x = geo.right() - SPRITE_SIZE - 20
        y = geo.bottom() - SPRITE_SIZE - FLOOR_OFFSET
        self.move(x, y)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def set_pixmap(self, pixmap: QPixmap):
        """Set the current sprite frame and refresh the widget."""
        self._pixmap = pixmap
        self._update_mask()
        self.update()

    def move_to(self, x: int, y: int):
        """Move the window and emit position_changed."""
        self.move(x, y)
        self.position_changed.emit(x, y)

    # ------------------------------------------------------------------ #
    # Painting
    # ------------------------------------------------------------------ #

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._pixmap and not self._pixmap.isNull():
            painter.drawPixmap(0, 0, self._pixmap)
        else:
            # Pink placeholder circle
            painter.setBrush(QBrush(QColor(255, 105, 180)))
            painter.setPen(Qt.PenStyle.NoPen)
            margin = 8
            painter.drawEllipse(
                margin, margin,
                SPRITE_SIZE - 2 * margin,
                SPRITE_SIZE - 2 * margin,
            )

        painter.end()

    # ------------------------------------------------------------------ #
    # Mask (click-through transparent areas)
    # ------------------------------------------------------------------ #

    def _update_mask(self):
        """Set window mask from pixmap alpha so transparent areas are click-through."""
        if self._pixmap and not self._pixmap.isNull():
            self.setMask(self._pixmap.mask())
        else:
            self.clearMask()

    # ------------------------------------------------------------------ #
    # Mouse interaction (drag + pet)
    # ------------------------------------------------------------------ #

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.position().toPoint()
            self._dragging = False
            self._drag_history.clear()
            self._drag_history.append((event.globalPosition().toPoint(), time.monotonic()))

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_offset is not None:
            if not self._dragging:
                self._dragging = True
                self.drag_started.emit()

            new_pos = event.globalPosition().toPoint() - self._drag_offset
            self.move(new_pos)
            self.position_changed.emit(new_pos.x(), new_pos.y())

            # Record for velocity calculation
            self._drag_history.append((event.globalPosition().toPoint(), time.monotonic()))

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._dragging:
                # Calculate release velocity from ring buffer
                vx, vy = self._compute_velocity()
                self.drag_released.emit(vx, vy)
            else:
                # Click without drag = pet
                self.petted.emit()

            self._drag_offset = None
            self._dragging = False

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()

    def _compute_velocity(self) -> tuple[float, float]:
        """Compute velocity in pixels/second from the drag history ring buffer."""
        if len(self._drag_history) < 2:
            return 0.0, 0.0

        newest_pos, newest_t = self._drag_history[-1]
        oldest_pos, oldest_t = self._drag_history[0]

        dt = newest_t - oldest_t
        if dt < 1e-6:
            return 0.0, 0.0

        dx = newest_pos.x() - oldest_pos.x()
        dy = newest_pos.y() - oldest_pos.y()

        return dx / dt, dy / dt

    # ------------------------------------------------------------------ #
    # Context menu
    # ------------------------------------------------------------------ #

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(QApplication.quit)
        menu.exec(event.globalPos())
