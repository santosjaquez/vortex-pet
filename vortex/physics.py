from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication

from vortex.config import SPRITE_SIZE, TICK_MS, GRAVITY, BOUNCE_DAMPING, GROUND_THRESHOLD


class PhysicsEngine(QObject):
    """Simple 2D physics for dropping, bouncing, and sliding the desktop pet."""

    landed = pyqtSignal()

    def __init__(self, pet_window, parent=None):
        super().__init__(parent)
        self._pet = pet_window

        # Screen geometry
        self._screen_rect = QApplication.primaryScreen().availableGeometry()
        self._floor_y = self._screen_rect.bottom() - SPRITE_SIZE + 1

        # Velocity in pixels per tick
        self._vx: float = 0.0
        self._vy: float = 0.0

        # Floating-point position for sub-pixel accuracy
        self._x: float = float(self._pet.x())
        self._y: float = float(self._pet.y())

        # Physics timer (not started until needed)
        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def is_grounded(self) -> bool:
        """True when the pet is resting on the floor with no significant velocity."""
        return (
            int(self._y) >= self._floor_y
            and not self._timer.isActive()
        )

    @property
    def floor_y(self) -> int:
        return self._floor_y

    @property
    def screen_rect(self):
        return self._screen_rect

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def start_falling(self, vx: float = 0.0, vy: float = 0.0):
        """Begin physics simulation with an initial velocity (px/sec)."""
        # Convert px/sec to px/tick
        ticks_per_sec = 1000.0 / TICK_MS
        self._vx = vx / ticks_per_sec
        self._vy = vy / ticks_per_sec

        # Sync floating position with actual widget position
        self._x = float(self._pet.x())
        self._y = float(self._pet.y())

        self._timer.start()

    def stop(self):
        """Stop the physics timer."""
        self._timer.stop()

    def place_on_ground(self, x: int = None):
        """Place the pet at floor level. Uses current x if none given."""
        if x is None:
            x = self._pet.x()
        self._x = float(x)
        self._y = float(self._floor_y)
        self._vx = 0.0
        self._vy = 0.0
        self._pet.move_to(int(self._x), int(self._y))

    def refresh_screen_geometry(self):
        """Re-read screen geometry (call on screen/resolution changes)."""
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        self._screen_rect = screen.availableGeometry()
        self._floor_y = self._screen_rect.bottom() - SPRITE_SIZE + 1

    # ------------------------------------------------------------------ #
    # Simulation tick
    # ------------------------------------------------------------------ #

    def _tick(self):
        # 1. Gravity (positive y = downward in screen coords)
        self._vy += GRAVITY

        # 2. Update position
        self._x += self._vx
        self._y += self._vy

        # 3. Air friction on horizontal velocity
        self._vx *= 0.98

        # 4. Floor collision
        if self._y >= self._floor_y:
            self._y = float(self._floor_y)
            self._vy = -self._vy * BOUNCE_DAMPING
            self._vx *= 0.8  # ground friction

            if abs(self._vy) < GROUND_THRESHOLD:
                self._vy = 0.0
                if abs(self._vx) < 0.5:
                    self._timer.stop()
                    self._pet.move_to(int(self._x), int(self._y))
                    self.landed.emit()
                    return

        # 5. Wall collision
        left_bound = float(self._screen_rect.left())
        right_bound = float(self._screen_rect.right() - SPRITE_SIZE)

        if self._x < left_bound:
            self._x = left_bound
            self._vx = -self._vx * 0.5
        elif self._x > right_bound:
            self._x = right_bound
            self._vx = -self._vx * 0.5

        # 6. Move the widget
        self._pet.move_to(int(self._x), int(self._y))
