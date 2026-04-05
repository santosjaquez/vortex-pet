"""
Vortex Desktop Pet — State Machine

The "brain" of the pet: manages state transitions, autonomous behavior
(idle/walk/sleep cycle), and reactions to user interaction and Claude Code
hook events.
"""

import enum
import random

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from vortex.config import (
    IDLE_MIN_MS,
    IDLE_MAX_MS,
    WALK_MIN_MS,
    WALK_MAX_MS,
    WALK_SPEED,
    SLEEP_MIN_MS,
    SLEEP_MAX_MS,
    TICK_MS,
    SPRITE_SIZE,
    BUBBLE_DURATION_MS,
)


class PetState(enum.Enum):
    IDLE = "idle"
    WALKING = "walking"
    SLEEPING = "sleeping"
    HAPPY = "happy"
    SAD = "sad"
    TYPING = "typing"
    PETTED = "petted"
    CONFUSED = "confused"
    CELEBRATING = "celebrating"
    FALLING = "falling"
    DRAGGING = "dragging"


# Map PetState -> animation name in sprites.json
_STATE_ANIM = {
    PetState.IDLE: "idle",
    PetState.WALKING: "walk",
    PetState.SLEEPING: "sleep",
    PetState.HAPPY: "happy",
    PetState.SAD: "sad",
    PetState.TYPING: "typing",
    PetState.PETTED: "petted",
    PetState.CONFUSED: "confused",
    PetState.CELEBRATING: "celebrate",
    PetState.FALLING: "fall",
    # DRAGGING keeps whatever animation was playing
}

# States that loop their animation
_LOOPING_STATES = {
    PetState.IDLE,
    PetState.WALKING,
    PetState.SLEEPING,
    PetState.TYPING,
    PetState.FALLING,
}

# Reaction states: animation plays once, then _on_reaction_done fires
_REACTION_STATES = {
    PetState.HAPPY,
    PetState.SAD,
    PetState.PETTED,
    PetState.CONFUSED,
    PetState.CELEBRATING,
}

# States that should not be interrupted by hook events
_UNINTERRUPTIBLE = {PetState.DRAGGING, PetState.FALLING}

# Tool names that trigger TYPING state
_ACTIVE_TOOLS = {"Bash", "Edit", "Write", "NotebookEdit"}
# Tool names that only get a small bubble (no state change)
_PASSIVE_TOOLS = {"Read", "Grep", "Glob"}


