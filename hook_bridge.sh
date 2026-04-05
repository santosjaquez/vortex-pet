#!/usr/bin/env bash
# Vortex Desktop Pet — Claude Code Hook Bridge
# Reads hook event JSON from stdin and sends it to the Vortex app via Unix socket.
# Fails silently if Vortex is not running (non-blocking for Claude Code).
#
# Usage: echo '{"hook_event_name":"PostToolUse"}' | ./hook_bridge.sh
# Make executable: chmod +x hook_bridge.sh

SOCK="/tmp/vortex.sock"

# Exit silently if socket doesn't exist (Vortex not running)
[ -S "$SOCK" ] || exit 0

# Read stdin and send to socket using Python's built-in socket module
# (avoids dependency on socat/netcat)
python3 -c "
import socket, sys
try:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(2)
    s.connect('$SOCK')
    s.sendall(sys.stdin.buffer.read())
    s.close()
except Exception:
    pass
" 2>/dev/null

exit 0
