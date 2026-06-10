"""Integration tests for the tetris-terminal WebSocket server."""

import asyncio
import json

import pytest
import websockets

from tetris.enums import WebClientMsgType
from tetris.utils import get_version

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 5.0  # seconds — each recv MUST complete within this


async def _recv_json(ws, *, timeout: float = DEFAULT_TIMEOUT) -> dict:
    """Receive one JSON message with a mandatory timeout."""
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    return json.loads(raw)


async def _recv_raw(ws, *, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Receive one raw message with a mandatory timeout."""
    return await asyncio.wait_for(ws.recv(), timeout=timeout)


async def _connect(port: int, *, version: str | None = None):
    """Connect to *port*, perform the version handshake.

    Returns ``(websocket, your_id)`` on success.
    Returns ``(websocket, msg)`` on error (e.g. ``ERROR``, ``SERVER_FULL``).
    """
    if version is None:
        version = get_version()
    ws = await websockets.connect(f"ws://127.0.0.1:{port}")
    await ws.send(
        json.dumps(
            {"type": WebClientMsgType.HELLO, "data": {"version": version}}
        )
    )
    msg = await _recv_json(ws)
    if msg.get("type") == WebClientMsgType.HELLO_OK:
        return ws, msg["data"]["your_id"]
    return ws, msg


# ---------------------------------------------------------------------------
# Matchmaking
# ---------------------------------------------------------------------------


class TestMatchmaking:
    async def test_two_players_match(self, server: int) -> None:
        ws1, id1 = await _connect(server)
        ws2, id2 = await _connect(server)

        msg1 = await _recv_json(ws1)
        msg2 = await _recv_json(ws2)

        assert msg1["type"] == WebClientMsgType.MATCH_FOUND
        assert msg1["data"]["opponent_id"] == id2
        assert msg2["type"] == WebClientMsgType.MATCH_FOUND
        assert msg2["data"]["opponent_id"] == id1

    async def test_concurrent_rooms(self, server: int) -> None:
        """Four players should form two independent rooms."""
        ws1, _ = await _connect(server)
        ws2, _ = await _connect(server)
        ws3, _ = await _connect(server)
        ws4, _ = await _connect(server)

        for ws in (ws1, ws2, ws3, ws4):
            msg = await _recv_json(ws)
            assert msg["type"] == WebClientMsgType.MATCH_FOUND

    async def test_server_full_rejects(self, server_full: int) -> None:
        ws1, _ = await _connect(server_full)
        ws2, _ = await _connect(server_full)

        # first two matched
        msg = await _recv_json(ws1)
        assert msg["type"] == WebClientMsgType.MATCH_FOUND

        # third gets SERVER_FULL after HELLO_OK
        ws3, _ = await _connect(server_full)
        msg3 = await _recv_json(ws3)
        assert msg3["type"] == WebClientMsgType.SERVER_FULL

    async def test_waiting_queue(self, server: int) -> None:
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
        ws1, _ = await _connect(server)
        await ws1.close()
        await asyncio.sleep(0.2)  # let server process the disconnect

        ws2, _ = await _connect(server)
        # ws2 should be waiting alone, not instantly matched
        with pytest.raises(asyncio.TimeoutError):
            await _recv_raw(ws2, timeout=0.5)

    async def test_room_ends_frees_slot(self, server_full: int) -> None:
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
    async def test_version_mismatch_rejected(self, server: int) -> None:
        ws, msg = await _connect(server, version="0.0.0")
        assert msg["type"] == WebClientMsgType.ERROR
        assert "mismatch" in msg["data"]["message"]


# ---------------------------------------------------------------------------
# Message relay
# ---------------------------------------------------------------------------


class TestMessageRelay:
    async def test_relay_garbage(self, server: int) -> None:
        ws1, _ = await _connect(server)
        ws2, _ = await _connect(server)

        await _recv_raw(ws1)  # MATCH_FOUND
        await _recv_raw(ws2)  # MATCH_FOUND

        await ws1.send(
            json.dumps(
                {"type": WebClientMsgType.GARBAGE, "data": {"lines": 3}}
            )
        )
        msg = await _recv_json(ws2)
        assert msg == {"type": WebClientMsgType.GARBAGE, "data": {"lines": 3}}