class StateMachine(QObject):
    """Manages the pet's behavioral state and autonomous transitions."""

    state_changed = pyqtSignal(object)  # emits PetState

    def __init__(self, sprite_renderer, pet_window):
        super().__init__()

        self._renderer = sprite_renderer
        self._window = pet_window
        self._state: PetState = PetState.IDLE

        # Deferred dependencies
        self._physics = None
        self._bubble = None

        # State duration timer (singleShot)
        self._state_timer = QTimer(self)
        self._state_timer.setSingleShot(True)
        self._state_timer.timeout.connect(self._on_state_timeout)

        # Walk movement timer (fires every TICK_MS while walking)
        self._walk_timer = QTimer(self)
        self._walk_timer.setInterval(TICK_MS)
        self._walk_timer.timeout.connect(self._walk_tick)

        # Walk direction: 1 = right, -1 = left
        self._walk_direction: int = 1

    # ------------------------------------------------------------------
    # Deferred dependency injection
    # ------------------------------------------------------------------

    def set_physics(self, physics_engine):
        """Connect the physics engine after construction."""
        self._physics = physics_engine
        self._physics.landed.connect(self._on_landed)

    def set_bubble(self, speech_bubble):
        """Connect the speech bubble widget after construction."""
        self._bubble = speech_bubble

    # ------------------------------------------------------------------
    # Core transition
    # ------------------------------------------------------------------

    def transition(self, new_state: PetState, speech: str = None):
        """Transition to *new_state*, optionally showing *speech* text."""

        # Don't re-trigger stable looping states
        if new_state == self._state and new_state in (PetState.IDLE, PetState.WALKING):
            return

        # Stop autonomous timers
        self._state_timer.stop()
        self._walk_timer.stop()

        self._state = new_state

        # Play the appropriate animation
        if new_state != PetState.DRAGGING:
            anim_name = _STATE_ANIM.get(new_state)
            if anim_name is not None:
                if new_state in _LOOPING_STATES:
                    self._renderer.play(anim_name, loop=True)
                elif new_state in _REACTION_STATES:
                    self._renderer.play(
                        anim_name, loop=False, on_complete=self._on_reaction_done
                    )
                else:
                    self._renderer.play(anim_name, loop=True)

        # Show speech bubble if text provided
        if speech is not None:
            self._show_bubble_text(speech)

        # Start state duration timer
        duration = self._get_state_duration(new_state)
        if duration is not None:
            self._state_timer.start(duration)

        # Start walk movement if entering WALKING
        if new_state == PetState.WALKING:
            self._walk_timer.start()

        self.state_changed.emit(new_state)

    # ------------------------------------------------------------------
    # State durations
    # ------------------------------------------------------------------

    @staticmethod
    def _get_state_duration(state: PetState):
        """Return duration in ms for the given state, or None if no timer."""
        if state == PetState.IDLE:
            return random.randint(IDLE_MIN_MS, IDLE_MAX_MS)
        if state == PetState.WALKING:
            return random.randint(WALK_MIN_MS, WALK_MAX_MS)
        if state == PetState.SLEEPING:
            return random.randint(SLEEP_MIN_MS, SLEEP_MAX_MS)
        if state == PetState.TYPING:
            return 5000
        # Reaction states, FALLING, DRAGGING: no timer
        return None

    # ------------------------------------------------------------------
    # Timer callbacks
    # ------------------------------------------------------------------

    def _on_state_timeout(self):
        """Decide what to do when the current state's duration expires."""
        if self._state == PetState.IDLE:
            roll = random.random()
            if roll < 0.60:
                self.transition(PetState.IDLE)
            elif roll < 0.90:
                self._walk_direction = random.choice([-1, 1])
                self.transition(PetState.WALKING)
            else:
                self.transition(PetState.SLEEPING)

        elif self._state == PetState.WALKING:
            self.transition(PetState.IDLE)

        elif self._state == PetState.SLEEPING:
            wake_msgs = ["Good morning!", "That was a nice nap!", "*stretch*"]
            self.transition(PetState.IDLE, speech=random.choice(wake_msgs))

        elif self._state == PetState.TYPING:
            self.transition(PetState.IDLE)

        else:
            self.transition(PetState.IDLE)

    def _on_reaction_done(self):
        """Called when a non-looping reaction animation finishes."""
        self.transition(PetState.IDLE)

    # ------------------------------------------------------------------
    # Walk movement
    # ------------------------------------------------------------------

    def _walk_tick(self):
        """Move the pet window horizontally each tick while walking."""
        from PyQt6.QtWidgets import QApplication

        current_x = self._window.x()
        current_y = self._window.y()

        new_x = current_x + int(WALK_SPEED * self._walk_direction)

        # Screen bounds check
        screen = QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            left = geo.x()
            right = geo.x() + geo.width() - SPRITE_SIZE

            if new_x <= left:
                new_x = left
                self._walk_direction = 1
            elif new_x >= right:
                new_x = right
                self._walk_direction = -1

        self._window.move(new_x, current_y)

    # ------------------------------------------------------------------
    # Event handlers (public API)
    # ------------------------------------------------------------------

    def on_petted(self):
        """User clicked on the pet (without dragging)."""
        if self._state in _UNINTERRUPTIBLE:
            return
        self.transition(PetState.PETTED, speech=self._random_msg("petted"))

    def on_drag_started(self):
        """User started dragging the pet."""
        self.transition(PetState.DRAGGING)

    def on_drag_released(self, vx: float, vy: float):
        """User released the pet after dragging."""
        if self._physics is not None:
            self.transition(PetState.FALLING)
            self._physics.start_falling(vx, vy)
        else:
            self.transition(PetState.IDLE)

    def _on_landed(self):
        """Physics engine signals the pet has landed on the ground."""
        self.transition(PetState.IDLE)

    def on_hook_event(self, event_name: str, data: dict):
        """React to a Claude Code hook event forwarded by EventRouter."""
        # Never interrupt drag or fall
        if self._state in _UNINTERRUPTIBLE:
            return

        tool_name = data.get("tool_name", "")

        if event_name == "PostToolUse":
            if tool_name in _ACTIVE_TOOLS:
                self.transition(PetState.TYPING, speech=self._random_msg("typing"))
            elif tool_name in _PASSIVE_TOOLS:
                # Just show a small bubble, don't change state
                self._show_bubble_text(self._random_msg("typing"))

        elif event_name == "PostToolUseFailure":
            self.transition(PetState.SAD, speech=self._random_msg("sad"))

        elif event_name == "Stop":
            if random.random() < 0.5:
                self.transition(PetState.HAPPY, speech=self._random_msg("happy"))
            else:
                self.transition(
                    PetState.CELEBRATING, speech=self._random_msg("celebrate")
                )

        elif event_name == "Notification":
            text = str(data.get("tool_response", "Hey!"))[:60]
            self.transition(PetState.HAPPY, speech=text)

        elif event_name == "SessionStart":
            self.transition(PetState.CELEBRATING, speech=self._random_msg("greet"))

        elif event_name == "SessionEnd":
            self.transition(PetState.SLEEPING, speech=self._random_msg("sleep"))

    # ------------------------------------------------------------------
    # Speech bubble helpers
    # ------------------------------------------------------------------

    def _show_bubble(self, category: str):
        """Show a random message from the given SpeechBubble category."""
        if self._bubble is None:
            return
        from vortex.speech_bubble import SpeechBubble

        text = SpeechBubble.get_random_message(category)
        anchor = self._pet_anchor()
        self._bubble.show_message(text, BUBBLE_DURATION_MS, anchor)

    def _show_bubble_text(self, text: str):
        """Show a specific text in the speech bubble."""
        if self._bubble is None:
            return
        anchor = self._pet_anchor()
        self._bubble.show_message(text, BUBBLE_DURATION_MS, anchor)

    def _pet_anchor(self) -> tuple[int, int]:
        """Return the anchor point (top-center of pet window)."""
        return (
            self._window.x() + SPRITE_SIZE // 2,
            self._window.y(),
        )

    @staticmethod
    def _random_msg(category: str) -> str:
        """Get a random message from SpeechBubble.MESSAGES."""
        from vortex.speech_bubble import SpeechBubble

        return SpeechBubble.get_random_message(category)
