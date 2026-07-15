"""Integration tests for the tetris-terminal WebSocket server."""

import asyncio
import json
import logging
from typing import Union

import pytest
import websockets

from tetris.enums import WebClientMsgType
from tetris.multiplay.server import main as server_main
from tetris.utils import get_version

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT: float = 5.0  # seconds — each recv MUST complete within this


async def _recv_json(
    ws: websockets.ClientConnection, *, timeout: float = DEFAULT_TIMEOUT
) -> dict:
    """Receive one JSON message with a mandatory timeout.

    Args:
        ws: The WebSocket connection.
        timeout: Maximum time to wait in seconds.

    Returns:
        Parsed JSON dict.

    Raises:
        asyncio.TimeoutError: If *timeout* is exceeded.
    """
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    return json.loads(raw)


async def _recv_raw(
    ws: websockets.ClientConnection, *, timeout: float = DEFAULT_TIMEOUT
) -> str | bytes:
    """Receive one raw message with a mandatory timeout.

    Args:
        ws: The WebSocket connection.
        timeout: Maximum time to wait in seconds.

    Returns:
        Raw message string.

    Raises:
        asyncio.TimeoutError: If *timeout* is exceeded.
    """
    return await asyncio.wait_for(ws.recv(), timeout=timeout)


async def _connect(
    port: int, *, version: str | None = None
) -> tuple[websockets.ClientConnection, Union[str, dict]]:
    """Connect to a server and perform the version handshake.

    Args:
        port: Server port.
        version: Client version string (default: installed version).

    Returns:
        A tuple of ``(websocket, data)``. On success *data* is the
        player ID string; on error (e.g. ``ERROR``, ``SERVER_FULL``) it
        is the raw message dict.
    """
    if version is None:
        version = get_version()
    ws = await websockets.connect(f"ws://127.0.0.1:{port}")
    await ws.send(
        json.dumps({"type": WebClientMsgType.HELLO, "data": {"version": version}})
    )
    msg = await _recv_json(ws)
    if msg.get("type") == WebClientMsgType.HELLO_OK:
        return ws, msg["data"]["your_id"]
    return ws, msg


# ---------------------------------------------------------------------------
# Matchmaking
# ---------------------------------------------------------------------------


