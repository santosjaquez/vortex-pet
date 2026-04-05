"""
Vortex Desktop Pet — Mood System

Tracks emotional state based on session events.
Mood affects animation choices and AI response tone.
"""

import time
from dataclasses import dataclass, field
from enum import Enum


class Mood(Enum):
    ECSTATIC = "ecstatic"      # many successes, user interaction
    HAPPY = "happy"            # default good state
    NEUTRAL = "neutral"        # starting state
    BORED = "bored"            # long idle, no events
    GRUMPY = "grumpy"          # errors, failures
    SLEEPY = "sleepy"          # very long idle


@dataclass
class MoodState:
    """Tracks mood with a numerical score and event history."""
    score: float = 50.0        # 0-100 scale. 50=neutral, >70=happy, >90=ecstatic, <30=grumpy, <15=bored
    last_event_time: float = field(default_factory=time.time)
    events_count: int = 0
    errors_count: int = 0
    successes_count: int = 0
    pets_count: int = 0

    @property
    def mood(self) -> Mood:
        idle_secs = time.time() - self.last_event_time
        if idle_secs > 300:  # 5 min idle
            return Mood.SLEEPY
        if idle_secs > 120:  # 2 min idle
            return Mood.BORED
        if self.score >= 90:
            return Mood.ECSTATIC
        if self.score >= 65:
            return Mood.HAPPY
        if self.score >= 35:
            return Mood.NEUTRAL
        return Mood.GRUMPY

    def on_success(self):
        """Tool completed successfully or session stop."""
        self.score = min(100, self.score + 8)
        self.successes_count += 1
        self.events_count += 1
        self.last_event_time = time.time()

    def on_error(self):
        """Tool failed."""
        self.score = max(0, self.score - 15)
        self.errors_count += 1
        self.events_count += 1
        self.last_event_time = time.time()

    def on_tool_use(self):
        """Any tool was used (activity)."""
        self.score = min(100, self.score + 3)
        self.events_count += 1
        self.last_event_time = time.time()

    def on_petted(self):
        """User petted Vortex."""
        self.score = min(100, self.score + 12)
        self.pets_count += 1
        self.last_event_time = time.time()

    def on_session_start(self):
        """New coding session started."""
        self.score = min(100, self.score + 10)
        self.last_event_time = time.time()

    def decay(self):
        """Called periodically to slowly drift toward neutral."""
        if self.score > 55:
            self.score -= 0.5
        elif self.score < 45:
            self.score += 0.3

    def summary(self) -> str:
        """Return a text summary of the session for AI context."""
        return (
            f"Mood: {self.mood.value} (score {self.score:.0f}/100). "
            f"Session: {self.events_count} events, "
            f"{self.successes_count} successes, "
            f"{self.errors_count} errors, "
            f"{self.pets_count} pets received."
        )
