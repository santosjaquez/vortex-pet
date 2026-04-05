"""Mini chat window for the Vortex desktop pet."""

from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QLabel,
    QScrollArea,
    QFrame,
    QApplication,
    QSizePolicy,
)
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QPixmap, QMouseEvent

from vortex.config import ASSETS_DIR


class _MessageBubble(QFrame):
    """A single chat message bubble."""

    MAX_BUBBLE_WIDTH = 220

    def __init__(self, text: str, is_user: bool, icon: QPixmap | None = None, parent=None):
        super().__init__(parent)
        self._is_user = is_user

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        # Icon for Vortex messages
        if not is_user and icon and not icon.isNull():
            icon_label = QLabel()
            icon_label.setPixmap(icon.scaled(
                24, 24,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            icon_label.setFixedSize(24, 24)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
            layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)

        # Message label
        label = QLabel(text)
        label.setWordWrap(True)
        label.setMaximumWidth(self.MAX_BUBBLE_WIDTH)
        label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        label.setFont(QFont("Sans Serif", 10))

        if is_user:
            label.setStyleSheet(
                "QLabel {"
                "  background-color: #D4E6F1;"
                "  border-radius: 10px;"
                "  padding: 8px;"
                "  color: #1a1a1a;"
                "}"
            )
        else:
            label.setStyleSheet(
                "QLabel {"
                "  background-color: #F0F0F0;"
                "  border-radius: 10px;"
                "  padding: 8px;"
                "  color: #1a1a1a;"
                "}"
            )

        if is_user:
            layout.addStretch()
            layout.addWidget(label)
        else:
            layout.addWidget(label)
            layout.addStretch()


class ChatWindow(QWidget):
    """A mini floating chat panel for talking to Vortex."""

    # Signals
    user_message = pyqtSignal(str)
    closed = pyqtSignal()

    WIDTH = 300
    HEIGHT = 400
    TITLE_BAR_H = 30
    INPUT_H = 40
    MAX_MESSAGES = 50

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setFixedSize(self.WIDTH, self.HEIGHT)

        # Load axolotl icon for Vortex messages
        icon_path = ASSETS_DIR / "icon.png"
        self._vortex_icon = QPixmap(str(icon_path)) if icon_path.exists() else QPixmap()

        # Drag state
        self._drag_offset: QPoint | None = None

        # Message count
        self._message_count = 0

        # Typing indicator label (managed separately)
        self._typing_label: _MessageBubble | None = None

        self._build_ui()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(1, self.TITLE_BAR_H + 1, 1, 1)
        root.setSpacing(0)

        # --- Chat area (scroll) ---
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet(
            "QScrollArea { background: #FFFFFF; border: none; }"
            "QScrollBar:vertical {"
            "  background: #F5F5F5; width: 6px; margin: 0;"
            "}"
            "QScrollBar::handle:vertical {"
            "  background: #C0C0C0; border-radius: 3px; min-height: 20px;"
            "}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {"
            "  height: 0; background: none;"
            "}"
        )

        # Container widget inside scroll area
        self._messages_widget = QWidget()
        self._messages_widget.setStyleSheet("background: #FFFFFF;")
        self._messages_layout = QVBoxLayout(self._messages_widget)
        self._messages_layout.setContentsMargins(4, 4, 4, 4)
        self._messages_layout.setSpacing(4)
        self._messages_layout.addStretch()

        self._scroll.setWidget(self._messages_widget)
        root.addWidget(self._scroll, 1)

        # --- Input area ---
        input_frame = QFrame()
        input_frame.setFixedHeight(self.INPUT_H)
        input_frame.setStyleSheet(
            "QFrame { background: #F8F8F8; border-top: 1px solid #E0E0E0; }"
        )

        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(6, 4, 6, 4)
        input_layout.setSpacing(0)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Talk to Vortex...")
        self._input.setFont(QFont("Sans Serif", 10))
        self._input.setStyleSheet(
            "QLineEdit {"
            "  background: #FFFFFF;"
            "  border: 1px solid #D0D0D0;"
            "  border-radius: 14px;"
            "  padding: 4px 12px;"
            "  color: #1a1a1a;"
            "}"
            "QLineEdit:focus {"
            "  border: 1px solid #7EB6E6;"
            "}"
        )
        self._input.returnPressed.connect(self._on_send)
        input_layout.addWidget(self._input)

        root.addWidget(input_frame)

    # ------------------------------------------------------------------ #
    # Painting (title bar + border)
    # ------------------------------------------------------------------ #

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Outer border
        painter.setPen(QPen(QColor("#B0B0B0"), 1))
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawRoundedRect(0, 0, w - 1, h - 1, 8, 8)

        # Title bar background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#2D2D2D"))
        painter.drawRoundedRect(1, 1, w - 2, self.TITLE_BAR_H, 8, 8)
        # Fill bottom corners of title bar (they should be square, not rounded)
        painter.drawRect(1, self.TITLE_BAR_H - 8, w - 2, 8)

        # Title text
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        painter.drawText(10, 1, w - 40, self.TITLE_BAR_H, int(Qt.AlignmentFlag.AlignVCenter), "Chat with Vortex")

        # Close button "X"
        close_rect_x = w - 26
        close_rect_y = 6
        close_size = 18
        painter.setPen(QPen(QColor("#AAAAAA"), 1.5))
        painter.drawLine(close_rect_x + 4, close_rect_y + 4, close_rect_x + close_size - 4, close_rect_y + close_size - 4)
        painter.drawLine(close_rect_x + close_size - 4, close_rect_y + 4, close_rect_x + 4, close_rect_y + close_size - 4)

        painter.end()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def show_near(self, anchor_x: int, anchor_y: int) -> None:
        """Position the chat window next to the pet and show it."""
        screen = QApplication.primaryScreen()
        if screen is None:
            self.move(anchor_x, anchor_y)
            self.show()
            return

        geo = screen.availableGeometry()
        gap = 8

        # Prefer to the left of the pet
        x = anchor_x - self.WIDTH - gap
        if x < geo.x():
            # Fall back to the right
            x = anchor_x + gap

        # Vertically: align bottom of chat with anchor, but keep on-screen
        y = anchor_y + 64 - self.HEIGHT
        y = max(geo.y(), min(y, geo.y() + geo.height() - self.HEIGHT))

        self.move(x, y)
        self.show()
        self.raise_()
        self._input.setFocus()

    def add_user_message(self, text: str) -> None:
        """Append a right-aligned user message bubble."""
        self._append_bubble(text, is_user=True)

    def add_vortex_message(self, text: str) -> None:
        """Append a left-aligned Vortex message bubble with icon."""
        self._remove_typing_indicator()
        self._append_bubble(text, is_user=False)

    def show_typing_indicator(self) -> None:
        """Show a 'Vortex is thinking...' indicator."""
        if self._typing_label is not None:
            return
        bubble = _MessageBubble("Vortex is thinking...", is_user=False, icon=self._vortex_icon)
        # Style the typing indicator with italic text
        for child in bubble.findChildren(QLabel):
            if child.text() == "Vortex is thinking...":
                child.setStyleSheet(
                    "QLabel {"
                    "  background-color: #F0F0F0;"
                    "  border-radius: 10px;"
                    "  padding: 8px;"
                    "  color: #888888;"
                    "  font-style: italic;"
                    "}"
                )
                break
        self._typing_label = bubble
        self._messages_layout.addWidget(bubble)
        self._scroll_to_bottom()

    # ------------------------------------------------------------------ #
    # Title-bar dragging
    # ------------------------------------------------------------------ #

    def mousePressEvent(self, event: QMouseEvent) -> None:
        pos = event.position().toPoint()

        # Check close button
        if self._hit_close_button(pos):
            self.close()
            self.closed.emit()
            return

        # Start drag only from title bar
        if event.button() == Qt.MouseButton.LeftButton and pos.y() <= self.TITLE_BAR_H:
            self._drag_offset = pos

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None:
            new_pos = event.globalPosition().toPoint() - self._drag_offset
            self.move(new_pos)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_offset = None

    def closeEvent(self, event) -> None:
        self.closed.emit()
        super().closeEvent(event)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _on_send(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self.add_user_message(text)
        self.user_message.emit(text)

    def _append_bubble(self, text: str, is_user: bool) -> None:
        icon = None if is_user else self._vortex_icon
        bubble = _MessageBubble(text, is_user=is_user, icon=icon)
        self._messages_layout.addWidget(bubble)
        self._message_count += 1

        # Enforce max messages
        while self._message_count > self.MAX_MESSAGES:
            # Remove the first widget after the stretch
            item = self._messages_layout.itemAt(1)
            if item and item.widget():
                widget = item.widget()
                self._messages_layout.removeWidget(widget)
                widget.deleteLater()
                self._message_count -= 1
            else:
                break

        self._scroll_to_bottom()

    def _remove_typing_indicator(self) -> None:
        if self._typing_label is not None:
            self._messages_layout.removeWidget(self._typing_label)
            self._typing_label.deleteLater()
            self._typing_label = None

    def _scroll_to_bottom(self) -> None:
        """Auto-scroll to the latest message after layout updates."""
        QTimer.singleShot(10, self._do_scroll)

    def _do_scroll(self) -> None:
        vbar = self._scroll.verticalScrollBar()
        vbar.setValue(vbar.maximum())

    def _hit_close_button(self, pos: QPoint) -> bool:
        """Check if a click position hits the close button area."""
        close_x = self.width() - 26
        close_y = 6
        return (
            close_x <= pos.x() <= close_x + 18
            and close_y <= pos.y() <= close_y + 18
        )
