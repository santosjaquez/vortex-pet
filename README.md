# Vortex Desktop Pet

An AI-powered desktop pet (axolotl) that integrates with [Claude Code](https://claude.ai/code) via hooks. Vortex lives as a transparent overlay on your desktop — it watches your workflow, reacts to your coding sessions, chats with you, searches the web, and proactively comments on what's happening.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.x-green)
![Gemma 4](https://img.shields.io/badge/AI-Gemma%204%20E2B-orange)
![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-purple)
![Platform](https://img.shields.io/badge/Platform-Linux%20(X11)-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

### Desktop Pet
- Animated kawaii axolotl sprite overlay (transparent, always-on-top, draggable)
- Physics engine with gravity, bounce, and throw mechanics
- Autonomous behaviors: idle, walk, sleep cycle with random transitions
- Window interaction: climbs window edges and walks on title bars (Shimeji-style)
- Speech bubbles with contextual messages
- System tray icon with controls (show/hide, wake up, reset position, quit)
- Click to pet, double-click to chat, drag and throw

### AI Brain (Gemma 4 E2B via Ollama)
- **Contextual comments**: reacts to what you're doing in Claude Code with specific, helpful observations
- **Chat window**: double-click Vortex to open a conversational chat with memory (last 20 messages)
- **Web search**: ask Vortex to search the web (DuckDuckGo, no API key needed)
- **URL reading**: paste a URL and Vortex will fetch and summarize the content
- **Screen reading**: ask Vortex to look at your screen (OCR via Tesseract)
- **Thinking mode**: say "piensa" or "analiza" for deeper reasoning
- **Proactive behavior**: Vortex speaks on its own — greets by time of day, comments on idle time, motivates when errors pile up, suggests rest late at night, periodically observes your screen

### Mood System
- Tracks emotional state (0-100 score) based on session events
- States: ecstatic, happy, neutral, bored, grumpy, sleepy
- Successes boost mood, errors lower it, petting boosts it, idle time drifts toward bored/sleepy
- Mood affects AI tone: happy = confident, grumpy = blunt, sleepy = minimal

### Claude Code Integration
- Real-time reactions to tool use, errors, task completion via async hooks
- AI-generated comments based on file names, commands, and error context
- Non-blocking: hooks are async, never slow down Claude Code

## Requirements

- **OS**: Linux with X11 (tested on Zorin OS 18 / Ubuntu 24.04)
- **Python**: 3.12+
- **PyQt6**: `sudo apt install python3-pyqt6`
- **Ollama**: Local LLM runtime (installed automatically)
- **Gemma 4 E2B**: ~7.2 GB download, runs on GPU (NVIDIA 8GB+ VRAM) or CPU
- **Tesseract OCR**: `sudo apt install tesseract-ocr tesseract-ocr-spa` (for screen reading)
- **wmctrl**: `sudo apt install wmctrl` (for window detection)

## Installation

```bash
git clone https://github.com/santosjaquez/vortex-pet.git
cd vortex-pet
bash install.sh
```

The installer will:
1. Install PyQt6 if needed
2. Generate placeholder sprites
3. Install a `.desktop` entry (app menu + desktop shortcut)
4. Configure Claude Code hooks in `~/.claude/settings.json`

### Ollama + Gemma 4 Setup

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Download Gemma 4 E2B
ollama pull gemma4:e2b

# Install OCR and window detection
sudo apt install tesseract-ocr tesseract-ocr-spa wmctrl
```

## Usage

```bash
cd ~/vortex-pet && python3 -m vortex
```

Or launch **"Vortex"** from your application menu or desktop icon.

### Interactions

| Action | Effect |
|---|---|
| **Click** | Pet Vortex (boosts mood) |
| **Double-click** | Open/close chat window |
| **Drag + release** | Throw Vortex (physics: gravity + bounce) |
| **Right-click** | Context menu (Quit) |
| **System tray** | Show/Hide, Wake Up, Reset Position, Quit |

### Chat Commands

| What you type | What Vortex does |
|---|---|
| Normal text | Conversational reply (remembers context) |
| "busca X" / "google X" | Searches the web and summarizes results |
| Paste a URL | Fetches the page and discusses content |
| "mira mi pantalla" | Takes screenshot, OCR, and comments |
| "piensa sobre X" / "analiza" | Deep thinking mode (slower, better reasoning) |

### Proactive Comments

Vortex speaks on its own without being asked:
- **Startup greeting** based on time of day
- **Idle observations** every ~90 seconds
- **Screen scanning** every ~3 minutes (comments if content changed)
- **Late night reminders** after 11 PM
- **Mood reactions**: motivates when grumpy, celebrates when ecstatic
- **Session summaries** every 20 Claude Code events

## Architecture

```
Claude Code ──[async hooks]──→ hook_bridge.sh ──→ /tmp/vortex.sock
                                                        |
                                                        v
                                                  VortexApp (PyQt6)
                                                  ├── EventRouter (QLocalServer)
                                                  ├── StateMachine (11 states FSM)
                                                  ├── PhysicsEngine (gravity/bounce)
                                                  ├── SpriteRenderer (QTimer + QPixmap)
                                                  ├── SpeechBubble (overlay widget)
                                                  ├── PetWindow (transparent overlay)
                                                  ├── ChatWindow (mini chat panel)
                                                  ├── AiBrain (Gemma 4 via Ollama)
                                                  ├── MoodState (emotional tracker)
                                                  ├── ProactiveBrain (autonomous comments)
                                                  ├── WindowDetector (wmctrl polling)
                                                  ├── WebSearch (DuckDuckGo + URL fetch)
                                                  └── TrayIcon (system tray)
```

## Project Structure

```
vortex-pet/
├── vortex/
│   ├── app.py               # Application bootstrap and wiring
│   ├── pet_window.py         # Transparent overlay widget
│   ├── sprite_renderer.py    # Animation engine (QTimer + QPixmap)
│   ├── speech_bubble.py      # Floating speech bubbles with auto-dismiss
│   ├── state_machine.py      # FSM: 11 states, autonomous behavior
│   ├── physics.py            # Gravity, bounce, screen edge detection
│   ├── event_router.py       # Unix socket server for Claude Code hooks
│   ├── window_detector.py    # X11 window geometry polling (wmctrl)
│   ├── ai_brain.py           # Gemma 4 E2B integration via Ollama
│   ├── mood.py               # Emotional state tracker
│   ├── proactive.py          # Autonomous comment generation
│   ├── web_search.py         # DuckDuckGo search + URL fetching
│   ├── chat_window.py        # Mini chat panel UI
│   ├── tray_icon.py          # System tray integration
│   ├── config.py             # Constants and paths
│   └── assets/
│       ├── sprites/          # PNG sprite frames (128x128, 10 animations)
│       ├── sprites.json      # Animation metadata
│       └── icon.png          # Tray/desktop icon (64x64)
├── hook_bridge.sh            # Claude Code hook bridge script
├── generate_placeholders.py  # Kawaii axolotl sprite generator (QPainter)
├── install.sh                # Installer (deps, hooks, desktop entry)
├── vortex.desktop            # XDG desktop entry
├── LICENSE                   # MIT License
└── README.md
```

## GPU Usage

Gemma 4 E2B uses ~7.3 GB VRAM when loaded. Ollama automatically unloads it after 5 minutes of inactivity, freeing VRAM for other tasks.

| State | VRAM | GPU Power |
|---|---|---|
| Idle (model unloaded) | ~64 MiB (Xorg only) | ~16W |
| Active (generating) | ~7.3 GB | ~30-35W |
| After 5 min idle | Auto-unloaded | ~16W |

To reduce VRAM usage, you can lower the context window:
```bash
# In Ollama, set lower context (default 4096)
OLLAMA_CONTEXT_LENGTH=2048
```

## Privacy

Everything runs 100% locally:
- **Gemma 4 E2B**: runs on your GPU via Ollama (localhost:11434)
- **Tesseract OCR**: local processing, screenshots deleted immediately
- **Web search**: DuckDuckGo (no account, no tracking cookies)
- No API keys, no cloud services, no telemetry

## License

MIT
