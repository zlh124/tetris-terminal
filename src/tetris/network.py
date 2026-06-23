"""WebSocket client for multiplayer Tetris.

Wraps the ``websockets.sync.client`` API for integration with the
synchronous curses-based game loop.
"""

from __future__ import annotations

import json
from typing import Any

from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect, ClientConnection

from .enums import WebClientMsgType


class NetworkClient:
    """Synchronous WebSocket client for 1v1 Tetris.

    Provides a non-blocking receive API so the main game loop can poll
    for incoming messages without stalling on I/O.

    Attributes:
        player_id: The ID assigned by the server after handshake.
        opponent_id: The opponent's ID (set when a match is found).
    """

    def __init__(self) -> None:
        self._ws: ClientConnection | None = None
        self.player_id: str = ""
        self.opponent_id: str = ""

    @property
    def connected(self) -> bool:
        """Return ``True`` if the WebSocket connection is still open."""
        return self._ws is not None

    def handshake(self, host: str, port: int, version: str) -> None:
        """Connect to the server and perform the version handshake.

        Args:
            host: Server hostname or IP address.
            port: Server TCP port.
            version: Client version string to send.

        Raises:
            RuntimeError: If the server rejects the connection (e.g. version
                mismatch).
        """
        self._ws = connect(f"ws://{host}:{port}")
        self._ws.send(
            json.dumps({"type": WebClientMsgType.HELLO, "data": {"version": version}})
        )
        msg: dict[str, Any] = json.loads(self._ws.recv())
        if msg.get("type") == WebClientMsgType.ERROR:
            raise RuntimeError(msg["data"]["message"])
        self.player_id = msg["data"]["your_id"]

    def wait_for_match(self) -> str:
        """Block until a ``match_found`` message arrives.

        Returns:
            The opponent's player ID.

        Raises:
            RuntimeError: If not connected, or if the server is full.
        """
        if self._ws is None:
            raise RuntimeError("Not connected")
        while True:
            msg: dict[str, Any] = json.loads(self._ws.recv())
            if msg.get("type") == WebClientMsgType.MATCH_FOUND:
                self.opponent_id = msg["data"]["opponent_id"]
                return self.opponent_id
            if msg.get("type") == WebClientMsgType.SERVER_FULL:
                raise RuntimeError("Server is full")

    def send(self, data: dict[str, Any]) -> None:
        """Send a JSON-serialisable dict to the server.

        Args:
            data: Message payload (will be serialised to JSON).
        """
        if self._ws is None:
            return
        try:
            self._ws.send(json.dumps(data))
        except ConnectionClosed:
            self._ws = None

    def recv(self, timeout: float = 0) -> dict[str, Any] | None:
        """Non-blocking receive.

        Returns a parsed JSON dict, or ``None`` when no message is available
        or the connection has been closed.

        Args:
            timeout: Seconds to wait for a message (``0`` = non-blocking).

        Returns:
            Parsed message dict, or ``None``.
        """
        if self._ws is None:
            return None
        try:
            return json.loads(self._ws.recv(timeout=timeout))
        except TimeoutError:
            return None
        except ConnectionClosed:
            self._ws = None
            return None

    def close(self) -> None:
        """Close the WebSocket connection gracefully."""
        if self._ws is not None:
            self._ws.close()
            self._ws = None
