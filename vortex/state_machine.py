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
    CLIMB_SPEED,
    WALK_ON_WINDOW_PROB,
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
    CLIMBING = "climbing"
    WALKING_ON_WINDOW = "walking_on_window"


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
    PetState.CLIMBING: "climb",
    PetState.WALKING_ON_WINDOW: "walk",
    # DRAGGING keeps whatever animation was playing
}

# States that loop their animation
_LOOPING_STATES = {
    PetState.IDLE,
    PetState.WALKING,
    PetState.SLEEPING,
    PetState.TYPING,
    PetState.FALLING,
    PetState.CLIMBING,
    PetState.WALKING_ON_WINDOW,
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
_UNINTERRUPTIBLE = {PetState.DRAGGING, PetState.FALLING, PetState.CLIMBING}

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
        self._state: PetState = None  # no initial state; first transition() sets it

        # Deferred dependencies
        self._physics = None
        self._bubble = None
        self._window_detector = None

        # State duration timer (singleShot)
        self._state_timer = QTimer(self)
        self._state_timer.setSingleShot(True)
        self._state_timer.timeout.connect(self._on_state_timeout)

        # Walk movement timer (fires every TICK_MS while walking)
        self._walk_timer = QTimer(self)
        self._walk_timer.setInterval(TICK_MS)
        self._walk_timer.timeout.connect(self._walk_tick)

        # Climb movement timer
        self._climb_timer = QTimer(self)
        self._climb_timer.setInterval(TICK_MS)
        self._climb_timer.timeout.connect(self._climb_tick)

        # Walk direction: 1 = right, -1 = left
        self._walk_direction: int = 1

        # Climbing state
        self._climb_edge = None  # Edge being climbed
        self._climb_direction: int = -1  # -1 = up, 1 = down
        self._target_edge = None  # Edge we're walking toward
        self._walk_target_x: int = None  # X position to reach before climbing

        # Walking on window surface
        self._on_window_surface: bool = False
        self._window_surface_y: int = 0
        self._window_edge = None  # Edge we're walking on

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

    def set_window_detector(self, detector):
        """Connect the window detector after construction."""
        self._window_detector = detector

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

        # Stop climbing timer if leaving climb
        self._climb_timer.stop()

        # Start walk movement if entering WALKING or WALKING_ON_WINDOW
        if new_state in (PetState.WALKING, PetState.WALKING_ON_WINDOW):
            self._walk_timer.start()

        # Start climb movement if entering CLIMBING
        if new_state == PetState.CLIMBING:
            self._climb_timer.start()

        self.state_changed.emit(new_state)

    # ------------------------------------------------------------------
    # State durations
    # ------------------------------------------------------------------

    @staticmethod
    def _get_state_duration(state: PetState):
        """Return duration in ms for the given state, or None if no timer."""
        if state == PetState.IDLE:
            return random.randint(IDLE_MIN_MS, IDLE_MAX_MS)
        if state in (PetState.WALKING, PetState.WALKING_ON_WINDOW):
            return random.randint(WALK_MIN_MS, WALK_MAX_MS)
        if state == PetState.SLEEPING:
            return random.randint(SLEEP_MIN_MS, SLEEP_MAX_MS)
        if state == PetState.TYPING:
            return 5000
        # CLIMBING has no timer — ends when reaching top or bottom of edge
        # Reaction states, FALLING, DRAGGING: no timer
        return None

    # ------------------------------------------------------------------
    # Timer callbacks
    # ------------------------------------------------------------------

    def _on_state_timeout(self):
        """Decide what to do when the current state's duration expires."""
        if self._state == PetState.IDLE:
            roll = random.random()
            if roll < 0.50:
                self.transition(PetState.IDLE)
            elif roll < 0.80:
                self._walk_direction = random.choice([-1, 1])
                self.transition(PetState.WALKING)
            elif roll < 0.80 + WALK_ON_WINDOW_PROB:
                # Try to climb a nearby window
                if self._try_start_climbing():
                    return
                self.transition(PetState.IDLE)
            else:
                self.transition(PetState.SLEEPING)

        elif self._state == PetState.WALKING:
            # Chance to start climbing if near a window edge
            if random.random() < 0.25 and self._try_start_climbing():
                return
            self.transition(PetState.IDLE)

        elif self._state == PetState.WALKING_ON_WINDOW:
            # After walking on window, either idle on window or climb down/fall
            if random.random() < 0.5:
                self.transition(PetState.IDLE)
            else:
                # Fall off the window
                self._on_window_surface = False
                if self._physics is not None:
                    self.transition(PetState.FALLING)
                    self._physics.start_falling(0, 0)
                else:
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

        # Check if we've reached a target edge to climb
        if (self._state == PetState.WALKING
                and self._target_edge is not None
                and self._walk_target_x is not None):
            if abs(new_x - self._walk_target_x) < 5:
                edge = self._target_edge
                self._target_edge = None
                self._walk_target_x = None
                self._climb_edge = edge
                self._climb_direction = -1
                self._walk_timer.stop()
                self.transition(PetState.CLIMBING, speech=random.choice(
                    ["Wheee!", "*climb climb*", "Up we go!"]
                ))
                return

        # If walking on a window, constrain to window edges
        if self._state == PetState.WALKING_ON_WINDOW and self._window_edge is not None:
            edge = self._window_edge
            left = edge.x
            right = edge.x + edge.width - SPRITE_SIZE

            if new_x <= left:
                new_x = left
                self._walk_direction = 1
            elif new_x >= right:
                new_x = right
                self._walk_direction = -1

            self._window.move_to(new_x, current_y)
            return

        # Screen bounds check (normal walking on desktop)
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

        self._window.move_to(new_x, current_y)

    # ------------------------------------------------------------------
    # Climbing logic
    # ------------------------------------------------------------------

    def _try_start_climbing(self) -> bool:
        """Find nearest window edge and walk toward it, then climb."""
        if self._window_detector is None:
            return False

        # First check if already touching an edge
        edge = self._window_detector.find_climbable_edge(
            self._window.x(), self._window.y(), SPRITE_SIZE
        )
        if edge is not None:
            self._climb_edge = edge
            self._climb_direction = -1
            self.transition(PetState.CLIMBING, speech=random.choice(
                ["Wheee!", "*climb climb*", "Up we go!"]
            ))
            return True

        # Find nearest window edge at same floor level and walk toward it
        pet_x = self._window.x()
        pet_y = self._window.y()
        best_edge = None
        best_dist = float("inf")

        for edge in self._window_detector.edges:
            if edge.edge_type not in ("left", "right"):
                continue
            # Only consider edges that extend to near the pet's Y level
            edge_bottom = edge.y + edge.height
            if edge_bottom < pet_y:
                continue  # edge is above the pet, unreachable

            # Calculate horizontal distance
            if edge.edge_type == "left":
                target_x = edge.x - SPRITE_SIZE
            else:
                target_x = edge.x + edge.width
            dist = abs(pet_x - target_x)

            if dist < best_dist and dist < 800:  # max 800px to walk
                best_dist = dist
                best_edge = edge

        if best_edge is None:
            return False

        # Set target and walk toward it
        self._target_edge = best_edge
        if best_edge.edge_type == "left":
            target_x = best_edge.x - SPRITE_SIZE
        else:
            target_x = best_edge.x + best_edge.width
        self._walk_direction = 1 if target_x > pet_x else -1
        self._walk_target_x = target_x
        self.transition(PetState.WALKING)
        return True

    def _climb_tick(self):
        """Move the pet vertically along a window edge."""
        if self._climb_edge is None:
            self.transition(PetState.IDLE)
            return

        current_y = self._window.y()
        new_y = current_y + int(CLIMB_SPEED * self._climb_direction)

        edge = self._climb_edge
        edge_top = edge.y
        edge_bottom = edge.y + edge.height - SPRITE_SIZE

        # Reached the top of the edge — step onto the window title bar
        if new_y <= edge_top:
            new_y = edge_top - SPRITE_SIZE  # sit on top of the window
            self._climb_timer.stop()
            self._on_window_surface = True
            self._window_surface_y = new_y
            # Find the top edge to get bounds for walking
            for e in self._window_detector.edges:
                if e.edge_type == "top" and e.window_title == edge.window_title:
                    self._window_edge = e
                    break
            self._window.move_to(self._window.x(), new_y)
            self._walk_direction = random.choice([-1, 1])
            self.transition(PetState.WALKING_ON_WINDOW)
            return

        # Reached the bottom — fall off
        if new_y >= edge_bottom:
            self._climb_timer.stop()
            self._climb_edge = None
            if self._physics is not None:
                self.transition(PetState.FALLING)
                self._physics.start_falling(0, 0)
            else:
                self.transition(PetState.IDLE)
            return

        # Position pet against the edge
        if edge.edge_type == "left":
            target_x = edge.x - SPRITE_SIZE
        else:
            target_x = edge.x + edge.width
        self._window.move_to(target_x, new_y)

    def on_landed_on_window(self, surface_y: int):
        """Physics engine signals the pet landed on a window title bar."""
        self._on_window_surface = True
        self._window_surface_y = surface_y
        # Find which edge we landed on
        if self._window_detector is not None:
            pet_cx = self._window.x() + SPRITE_SIZE // 2
            for e in self._window_detector.edges:
                if e.edge_type == "top" and e.x <= pet_cx <= e.x + e.width:
                    if abs((e.y - SPRITE_SIZE) - surface_y) < 5:
                        self._window_edge = e
                        break
        self._walk_direction = random.choice([-1, 1])
        self.transition(PetState.WALKING_ON_WINDOW)

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
        self._on_window_surface = False
        self._window_edge = None
        self._climb_edge = None
        self._target_edge = None
        self._walk_target_x = None
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
