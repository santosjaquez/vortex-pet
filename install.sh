#!/usr/bin/env bash
# Vortex Desktop Pet — Installer
# Installs dependencies, generates placeholders, sets up desktop entry,
# and merges Claude Code hooks into ~/.claude/settings.json.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETTINGS_FILE="$HOME/.claude/settings.json"
DESKTOP_SRC="$SCRIPT_DIR/vortex.desktop"
DESKTOP_DST="$HOME/.local/share/applications/vortex.desktop"
HOOK_CMD="cat | $SCRIPT_DIR/hook_bridge.sh"

echo "=== Vortex Desktop Pet Installer ==="
echo ""

# ------------------------------------------------------------------
# 1. Check for python3-pyqt6, install if missing
# ------------------------------------------------------------------
echo "[1/5] Checking for python3-pyqt6..."
if dpkg -s python3-pyqt6 &>/dev/null; then
    echo "      python3-pyqt6 is already installed."
else
    echo "      python3-pyqt6 not found. Installing..."
    if sudo -n true 2>/dev/null; then
        sudo apt-get install -y python3-pyqt6
    else
        echo "      ERROR: passwordless sudo is not active."
        echo "      Please run: sudo apt-get install -y python3-pyqt6"
        echo "      Then re-run this installer."
        exit 1
    fi
fi

# ------------------------------------------------------------------
# 2. Generate placeholder sprites if they don't exist
# ------------------------------------------------------------------
echo "[2/5] Checking for placeholder sprites..."
SPRITES_DIR="$SCRIPT_DIR/vortex/assets/sprites"
if [ -d "$SPRITES_DIR" ] && [ "$(ls -A "$SPRITES_DIR" 2>/dev/null)" ]; then
    echo "      Sprites directory already has files, skipping generation."
else
    echo "      Generating placeholder sprites..."
    python3 "$SCRIPT_DIR/generate_placeholders.py"
    echo "      Done."
fi

# ------------------------------------------------------------------
# 3. Make hook_bridge.sh executable
# ------------------------------------------------------------------
echo "[3/5] Making hook_bridge.sh executable..."
chmod +x "$SCRIPT_DIR/hook_bridge.sh"
echo "      Done."

# ------------------------------------------------------------------
# 4. Copy vortex.desktop to ~/.local/share/applications/
# ------------------------------------------------------------------
echo "[4/5] Installing desktop entry..."
mkdir -p "$(dirname "$DESKTOP_DST")"
cp "$DESKTOP_SRC" "$DESKTOP_DST"
echo "      Installed to $DESKTOP_DST"

# ------------------------------------------------------------------
# 5. Merge hooks into ~/.claude/settings.json
# ------------------------------------------------------------------
echo "[5/5] Merging Claude Code hooks into settings.json..."
mkdir -p "$(dirname "$SETTINGS_FILE")"

python3 -c "
import json
from pathlib import Path

settings_path = Path.home() / '.claude' / 'settings.json'
hook_cmd = '$HOOK_CMD'

if settings_path.exists():
    with open(settings_path, 'r') as f:
        settings = json.load(f)
else:
    settings = {}

if 'hooks' not in settings:
    settings['hooks'] = {}

hooks = settings['hooks']
hook_events = ['PostToolUse', 'PostToolUseFailure', 'Stop', 'Notification']

def make_hook_entry(cmd):
    return {'type': 'command', 'command': cmd, 'async': True}

changes = []
for event in hook_events:
    if event not in hooks:
        hooks[event] = []
    existing_cmds = [h.get('command', '') for h in hooks[event]]
    if hook_cmd not in existing_cmds:
        hooks[event].append(make_hook_entry(hook_cmd))
        changes.append(event)

with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=2)
    f.write('\n')

if changes:
    print(f'      Added hooks for: {\", \".join(changes)}')
else:
    print('      All hooks already present, no changes needed.')
"

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
echo ""
echo "=== Installation complete ==="
echo ""
echo "  Desktop entry:  $DESKTOP_DST"
echo "  Hook bridge:    $SCRIPT_DIR/hook_bridge.sh (executable)"
echo "  Settings file:  $SETTINGS_FILE"
echo "  Sprites:        $SPRITES_DIR/"
echo ""
echo "  To launch Vortex:"
echo "    cd $SCRIPT_DIR && python3 -m vortex"
echo "  Or use the 'Vortex' entry in your application menu."
echo ""
