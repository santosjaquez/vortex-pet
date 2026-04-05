"""Floating speech bubble widget for the Vortex desktop pet."""

import random

from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRectF
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QFont, QFontMetrics, QPen


class SpeechBubble(QWidget):
    """A floating speech bubble that appears above the pet sprite."""

    MAX_WIDTH = 250
    PADDING = 10
    BORDER_RADIUS = 10
    BORDER_WIDTH = 2
    TRIANGLE_WIDTH = 12
    TRIANGLE_HEIGHT = 8
    FONT_FAMILY = "Sans Serif"
    FONT_SIZE = 11

    MESSAGES: dict[str, list[str]] = {
        "petted": ["Hey.", "What's up?", "I'm here.", "Need something?"],
        "idle": ["...", "Waiting.", "All clear.", "Standing by."],
        "happy": ["Nice.", "Solid.", "That worked.", "Clean."],
        "sad": ["That failed.", "Check the output.", "Something broke.", "Hmm."],
        "typing": ["On it.", "Processing...", "Working...", "Let me check."],
        "confused": ["That's odd.", "Unexpected.", "Double check that.", "Huh."],
        "celebrate": ["Done.", "Ship it.", "Nailed it.", "All green."],
        "sleep": ["Idle.", "Taking a break.", "Low power mode."],
        "greet": ["Ready.", "Let's work.", "Online.", "What's the plan?"],
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._text = ""
        self._anchor_x = 0
        self._anchor_y = 0

        self._font = QFont(self.FONT_FAMILY, self.FONT_SIZE)

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self._start_dismiss)

        self._fade_anim: QPropertyAnimation | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_message(
        self, text: str, duration_ms: int, anchor_pos: tuple[int, int]
    ) -> None:
        """Display *text* above the pet for *duration_ms* milliseconds."""
        # Cancel any running fade / timer
        self._stop_animations()

        self._text = text
        self._anchor_x, self._anchor_y = anchor_pos

        # Reset opacity in case a previous fade left it < 1
        self.setWindowOpacity(1.0)

        self._resize_to_text()
        self._reposition()

        self.show()
        self.raise_()

        self._dismiss_timer.start(duration_ms)

    def update_anchor(self, x: int, y: int) -> None:
        """Move the bubble so it stays above the pet when the pet moves."""
        self._anchor_x = x
        self._anchor_y = y
        if self.isVisible():
            self._reposition()

    def hide_message(self) -> None:
        """Immediately hide the bubble and cancel pending timers."""
        self._stop_animations()
        self.hide()

    @classmethod
    def get_random_message(cls, category: str) -> str:
        """Return a random message from *category*, or '...' if unknown."""
        pool = cls.MESSAGES.get(category, ["..."])
        return random.choice(pool)

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        bubble_rect = QRectF(
            self.BORDER_WIDTH / 2,
            self.BORDER_WIDTH / 2,
            w - self.BORDER_WIDTH,
            h - self.TRIANGLE_HEIGHT - self.BORDER_WIDTH,
        )

        # --- build path: rounded rect + triangle pointer ---
        path = QPainterPath()
        path.addRoundedRect(bubble_rect, self.BORDER_RADIUS, self.BORDER_RADIUS)

        # Triangle at bottom-center pointing down
        tri_cx = w / 2
        tri_top = bubble_rect.bottom()
        tri_bottom = tri_top + self.TRIANGLE_HEIGHT

        tri_path = QPainterPath()
        tri_path.moveTo(tri_cx - self.TRIANGLE_WIDTH / 2, tri_top)
        tri_path.lineTo(tri_cx, tri_bottom)
        tri_path.lineTo(tri_cx + self.TRIANGLE_WIDTH / 2, tri_top)
        tri_path.closeSubpath()

        path = path.united(tri_path)

        # Fill + stroke
        painter.setPen(QPen(QColor("#333333"), self.BORDER_WIDTH))
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawPath(path)

        # --- draw text ---
        painter.setPen(QColor("#333333"))
        painter.setFont(self._font)

        text_rect = QRectF(
            self.PADDING,
            self.PADDING,
            w - 2 * self.PADDING,
            h - self.TRIANGLE_HEIGHT - 2 * self.PADDING,
        )
        painter.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            | int(Qt.TextFlag.TextWordWrap),
            self._text,
        )

        painter.end()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resize_to_text(self) -> None:
        fm = QFontMetrics(self._font)
        max_text_width = self.MAX_WIDTH - 2 * self.PADDING

        bounding = fm.boundingRect(
            0,
            0,
            max_text_width,
            0,
            int(Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap),
            self._text,
        )

        text_w = min(bounding.width(), max_text_width)
        text_h = bounding.height()

        width = text_w + 2 * self.PADDING + self.BORDER_WIDTH
        height = text_h + 2 * self.PADDING + self.TRIANGLE_HEIGHT + self.BORDER_WIDTH

        # Enforce minimum size so tiny messages still look good
        width = max(width, 40)
        height = max(height, 30 + self.TRIANGLE_HEIGHT)

        self.setFixedSize(int(width), int(height))

    def _reposition(self) -> None:
        """Place the bubble centered above the anchor point."""
        gap = 4  # pixels between triangle tip and anchor
        x = self._anchor_x - self.width() // 2
        y = self._anchor_y - self.height() - gap

        # Keep on-screen
        screen = QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            x = max(geo.x(), min(x, geo.x() + geo.width() - self.width()))
            y = max(geo.y(), y)

        self.move(x, y)

    def _start_dismiss(self) -> None:
        """Fade out over 500 ms, then hide."""
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(500)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InQuad)
        self._fade_anim.finished.connect(self.hide)
        self._fade_anim.start()

    def _stop_animations(self) -> None:
        self._dismiss_timer.stop()
        if self._fade_anim is not None:
            self._fade_anim.stop()
            self._fade_anim = None
