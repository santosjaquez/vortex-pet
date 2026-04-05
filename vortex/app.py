"""
Vortex Desktop Pet — Application entry point.

Creates all components, wires signals/slots, and starts the event loop.
"""

import sys
import signal
import atexit
import os

from PyQt6.QtWidgets import QApplication

from vortex.config import ASSETS_DIR, SOCKET_PATH
from vortex.pet_window import PetWindow
from vortex.sprite_renderer import SpriteRenderer
from vortex.speech_bubble import SpeechBubble
from vortex.physics import PhysicsEngine
from vortex.state_machine import StateMachine, PetState
from vortex.event_router import EventRouter
from vortex.window_detector import WindowDetector


def _cleanup_socket():
    """Remove the Unix socket file on exit."""
    try:
        if os.path.exists(SOCKET_PATH):
            os.unlink(SOCKET_PATH)
    except OSError:
        pass


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Vortex")
    app.setQuitOnLastWindowClosed(False)

    # Graceful shutdown on SIGINT / SIGTERM
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    signal.signal(signal.SIGTERM, lambda *_: app.quit())

    # -- Create components ------------------------------------------------
    pet = PetWindow()
    renderer = SpriteRenderer(ASSETS_DIR)
    bubble = SpeechBubble()
    physics = PhysicsEngine(pet)
    fsm = StateMachine(renderer, pet)
    router = EventRouter()
    win_detector = WindowDetector()

    # -- Deferred injection -----------------------------------------------
    fsm.set_physics(physics)
    fsm.set_bubble(bubble)
    fsm.set_window_detector(win_detector)
    physics.set_window_detector(win_detector)

    # -- Wire signals -----------------------------------------------------

    # Renderer frame_changed(QPixmap) -> PetWindow.set_pixmap(QPixmap)
    renderer.frame_changed.connect(pet.set_pixmap)

    # PetWindow interactions -> StateMachine
    pet.petted.connect(fsm.on_petted)
    pet.drag_started.connect(fsm.on_drag_started)
    pet.drag_released.connect(fsm.on_drag_released)  # (float, float)

    # PetWindow position_changed(int, int) -> SpeechBubble.update_anchor(int, int)
    pet.position_changed.connect(bubble.update_anchor)

    # EventRouter hook_event(str, dict) -> StateMachine.on_hook_event(str, dict)
    router.hook_event.connect(fsm.on_hook_event)

    # PhysicsEngine landed_on_window(int) -> StateMachine
    physics.landed_on_window.connect(fsm.on_landed_on_window)

    # -- Start socket server and window detector --------------------------
    router.start()
    win_detector.start()
    atexit.register(_cleanup_socket)

    # -- Place pet on screen, start idle ----------------------------------
    physics.place_on_ground()
    pet.show()
    fsm.transition(PetState.IDLE)

    # -- Optional tray icon (loaded if module exists) ---------------------
    tray = None
    try:
        from vortex.tray_icon import TrayIcon
        tray = TrayIcon(pet, fsm, app)
        tray.show()
    except ImportError:
        pass

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
