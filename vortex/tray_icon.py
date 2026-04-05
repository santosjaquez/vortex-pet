"""
Vortex Desktop Pet — System Tray Icon

Provides a system tray icon with a context menu for controlling the pet:
show/hide, wake up, reset position, and quit.
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt

from vortex.config import ASSETS_DIR, SPRITE_SIZE, FLOOR_OFFSET
from vortex.state_machine import PetState


class TrayIcon(QSystemTrayIcon):
    """System tray icon for the Vortex desktop pet."""

    def __init__(self, pet_window, state_machine, app):
        super().__init__(parent=app)

        self._pet_window = pet_window
        self._state_machine = state_machine
        self._app = app

        # Load tray icon
        icon_path = ASSETS_DIR / "icon.png"
        if icon_path.exists():
            self.setIcon(QIcon(str(icon_path)))
        else:
            # Fallback to application icon if icon.png is missing
            self.setIcon(app.windowIcon())

        self.setToolTip("Vortex — Desktop Axolotl")

        # Build context menu
        menu = QMenu()

        show_hide_action = QAction("Show/Hide Vortex", menu)
        show_hide_action.triggered.connect(self._toggle_visibility)
        menu.addAction(show_hide_action)

        wake_action = QAction("Wake Up", menu)
        wake_action.triggered.connect(self._wake_up)
        menu.addAction(wake_action)

        reset_action = QAction("Reset Position", menu)
        reset_action.triggered.connect(self._reset_position)
        menu.addAction(reset_action)

        menu.addSeparator()

        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

        # Double-click on tray icon toggles visibility
        self.activated.connect(self._on_activated)

    # ------------------------------------------------------------------ #
    # Slots
    # ------------------------------------------------------------------ #

    def _toggle_visibility(self):
        """Toggle the pet window's visibility."""
        self._pet_window.setVisible(not self._pet_window.isVisible())

    def _wake_up(self):
        """Force the pet out of sleep into idle state."""
        self._state_machine.transition(PetState.IDLE)

    def _reset_position(self):
        """Move the pet back to the default bottom-right position."""
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        x = geo.right() - SPRITE_SIZE - 20
        y = geo.bottom() - SPRITE_SIZE - FLOOR_OFFSET
        self._pet_window.move(x, y)

    def _on_activated(self, reason):
        """Handle tray icon activation (double-click toggles visibility)."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_visibility()
