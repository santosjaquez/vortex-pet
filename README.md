# Vortex Desktop Pet

A graphical desktop pet (axolotl) that integrates with [Claude Code](https://claude.ai/code) via hooks. Vortex lives as a transparent overlay on your desktop, reacting in real-time to your coding sessions.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.x-green)
![Platform](https://img.shields.io/badge/Platform-Linux%20(X11)-lightgrey)

## Features

- Animated axolotl sprite overlay (transparent, always-on-top, draggable)
- Physics engine with gravity and bounce
- Autonomous behaviors: idle, walk, sleep
- Reacts to Claude Code events via hooks (typing, celebrating, sad on errors)
- Speech bubbles with contextual messages
- System tray icon with controls
- Click to pet, drag and throw

## Requirements

- Python 3.12+
- PyQt6 (`sudo apt install python3-pyqt6`)
- Linux with X11 (tested on Zorin OS 18 / Ubuntu 24.04)

## Installation

```bash
git clone https://github.com/ericksantosjaquez/vortex-pet.git
cd vortex-pet
bash install.sh
```

The installer will:
1. Install PyQt6 if needed
2. Generate placeholder sprites
3. Install a `.desktop` entry
4. Configure Claude Code hooks in `~/.claude/settings.json`

## Usage

```bash
cd vortex-pet
python3 -m vortex
```

Or launch "Vortex" from your application menu.

## How it works

```
Claude Code ──[hooks]──→ hook_bridge.sh ──→ /tmp/vortex.sock ──→ Vortex App (PyQt6)
```

Claude Code fires async hooks on events (tool use, errors, completion). The hook bridge script pipes JSON to Vortex via a Unix socket. Vortex's state machine maps events to animations and speech bubbles.

## Claude Code Hook Events

| Event | Pet Reaction |
|---|---|
| Tool use (Bash/Edit/Write) | Typing animation |
| Tool use failure | Sad animation |
| Task completed | Happy/celebrating |
| Session start | Celebrating |
| Session end | Sleeping |

## Project Structure

```
vortex-pet/
├── vortex/
│   ├── app.py               # Application bootstrap and wiring
│   ├── pet_window.py         # Transparent overlay widget
│   ├── sprite_renderer.py    # Animation engine
│   ├── speech_bubble.py      # Floating speech bubbles
│   ├── state_machine.py      # FSM behavior brain
│   ├── physics.py            # Gravity and bounce
│   ├── event_router.py       # Unix socket server
│   ├── tray_icon.py          # System tray integration
│   └── assets/sprites/       # PNG sprite frames (128x128)
├── hook_bridge.sh            # Claude Code hook bridge
├── generate_placeholders.py  # Placeholder sprite generator
└── install.sh                # Installer
```

## License

MIT
