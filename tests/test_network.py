"""Unit tests for the synchronous WebSocket client (``tetris/network.py``).

A ``FakeWS`` stub is injected via ``monkeypatch``-ing ``tetris.network.connect``
so the client's parsing / state logic is exercised without a live server.
This avoids the sync-client-vs-async-server same-thread deadlock that a real
integration test would hit (the async ``server`` fixture and the synchronous
client cannot share one event loop).
"""

from __future__ import annotations

import json

import pytest
from websockets import Close
from websockets.exceptions import ConnectionClosed
from websockets.sync.client import ClientConnection

from tetris.enums import WebClientMsgType
from tetris.multiplay.network import NetworkClient


class FakeWS(ClientConnection):
    """A minimal stand-in for ``websockets.sync.client.ClientConnection``."""

    def __init__(self, incoming=None, send_raises=None, recv_raises=None):
        self.incoming: list[str] = list(incoming or [])
        self.sent: list[str] = []
        self._send_raises = send_raises
        self._recv_raises = recv_raises
        self.closed = False

    def send(self, data: str) -> None:
        if self._send_raises is not None:
            raise self._send_raises
        self.sent.append(data)

    def recv(self, timeout: float = 0) -> str:
        if self._recv_raises is not None:
            raise self._recv_raises
        if not self.incoming:
            raise TimeoutError()
        return self.incoming.pop(0)

    def close(self) -> None:
        self.closed = True


def _msg(d: dict) -> str:
    return json.dumps(d)


def _client_with(fake: FakeWS, monkeypatch) -> NetworkClient:
    monkeypatch.setattr("tetris.multiplay.network.connect", lambda url: fake)
    return NetworkClient()


def _handshake_ok(fake: FakeWS, monkeypatch) -> NetworkClient:
    """A client that has completed a successful handshake."""
    fake.incoming.append(
        _msg({"type": WebClientMsgType.HELLO_OK, "data": {"your_id": "abc12345"}})
    )
    client = _client_with(fake, monkeypatch)
    client.handshake("localhost", 8765, "0.4.0")
    return client


# ---------------------------------------------------------------------------
# handshake
# ---------------------------------------------------------------------------


class TestHandshake:
    """Tests for ``NetworkClient.handshake``."""

    def test_success_sets_player_id(self, monkeypatch) -> None:
        fake = FakeWS(
            incoming=[
                _msg(
                    {
                        "type": WebClientMsgType.HELLO_OK,
                        "data": {"your_id": "abc12345"},
                    }
                )
            ]
        )
        client = _client_with(fake, monkeypatch)
        client.handshake("localhost", 8765, "0.4.0")
        assert client.player_id == "abc12345"
        assert client.connected is True
        sent = json.loads(fake.sent[0])
        assert sent["type"] == WebClientMsgType.HELLO
        assert sent["data"]["version"] == "0.4.0"

    def test_version_mismatch_raises(self, monkeypatch) -> None:
        fake = FakeWS(
            incoming=[
                _msg(
                    {
                        "type": WebClientMsgType.ERROR,
                        "data": {"message": "Version mismatch: 0.0.0 != 0.4.0"},
                    }
                )
            ]
        )
        client = _client_with(fake, monkeypatch)
        with pytest.raises(RuntimeError, match="Version mismatch"):
            client.handshake("localhost", 8765, "0.0.0")


# ---------------------------------------------------------------------------
# wait_for_match
# ---------------------------------------------------------------------------