class TestMatchmaking:
    """Tests for the 1v1 matchmaking queue."""

    async def test_two_players_match(self, server: int) -> None:
        """Two connecting players should be paired, receive each other's ID,
        and share the same random seed."""
        ws1, id1 = await _connect(server)
        ws2, id2 = await _connect(server)

        msg1 = await _recv_json(ws1)
        msg2 = await _recv_json(ws2)

        assert msg1["type"] == WebClientMsgType.MATCH_FOUND
        assert msg1["data"]["opponent_id"] == id2
        assert "seed" in msg1["data"]
        assert isinstance(msg1["data"]["seed"], int)

        assert msg2["type"] == WebClientMsgType.MATCH_FOUND
        assert msg2["data"]["opponent_id"] == id1

        # Both players must get the same seed
        assert msg1["data"]["seed"] == msg2["data"]["seed"]

    async def test_concurrent_rooms(self, server: int) -> None:
        """Four players should form two independent rooms with different seeds."""
        ws1, _ = await _connect(server)
        ws2, _ = await _connect(server)
        ws3, _ = await _connect(server)
        ws4, _ = await _connect(server)

        msgs: list[dict] = []
        for ws in (ws1, ws2, ws3, ws4):
            msg = await _recv_json(ws)
            assert msg["type"] == WebClientMsgType.MATCH_FOUND
            msgs.append(msg)

        # First room: ws1 and ws2 share seed
        assert msgs[0]["data"]["seed"] == msgs[1]["data"]["seed"]
        # Second room: ws3 and ws4 share seed
        assert msgs[2]["data"]["seed"] == msgs[3]["data"]["seed"]
        # Different rooms have (probably) different seeds
        assert msgs[0]["data"]["seed"] != msgs[2]["data"]["seed"]

    async def test_server_full_rejects(self, server_full: int) -> None:
        """The third player should be rejected when max_rooms=1."""
        ws1, _ = await _connect(server_full)
        ws2, _ = await _connect(server_full)

        # first two matched
        msg = await _recv_json(ws1)
        assert msg["type"] == WebClientMsgType.MATCH_FOUND

        # third connects; server sends HELLO_OK then SERVER_FULL.
        # HELLO_OK was consumed by _connect; read the next message.
        ws3, _ = await _connect(server_full)
        msg3 = await _recv_json(ws3)
        assert msg3["type"] == WebClientMsgType.SERVER_FULL

    async def test_waiting_queue(self, server: int) -> None:
        """A single player should wait until a second arrives."""
        ws1, _ = await _connect(server)

        # ws1 is waiting — should receive nothing within a short timeout
        with pytest.raises(asyncio.TimeoutError):
            await _recv_raw(ws1, timeout=0.5)

        ws2, _ = await _connect(server)
        msg1 = await _recv_json(ws1)
        msg2 = await _recv_json(ws2)
        assert msg1["type"] == WebClientMsgType.MATCH_FOUND
        assert msg2["type"] == WebClientMsgType.MATCH_FOUND

    async def test_waiting_disconnect_cleanup(self, server: int) -> None:
        """A player who disconnects while waiting should be cleaned up."""
        ws1, _ = await _connect(server)
        await ws1.close()
        await asyncio.sleep(0.2)  # let server process the disconnect

        ws2, _ = await _connect(server)
        # ws2 should be waiting alone, not instantly matched
        with pytest.raises(asyncio.TimeoutError):
            await _recv_raw(ws2, timeout=0.5)

    async def test_room_ends_frees_slot(self, server_full: int) -> None:
        """Ending a room should free a slot for new players."""
        ws1, _ = await _connect(server_full)
        ws2, _ = await _connect(server_full)

        await _recv_raw(ws1)  # MATCH_FOUND
        await _recv_raw(ws2)  # MATCH_FOUND

        # end the room by disconnecting one player
        await ws1.close()
        await asyncio.sleep(0.2)

        # a new room should be able to form
        ws3, _ = await _connect(server_full)
        ws4, _ = await _connect(server_full)
        msg3 = await _recv_json(ws3)
        msg4 = await _recv_json(ws4)
        assert msg3["type"] == WebClientMsgType.MATCH_FOUND
        assert msg4["type"] == WebClientMsgType.MATCH_FOUND


# ---------------------------------------------------------------------------
# Handshake
# ---------------------------------------------------------------------------


class TestVersionHandshake:
    """Tests for the version negotiation handshake."""

    async def test_version_mismatch_rejected(self, server: int) -> None:
        """A client with a mismatched version should receive an ERROR message."""
        ws, msg = await _connect(server, version="0.0.0")
        assert isinstance(msg, dict), "msg is not a dict"
        assert msg["type"] == WebClientMsgType.ERROR
        assert "mismatch" in msg["data"]["message"]


# ---------------------------------------------------------------------------
# Message relay
# ---------------------------------------------------------------------------


class TestMessageRelay:
    """Tests for in-room message forwarding."""

    async def test_relay_garbage(self, server: int) -> None:
        """A garbage message sent by one player should reach the opponent."""
        ws1, _ = await _connect(server)
        ws2, _ = await _connect(server)

        await _recv_raw(ws1)  # MATCH_FOUND
        await _recv_raw(ws2)  # MATCH_FOUND

        await ws1.send(
            json.dumps({"type": WebClientMsgType.GARBAGE, "data": {"lines": 3}})
        )
        msg = await _recv_json(ws2)
        assert msg == {"type": WebClientMsgType.GARBAGE, "data": {"lines": 3}}


# ---------------------------------------------------------------------------
# Handshake validation
# ---------------------------------------------------------------------------


