"""
Vortex Desktop Pet — Event Router

Unix socket server that receives JSON events from Claude Code hooks
(forwarded by hook_bridge.sh) and emits them as Qt signals for the pet
to react to.
"""

import json
import logging
import os

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

logger = logging.getLogger(__name__)

SOCKET_PATH = "/tmp/vortex.sock"


class EventRouter(QObject):
    """Listens on a Unix socket for JSON hook events from Claude Code."""

    # Signal: (event_name: str, parsed_data: dict)
    hook_event = pyqtSignal(str, dict)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_new_connection)
        # Track active connections and their read buffers to prevent GC
        self._connections: list[QLocalSocket] = []
        self._buffers: dict[QLocalSocket, bytes] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> bool:
        """Begin listening on the Unix socket.

        Returns True on success, False if the socket is already in use.
        """
        # Remove a stale socket file left over from a previous crash
        if os.path.exists(SOCKET_PATH):
            try:
                os.unlink(SOCKET_PATH)
            except OSError:
                logger.warning("Could not remove stale socket %s", SOCKET_PATH)

        if not self._server.listen(SOCKET_PATH):
            logger.error(
                "EventRouter: failed to listen on %s — %s",
                SOCKET_PATH,
                self._server.errorString(),
            )
            return False

        logger.info("EventRouter: listening on %s", SOCKET_PATH)
        return True

    def stop(self) -> None:
        """Close the server and clean up the socket file."""
        self._server.close()

        # Disconnect any lingering clients
        for sock in list(self._connections):
            sock.disconnectFromServer()
        self._connections.clear()
        self._buffers.clear()

        if os.path.exists(SOCKET_PATH):
            try:
                os.unlink(SOCKET_PATH)
            except OSError:
                pass

        logger.info("EventRouter: stopped")

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _on_new_connection(self) -> None:
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            if socket is None:
                continue

            self._connections.append(socket)
            self._buffers[socket] = b""

            # Buffer incoming data
            socket.readyRead.connect(lambda s=socket: self._on_ready_read(s))
            # Parse once the sender closes the connection
            socket.disconnected.connect(lambda s=socket: self._on_disconnected(s))

    def _on_ready_read(self, socket: QLocalSocket) -> None:
        """Accumulate incoming bytes in the per-socket buffer."""
        raw: bytes = socket.readAll().data()
        if raw:
            self._buffers[socket] = self._buffers.get(socket, b"") + raw

    def _on_disconnected(self, socket: QLocalSocket) -> None:
        """Client closed — parse the buffered JSON and emit the signal."""
        data = self._buffers.pop(socket, b"")

        # Clean up the connection list
        if socket in self._connections:
            self._connections.remove(socket)
        socket.deleteLater()

        if not data:
            return

        try:
            payload = json.loads(data.decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, ValueError):
            logger.debug("EventRouter: ignoring malformed JSON (%d bytes)", len(data))
            return

        if not isinstance(payload, dict):
            return

        parsed = self._parse_event(payload)
        event_name = parsed.get("hook_event_name", "unknown")
        import sys
        print(f"[Vortex Hook] {event_name}: {parsed.get('tool_name', '')}", file=sys.stderr, flush=True)
        self.hook_event.emit(event_name, parsed)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_event(data: dict) -> dict:
        """Extract the fields we care about from a Claude Code hook payload."""
        parsed: dict = {}

        parsed["hook_event_name"] = data.get("hook_event_name", "unknown")

        if "session_id" in data:
            parsed["session_id"] = data["session_id"]

        if "tool_name" in data:
            parsed["tool_name"] = data["tool_name"]

        if "tool_input" in data and isinstance(data["tool_input"], dict):
            parsed["tool_input"] = data["tool_input"]

        if "tool_response" in data:
            resp = str(data["tool_response"])
            parsed["tool_response"] = resp[:200]

        return parsed