class TestWaitForMatch:
    """Tests for ``NetworkClient.wait_for_match``."""

    def test_returns_opponent_id(self, monkeypatch) -> None:
        fake = FakeWS(
            incoming=[
                _msg({"type": WebClientMsgType.HELLO_OK, "data": {"your_id": "a"}}),
                _msg(
                    {
                        "type": WebClientMsgType.MATCH_FOUND,
                        "data": {"opponent_id": "opponent42", "seed": 123},
                    }
                ),
            ]
        )
        client = _client_with(fake, monkeypatch)
        client.handshake("localhost", 8765, "v")  # consumes HELLO_OK
        assert client.wait_for_match() == "opponent42"
        assert client.opponent_id == "opponent42"

    def test_server_full_raises(self, monkeypatch) -> None:
        fake = FakeWS(
            incoming=[
                _msg({"type": WebClientMsgType.HELLO_OK, "data": {"your_id": "a"}}),
                _msg({"type": WebClientMsgType.SERVER_FULL, "data": {}}),
            ]
        )
        client = _client_with(fake, monkeypatch)
        client.handshake("localhost", 8765, "v")
        with pytest.raises(RuntimeError, match="Server is full"):
            client.wait_for_match()

    def test_not_connected_raises(self) -> None:
        client = NetworkClient()
        with pytest.raises(RuntimeError, match="Not connected"):
            client.wait_for_match()


# ---------------------------------------------------------------------------
# send
# ---------------------------------------------------------------------------


class TestSend:
    """Tests for ``NetworkClient.send``."""

    def test_serialises_json(self) -> None:
        fake = FakeWS()
        client = NetworkClient()
        client._ws = fake
        client.send({"type": WebClientMsgType.GARBAGE, "data": {"lines": 3}})
        assert json.loads(fake.sent[0]) == {
            "type": WebClientMsgType.GARBAGE,
            "data": {"lines": 3},
        }

    def test_when_disconnected_is_noop(self) -> None:
        client = NetworkClient()
        client.send({"type": WebClientMsgType.GARBAGE, "data": {"lines": 3}})

    def test_connection_closed_clears_ws(self) -> None:
        fake = FakeWS(send_raises=ConnectionClosed(Close(1006, ""), None))
        client = NetworkClient()
        client._ws = fake
        client.send({"type": WebClientMsgType.GARBAGE, "data": {"lines": 3}})
        assert client._ws is None
        assert client.connected is False


# ---------------------------------------------------------------------------
# recv
# ---------------------------------------------------------------------------


class TestRecv:
    """Tests for ``NetworkClient.recv``."""

    def test_returns_parsed_message(self) -> None:
        fake = FakeWS(
            incoming=[
                _msg(
                    {
                        "type": WebClientMsgType.GARBAGE,
                        "data": {"lines": 2},
                    }
                )
            ]
        )
        client = NetworkClient()
        client._ws = fake
        assert client.recv(timeout=0) == {
            "type": WebClientMsgType.GARBAGE,
            "data": {"lines": 2},
        }

    def test_returns_none_when_no_message(self) -> None:
        fake = FakeWS()
        client = NetworkClient()
        client._ws = fake
        assert client.recv(timeout=0) is None

    def test_returns_none_when_disconnected(self) -> None:
        client = NetworkClient()
        assert client.recv(timeout=0) is None

    def test_connection_closed_clears_ws(self) -> None:
        fake = FakeWS(recv_raises=ConnectionClosed(Close(1006, ""), None))
        client = NetworkClient()
        client._ws = fake
        assert client.recv(timeout=0) is None
        assert client._ws is None
        assert client.connected is False


# ---------------------------------------------------------------------------
# close & connected
# ---------------------------------------------------------------------------


class TestClose:
    """Tests for ``NetworkClient.close``."""

    def test_closes_and_clears_ws(self) -> None:
        fake = FakeWS()
        client = NetworkClient()
        client._ws = fake
        client.close()
        assert client._ws is None
        assert fake.closed is True
        assert client.connected is False

    def test_when_already_disconnected_is_noop(self) -> None:
        client = NetworkClient()
        client.close()
        assert client.connected is False


class TestConnected:
    """Tests for the ``connected`` property."""

    def test_false_by_default(self) -> None:
        assert NetworkClient().connected is False

    def test_true_after_handshake(self, monkeypatch) -> None:
        fake = FakeWS()
        _handshake_ok(fake, monkeypatch)
        # _handshake_ok builds its own client; rebuild to inspect the same fake
        fake2 = FakeWS(
            incoming=[
                _msg({"type": WebClientMsgType.HELLO_OK, "data": {"your_id": "x"}})
            ]
        )
        client = _client_with(fake2, monkeypatch)
        client.handshake("localhost", 8765, "v")
        assert client.connected is True
