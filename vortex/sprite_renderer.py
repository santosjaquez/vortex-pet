"""Sprite rendering engine for Vortex desktop pet."""

import json
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap


class SpriteRenderer(QObject):
    """Loads and plays sprite animations from PNG frame sequences."""

    frame_changed = pyqtSignal(QPixmap)
    animation_finished = pyqtSignal(str)

    def __init__(self, assets_dir: Path, parent: Optional[QObject] = None):
        super().__init__(parent)

        self._assets_dir = Path(assets_dir)
        self._sprites_dir = self._assets_dir / "sprites"

        # Load animation metadata
        meta_path = self._assets_dir / "sprites.json"
        with open(meta_path, "r") as f:
            self._meta: dict = json.load(f)

        # Pre-load all PNG frames into QPixmaps
        self._frames: dict[str, list[QPixmap]] = {}
        for anim_name, info in self._meta.items():
            frames = []
            for i in range(info["frames"]):
                path = self._sprites_dir / anim_name / f"{anim_name}_{i:02d}.png"
                pixmap = QPixmap(str(path))
                if pixmap.isNull():
                    # Create a small fallback pixmap so we never crash
                    pixmap = QPixmap(128, 128)
                    pixmap.fill()
                frames.append(pixmap)
            self._frames[anim_name] = frames

        # Playback state
        self._current_anim: Optional[str] = None
        self._frame_index: int = 0
        self._looping: bool = True
        self._on_complete: Optional[callable] = None

        # Animation timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_frame)

    # ── Properties ──────────────────────────────────────────────────

    @property
    def current_pixmap(self) -> Optional[QPixmap]:
        """Return the QPixmap for the current frame."""
        if self._current_anim and self._current_anim in self._frames:
            frames = self._frames[self._current_anim]
            if frames:
                return frames[self._frame_index % len(frames)]
        return None

    @property
    def current_animation(self) -> Optional[str]:
        """Return the name of the currently playing animation."""
        return self._current_anim

    # ── Public API ──────────────────────────────────────────────────

    def play(
        self,
        animation_name: str,
        loop: Optional[bool] = None,
        on_complete: Optional[callable] = None,
    ) -> None:
        """Start playing the named animation.

        Args:
            animation_name: Key from sprites.json (e.g. "idle", "walk").
            loop: Override looping behaviour. None uses the default from
                  sprites.json.
            on_complete: Callback invoked when a non-looping animation
                         finishes its last frame.
        """
        if animation_name not in self._meta:
            return

        info = self._meta[animation_name]

        # Reset frame counter when the animation changes
        if animation_name != self._current_anim:
            self._frame_index = 0

        self._current_anim = animation_name
        self._looping = info["loop"] if loop is None else loop
        self._on_complete = on_complete

        # (Re)start timer at the correct interval for this animation's fps
        interval = 1000 // info["fps"]
        self._timer.start(interval)

        # Emit the first frame immediately
        pixmap = self.current_pixmap
        if pixmap is not None:
            self.frame_changed.emit(pixmap)

    def stop(self) -> None:
        """Stop the animation timer."""
        self._timer.stop()

    # ── Internal ────────────────────────────────────────────────────

    def _advance_frame(self) -> None:
        """Advance to the next frame; called by QTimer."""
        if self._current_anim is None:
            return

        frames = self._frames[self._current_anim]
        total = len(frames)

        self._frame_index += 1

        if self._looping:
            self._frame_index %= total
        elif self._frame_index >= total:
            # Non-looping animation finished
            self._frame_index = total - 1
            self._timer.stop()
            self.animation_finished.emit(self._current_anim)
            if self._on_complete is not None:
                self._on_complete()
            return

        self.frame_changed.emit(frames[self._frame_index])