class TestHandshakeValidation:
    """Tests for malformed first messages being rejected silently."""

    async def test_non_hello_first_message_closes(self, server: int) -> None:
        """A first message that is not ``HELLO`` closes the connection."""
        ws = await websockets.connect(f"ws://127.0.0.1:{server}")
        await ws.send(json.dumps({"type": WebClientMsgType.GARBAGE, "data": {}}))
        with pytest.raises(websockets.ConnectionClosed):
            await asyncio.wait_for(ws.recv(), timeout=2.0)

    async def test_invalid_json_first_message_closes(self, server: int) -> None:
        """A first message that is not valid JSON closes the connection."""
        ws = await websockets.connect(f"ws://127.0.0.1:{server}")
        await ws.send("not-json{")
        with pytest.raises(websockets.ConnectionClosed):
            await asyncio.wait_for(ws.recv(), timeout=2.0)


# ---------------------------------------------------------------------------
# Disconnect handling
# ---------------------------------------------------------------------------


class TestDisconnect:
    """Tests for room cleanup when a player disconnects mid-match."""

    async def test_opponent_disconnected_relayed(self, server: int) -> None:
        """The surviving player is notified when their opponent disconnects."""
        ws1, _ = await _connect(server)
        ws2, _ = await _connect(server)
        await _recv_raw(ws1)  # MATCH_FOUND
        await _recv_raw(ws2)  # MATCH_FOUND

        await ws1.close()
        msg = await _recv_json(ws2)
        assert msg["type"] == WebClientMsgType.OPPONENT_DISCONNECTED


# ---------------------------------------------------------------------------
# Relay edge cases
# ---------------------------------------------------------------------------


class TestRelayValidation:
    """Tests for malformed messages during in-room relay."""

    async def test_invalid_json_during_relay_is_logged(self, server: int) -> None:
        """Invalid JSON from a player is logged and not forwarded."""
        ws1, _ = await _connect(server)
        ws2, _ = await _connect(server)
        await _recv_raw(ws1)  # MATCH_FOUND
        await _recv_raw(ws2)  # MATCH_FOUND

        records: list[logging.LogRecord] = []

        class _ListHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        srv_logger = logging.getLogger("tetris.mulitplay.server")
        handler = _ListHandler(level=logging.WARNING)
        srv_logger.addHandler(handler)
        try:
            await ws1.send("not-json{")
            await asyncio.sleep(0.3)  # let the relay process it
        finally:
            srv_logger.removeHandler(handler)

        assert any("Invalid JSON" in r.getMessage() for r in records)
        # The malformed payload is not forwarded. The relay's JSONDecodeError
        # handler is at the try-level (not per-message), so one bad message
        # aborts the relay, ending the room — the opponent is then notified
        # via OPPONENT_DISCONNECTED rather than receiving the garbage.
        msg = await _recv_json(ws2, timeout=1.0)
        assert msg["type"] == WebClientMsgType.OPPONENT_DISCONNECTED


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestServerCLI:
    """Tests for the ``tetris-server`` CLI argument parsing."""

    def test_main_parses_args_and_invokes_serve(self, monkeypatch) -> None:
        captured: dict = {}

        async def fake_serve(host, port, version, max_rooms=0) -> None:
            captured.update(host=host, port=port, version=version, max_rooms=max_rooms)

        monkeypatch.setattr("tetris.multiplay.server.serve", fake_serve)
        monkeypatch.setattr(
            "sys.argv",
            [
                "tetris-server",
                "--host",
                "1.2.3.4",
                "--port",
                "9999",
                "--max-rooms",
                "3",
            ],
        )
        assert server_main() == 0
        assert captured["host"] == "1.2.3.4"
        assert captured["port"] == 9999
        assert captured["max_rooms"] == 3

    def test_main_defaults(self, monkeypatch) -> None:
        captured: dict = {}

        async def fake_serve(host, port, version, max_rooms=0) -> None:
            captured.update(host=host, port=port, version=version, max_rooms=max_rooms)

        monkeypatch.setattr("tetris.multiplay.server.serve", fake_serve)
        monkeypatch.setattr("sys.argv", ["tetris-server"])
        assert server_main() == 0
        assert captured["host"] == "0.0.0.0"
        assert captured["port"] == 8765
        assert captured["max_rooms"] == 0
