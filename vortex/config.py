from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
ASSETS_DIR = Path(__file__).parent / "assets"
SPRITES_DIR = ASSETS_DIR / "sprites"
SPRITES_JSON = ASSETS_DIR / "sprites.json"
SOCKET_PATH = "/tmp/vortex.sock"

# Sprite
SPRITE_SIZE = 128

# Physics
TICK_MS = 16          # ~60fps physics
GRAVITY = 0.6         # pixels/tick²
BOUNCE_DAMPING = 0.5
GROUND_THRESHOLD = 1.0  # stop bouncing below this velocity
FLOOR_OFFSET = 48     # pixels above screen bottom for taskbar

# Animation
FRAME_MS = 100        # default 10fps animation

# Behavior
IDLE_MIN_MS = 3000
IDLE_MAX_MS = 8000
WALK_MIN_MS = 2000
WALK_MAX_MS = 5000
WALK_SPEED = 1.5      # pixels per tick
SLEEP_MIN_MS = 30000
SLEEP_MAX_MS = 60000

# Speech bubble
BUBBLE_DURATION_MS = 3500
BUBBLE_MAX_WIDTH = 250
BUBBLE_FADE_MS = 500

# Window interaction
CLIMB_SPEED = 1.0     # pixels per tick when climbing
WALK_ON_WINDOW_PROB = 0.15  # probability of walking toward a window edge
