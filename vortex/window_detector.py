"""
Vortex Desktop Pet — Window Detector

Polls wmctrl to get visible window geometries on X11.
Provides edge data (title bars, side edges) for physics collision.
"""

import subprocess
from dataclasses import dataclass
from PyQt6.QtCore import QObject, QTimer, pyqtSignal


TITLE_BAR_HEIGHT = 37  # typical GNOME CSD title bar height
POLL_INTERVAL_MS = 500  # poll every 500ms


@dataclass
class WindowRect:
    """A detected window's frame geometry."""
    wid: int
    x: int
    y: int
    width: int
    height: int
    title: str


@dataclass
class Edge:
    """A walkable/climbable edge segment."""
    x: int
    y: int
    width: int
    height: int
    edge_type: str  # "top", "left", "right"
    window_title: str


class WindowDetector(QObject):
    """Periodically scans X11 windows and provides edge collision data."""

    windows_updated = pyqtSignal()  # emitted after each scan

    def __init__(self, parent=None):
        super().__init__(parent)
        self._windows: list[WindowRect] = []
        self._edges: list[Edge] = []
        self._own_wids: set[int] = set()  # Vortex's own window IDs to exclude

        self._timer = QTimer(self)
        self._timer.setInterval(POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._poll)

    @property
    def windows(self) -> list[WindowRect]:
        return self._windows

    @property
    def edges(self) -> list[Edge]:
        return self._edges

    def start(self):
        """Start polling for windows."""
        self._poll()  # initial scan
        self._timer.start()

    def stop(self):
        """Stop polling."""
        self._timer.stop()

    def set_own_wids(self, wids: set[int]):
        """Set window IDs belonging to Vortex (to exclude from detection)."""
        self._own_wids = wids

    def _poll(self):
        """Run wmctrl -lG and parse results."""
        try:
            result = subprocess.run(
                ["wmctrl", "-lG"],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode != 0:
                return
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return

        windows = []
        for line in result.stdout.strip().splitlines():
            parts = line.split(None, 7)
            if len(parts) < 7:
                continue
            try:
                wid = int(parts[0], 16)
                desktop = int(parts[1])
                x, y, w, h = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
            except ValueError:
                continue

            # Skip desktop window and Vortex's own windows
            if desktop == -1:
                continue
            if wid in self._own_wids:
                continue
            # Skip tiny windows (likely panels, trays, etc.)
            if w < 100 or h < 100:
                continue

            title = parts[7] if len(parts) > 7 else ""
            windows.append(WindowRect(wid, x, y, w, h, title))

        self._windows = windows
        self._build_edges()
        self.windows_updated.emit()

    def _build_edges(self):
        """Build walkable/climbable edges from detected windows."""
        edges = []
        for win in self._windows:
            # Top edge (title bar) — walkable surface
            edges.append(Edge(
                x=win.x,
                y=win.y,
                width=win.width,
                height=TITLE_BAR_HEIGHT,
                edge_type="top",
                window_title=win.title,
            ))
            # Left edge — climbable
            edges.append(Edge(
                x=win.x,
                y=win.y + TITLE_BAR_HEIGHT,
                width=8,  # thin climbable strip
                height=win.height - TITLE_BAR_HEIGHT,
                edge_type="left",
                window_title=win.title,
            ))
            # Right edge — climbable
            edges.append(Edge(
                x=win.x + win.width - 8,
                y=win.y + TITLE_BAR_HEIGHT,
                width=8,
                height=win.height - TITLE_BAR_HEIGHT,
                edge_type="right",
                window_title=win.title,
            ))
        self._edges = edges

    def find_surface_below(self, pet_x: int, pet_y: int, pet_width: int) -> tuple[int, str] | None:
        """Find the highest walkable surface directly below the pet.

        Returns (surface_y, edge_type) or None if only the desktop floor is below.
        Checks if the pet's horizontal center overlaps with any top edge.
        """
        pet_center_x = pet_x + pet_width // 2
        pet_bottom = pet_y + pet_width  # pet is square (SPRITE_SIZE x SPRITE_SIZE)

        best_y = None
        best_type = None

        for edge in self._edges:
            if edge.edge_type != "top":
                continue
            # Check horizontal overlap: pet center must be within the edge
            if edge.x <= pet_center_x <= edge.x + edge.width:
                surface_y = edge.y - pet_width  # pet sits ON TOP of the edge
                # Surface must be below the pet's current top but above the pet's bottom
                # (i.e., the pet is falling toward it)
                if surface_y >= pet_y:
                    if best_y is None or surface_y < best_y:
                        best_y = surface_y
                        best_type = edge.edge_type

        return (best_y, best_type) if best_y is not None else None

    def find_climbable_edge(self, pet_x: int, pet_y: int, pet_width: int) -> Edge | None:
        """Find a climbable side edge that the pet is overlapping with.

        Returns the Edge if the pet is at a window's side edge, or None.
        The pet must be vertically within the edge range and horizontally touching it.
        """
        pet_right = pet_x + pet_width
        pet_bottom = pet_y + pet_width

        for edge in self._edges:
            if edge.edge_type not in ("left", "right"):
                continue
            # Vertical overlap check
            if pet_bottom < edge.y or pet_y > edge.y + edge.height:
                continue
            # Horizontal proximity check
            if edge.edge_type == "left":
                # Pet's right side touches the window's left edge
                if abs(pet_right - edge.x) < 15:
                    return edge
            elif edge.edge_type == "right":
                # Pet's left side touches the window's right edge
                if abs(pet_x - (edge.x + edge.width)) < 15:
                    return edge
        return None
