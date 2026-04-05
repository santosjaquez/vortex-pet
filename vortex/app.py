"""
Vortex Desktop Pet — Application entry point.

Creates all components, wires signals/slots, and starts the event loop.
"""

import sys
import signal
import atexit
import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from vortex.config import ASSETS_DIR, SOCKET_PATH, SPRITE_SIZE, BUBBLE_DURATION_MS
from vortex.pet_window import PetWindow
from vortex.sprite_renderer import SpriteRenderer
from vortex.speech_bubble import SpeechBubble
from vortex.physics import PhysicsEngine
from vortex.state_machine import StateMachine, PetState
from vortex.event_router import EventRouter
from vortex.window_detector import WindowDetector
from vortex.mood import MoodState
from vortex.ai_brain import AiBrain
from vortex.chat_window import ChatWindow


def _cleanup():
    """Clean up resources on exit."""
    # Remove Unix socket
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
    mood = MoodState()
    brain = AiBrain(mood)
    chat = ChatWindow()

    # -- Deferred injection -----------------------------------------------
    fsm.set_physics(physics)
    fsm.set_bubble(bubble)
    fsm.set_window_detector(win_detector)
    fsm.set_ai_brain(brain)
    fsm.set_mood(mood)
    physics.set_window_detector(win_detector)

    # -- Wire signals -----------------------------------------------------

    # Renderer frame_changed(QPixmap) -> PetWindow.set_pixmap(QPixmap)
    renderer.frame_changed.connect(pet.set_pixmap)

    # PetWindow interactions -> StateMachine
    pet.petted.connect(fsm.on_petted)
    pet.drag_started.connect(fsm.on_drag_started)
    pet.drag_released.connect(fsm.on_drag_released)

    # PetWindow position_changed(int, int) -> SpeechBubble.update_anchor(int, int)
    pet.position_changed.connect(bubble.update_anchor)

    # EventRouter hook_event(str, dict) -> StateMachine.on_hook_event(str, dict)
    router.hook_event.connect(fsm.on_hook_event)

    # PhysicsEngine landed_on_window(int) -> StateMachine
    physics.landed_on_window.connect(fsm.on_landed_on_window)

    # AI Brain -> Speech bubble (show AI-generated messages from hooks)
    def on_ai_message(text):
        anchor = (pet.x() + SPRITE_SIZE // 2, pet.y())
        bubble.show_message(text, BUBBLE_DURATION_MS, anchor)
    brain.message_ready.connect(on_ai_message)

    # Chat uses a separate AiBrain so hook comments and chat don't interfere
    chat_brain = AiBrain(mood)
    chat_brain.message_ready.connect(chat.add_vortex_message)

    # Keywords that trigger screen analysis
    _SCREEN_KEYWORDS = ["pantalla", "screen", "mira", "look", "ve mi", "que ves",
                        "what do you see", "que hay", "screenshot", "captura"]

    def on_chat_send(text):
        chat.show_typing_indicator()
        text_lower = text.lower()
        if any(kw in text_lower for kw in _SCREEN_KEYWORDS):
            chat_brain.analyze_screen(text)
        else:
            chat_brain.generate_chat_reply(text)
    chat.user_message.connect(on_chat_send)

    # Double-click pet -> open chat
    def on_pet_double_click():
        if chat.isVisible():
            chat.hide()
        else:
            chat.show_near(pet.x(), pet.y())
    pet.double_clicked.connect(on_pet_double_click)

    # Mood decay timer (every 30 seconds)
    mood_timer = QTimer()
    mood_timer.timeout.connect(mood.decay)
    mood_timer.start(30000)

    # -- Cleanup on exit --------------------------------------------------
    def shutdown():
        _cleanup()
        win_detector.stop()
        router.stop()

    app.aboutToQuit.connect(shutdown)
    atexit.register(_cleanup)

    # -- Start socket server and window detector --------------------------
    router.start()
    win_detector.start()

    # -- Place pet on screen, start idle ----------------------------------
    physics.place_on_ground()
    pet.show()
    fsm.transition(PetState.IDLE)

    # -- Tray icon --------------------------------------------------------
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
