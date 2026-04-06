"""
Vortex Desktop Pet — Proactive Behavior

Makes Vortex speak on its own based on context:
- Periodic screen observations (OCR)
- Time-of-day awareness
- Idle commentary based on mood
- Activity summaries
"""

import random
import subprocess
import time
from datetime import datetime

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


# How often to potentially make a proactive comment (seconds)
PROACTIVE_INTERVAL = 90
# How often to scan the screen (seconds)
SCREEN_SCAN_INTERVAL = 180
# Minimum time between any proactive comment (seconds)
MIN_COMMENT_GAP = 45


class ProactiveBrain(QObject):
    """Generates unsolicited contextual comments."""

    comment_ready = pyqtSignal(str)  # context string to send to AI brain

    def __init__(self, mood_state, parent=None):
        super().__init__(parent)
        self._mood = mood_state
        self._last_comment_time: float = time.time()
        self._last_screen_text: str = ""
        self._session_start = datetime.now()

        # Timer for periodic proactive checks
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        # Timer for screen scanning
        self._screen_timer = QTimer(self)
        self._screen_timer.timeout.connect(self._scan_screen)

    def start(self):
        """Start proactive behavior."""
        self._timer.start(PROACTIVE_INTERVAL * 1000)
        self._screen_timer.start(SCREEN_SCAN_INTERVAL * 1000)
        # Initial greeting after 5 seconds
        QTimer.singleShot(5000, self._greet)

    def stop(self):
        self._timer.stop()
        self._screen_timer.stop()

    def _can_comment(self) -> bool:
        """Rate limit: don't spam comments."""
        return (time.time() - self._last_comment_time) >= MIN_COMMENT_GAP

    def _emit(self, context: str):
        """Emit a comment request and update timestamp."""
        self._last_comment_time = time.time()
        self.comment_ready.emit(context)

    def _greet(self):
        """Initial greeting based on time of day."""
        hour = datetime.now().hour
        if hour < 6:
            ctx = "Es de madrugada. El desarrollador está trasnochando programando."
        elif hour < 12:
            ctx = "Es la mañana. El desarrollador acaba de empezar su jornada."
        elif hour < 14:
            ctx = "Es mediodía. Hora de almorzar pronto."
        elif hour < 19:
            ctx = "Es la tarde. El desarrollador sigue trabajando."
        elif hour < 22:
            ctx = "Es la noche. El desarrollador sigue activo."
        else:
            ctx = "Es tarde en la noche. El desarrollador debería descansar pronto."
        ctx += f" Saluda brevemente al desarrollador."
        self._emit(ctx)

    def _tick(self):
        """Periodic check — decide if we should say something."""
        if not self._can_comment():
            return

        # Weighted random: don't comment every time
        if random.random() > 0.4:  # 40% chance each tick
            return

        hour = datetime.now().hour
        mood = self._mood.mood.value
        idle_secs = time.time() - self._mood.last_event_time

        # Time-based comments
        if hour >= 23 or hour < 5:
            if random.random() < 0.5:
                self._emit(
                    f"Son las {datetime.now().strftime('%H:%M')}. "
                    f"Es muy tarde. Sugiere al desarrollador que descanse."
                )
                return

        # Mood-based comments
        if mood == "grumpy" and random.random() < 0.6:
            self._emit(
                f"El humor está bajo (score: {self._mood.score:.0f}/100). "
                f"Ha habido {self._mood.errors_count} errores. "
                f"Di algo motivador o sarcástico para animar."
            )
            return

        if mood == "bored" and idle_secs > 120:
            self._emit(
                f"Llevas {int(idle_secs)}s sin actividad. "
                f"Estás aburrido. Comenta algo sobre la inactividad."
            )
            return

        if mood == "ecstatic":
            self._emit(
                f"Todo va genial: {self._mood.successes_count} éxitos, "
                f"score {self._mood.score:.0f}/100. Celebra brevemente."
            )
            return

        # Session stats comment
        if self._mood.events_count > 0 and self._mood.events_count % 20 == 0:
            self._emit(
                f"Resumen parcial: {self._mood.events_count} eventos, "
                f"{self._mood.successes_count} éxitos, "
                f"{self._mood.errors_count} errores. "
                f"Da un mini resumen de cómo va la sesión."
            )
            return

        # Generic idle observation
        if idle_secs > 60:
            options = [
                "El desarrollador está pensando. Haz un comentario casual breve.",
                "No hay actividad reciente. Di algo observacional.",
                f"Llevas {int(idle_secs)}s en silencio. Comenta algo.",
            ]
            self._emit(random.choice(options))

    def _scan_screen(self):
        """OCR the screen and comment if something interesting changed."""
        if not self._can_comment():
            return

        try:
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            if screen is None:
                return

            pixmap = screen.grabWindow(0)
            tmp_path = "/tmp/vortex_proactive_ocr.png"
            pixmap.save(tmp_path, "PNG")

            result = subprocess.run(
                ["tesseract", tmp_path, "-", "-l", "spa+eng"],
                capture_output=True, text=True, timeout=10
            )
            screen_text = result.stdout.strip()[:1500]

            import os
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

            # Only comment if screen changed significantly
            if self._last_screen_text and self._texts_similar(screen_text, self._last_screen_text):
                return  # nothing new

            self._last_screen_text = screen_text

            if not screen_text or len(screen_text) < 50:
                return

            # 30% chance to comment on screen content
            if random.random() > 0.3:
                return

            # Extract a relevant snippet (not the whole thing)
            lines = [l.strip() for l in screen_text.split("\n") if len(l.strip()) > 10]
            if not lines:
                return
            snippet = "\n".join(lines[:10])

            self._emit(
                f"Observaste la pantalla del desarrollador. Texto visible:\n"
                f"---\n{snippet}\n---\n"
                f"Haz un comentario breve y útil sobre lo que ves."
            )

        except Exception:
            pass  # never crash the pet for proactive features

    @staticmethod
    def _texts_similar(a: str, b: str) -> bool:
        """Quick check if two OCR texts are roughly the same."""
        if not a or not b:
            return False
        # Compare first 200 chars
        return a[:200] == b[:200]
