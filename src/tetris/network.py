"""WebSocket client for multiplayer Tetris.

Wraps the ``websockets.sync.client`` API for integration with the
synchronous curses-based game loop.
"""

from __future__ import annotations

import json
from typing import Any

from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect, ClientConnection


class NetworkClient:
    """Synchronous WebSocket client for 1v1 Tetris."""

    def __init__(self) -> None:
        self._ws: ClientConnection | None = None
        self.player_id: str = ""
        self.opponent_id: str = ""

    def handshake(self, host: str, port: int, version: str) -> None:
        """Connect to server and perform version handshake.

        Raises :exc:`RuntimeError` on version mismatch.
        """
        self._ws = connect(f"ws://{host}:{port}")
        self._ws.send(json.dumps({"type": "hello", "data": {"version": version}}))
        msg = json.loads(self._ws.recv())
        if msg.get("type") == "error":
            raise RuntimeError(msg["data"]["message"])
        self.player_id = msg["data"]["your_id"]

    def wait_for_match(self) -> str:
        """Block until a ``match_found`` message arrives.

        Returns the opponent's ID.
        """
        if self._ws is None:
            raise RuntimeError("Not connected")
        while True:
            msg = json.loads(self._ws.recv())
            if msg.get("type") == "match_found":
                self.opponent_id = msg["data"]["opponent_id"]
                return self.opponent_id

    def send(self, data: dict[str, Any]) -> None:
        """Send a JSON message to the server."""
        if self._ws is None:
            return
        try:
            self._ws.send(json.dumps(data))
        except ConnectionClosed:
            self._ws = None

    def recv(self, timeout: float = 0) -> dict[str, Any] | None:
        """Non-blocking receive. Returns a parsed JSON dict, or None."""
        if self._ws is None:
            return None
        try:
            return json.loads(self._ws.recv(timeout=timeout))
        except (TimeoutError, ConnectionClosed):
            return None

    def close(self) -> None:
        if self._ws is not None:
            self._ws.close()
            self._ws = None
