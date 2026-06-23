"""WebSocket server for 1v1 multiplayer Tetris."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import uuid
from typing import Optional

import websockets
from websockets.exceptions import ConnectionClosed

from .enums import WebClientMsgType
from .utils import get_version

logger = logging.getLogger(__name__)


class Player:
    """Wraps a WebSocket connection with a short human-readable ID.

    Attributes:
        id: An 8-character UUID prefix.
        websocket: The underlying WebSocket connection.
        room: The :class:`Room` this player is currently in (``None`` while
            waiting).
    """

    def __init__(self, websocket: websockets.WebSocketServerProtocol) -> None:
        self.id: str = str(uuid.uuid4())[:8]
        self.websocket = websocket
        self.room: Room | None = None

    async def send(self, data: dict) -> None:
        """Send a JSON-serialisable dict to this player.

        Args:
            data: The message payload.
        """
        await self.websocket.send(json.dumps(data))


class Room:
    """Holds two matched players and relays messages between them.

    The room runs until one player disconnects, at which point the
    remaining player is notified and both connections are closed.
    """

    def __init__(
        self,
        player_a: Player,
        player_b: Player,
        matchmaker: Matchmaker | None = None,
    ) -> None:
        self.players: list[Player] = [player_a, player_b]
        player_a.room = self
        player_b.room = self
        self._matchmaker = matchmaker
        self._closed: bool = False

    async def run(self) -> None:
        """Notify both players of the match, then relay messages until a disconnect."""
        for i, player in enumerate(self.players):
            opponent = self.players[1 - i]
            await player.send(
                {
                    "type": WebClientMsgType.MATCH_FOUND,
                    "data": {"opponent_id": opponent.id},
                }
            )

        tasks = [
            asyncio.create_task(self._relay(self.players[0], self.players[1])),
            asyncio.create_task(self._relay(self.players[1], self.players[0])),
        ]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await self._cleanup()

    async def _relay(self, source: Player, target: Player) -> None:
        """Read messages from *source* and forward them to *target*.

        Args:
            source: The player whose messages are read.
            target: The player to whom messages are forwarded.
        """
        try:
            async for message in source.websocket:
                if self._closed:
                    break
                data = json.loads(message)
                await target.send(data)
        except ConnectionClosed:
            pass
        except json.JSONDecodeError:
            logger.warning("Invalid JSON from player %s", source.id)

    async def _cleanup(self) -> None:
        """Notify the remaining player and close both connections."""
        if self._closed:
            return
        self._closed = True
        for player in self.players:
            try:
                await player.send(
                    {
                        "type": WebClientMsgType.OPPONENT_DISCONNECTED,
                        "data": {},
                    }
                )
                await player.websocket.close()
            except (ConnectionClosed, websockets.exceptions.WebSocketException):
                pass
        if self._matchmaker:
            self._matchmaker._room_closed(self)


class Matchmaker:
    """Manages the waiting queue for 1v1 matchmaking.

    When a player connects they either pair with the next available
    waiting player or enter the queue themselves.

    Attributes:
        _max_rooms: Maximum concurrent rooms (``0`` = unlimited).
    """

    def __init__(self, max_rooms: int = 0) -> None:
        self._waiting: Player | None = None
        self._lock: asyncio.Lock = asyncio.Lock()
        self._active_rooms: set[Room] = set()
        self._max_rooms = max_rooms  # 0 means unlimited

    async def handle(self, player: Player) -> None:
        """Match *player* with a waiting opponent, or queue them.

        Args:
            player: The newly connected player.
        """
        async with self._lock:
            # Check if server is at capacity
            if self._max_rooms > 0 and len(self._active_rooms) >= self._max_rooms:
                logger.info(
                    "Player %s rejected: server full (%d rooms)",
                    player.id,
                    self._max_rooms,
                )
                await player.send(
                    {
                        "type": WebClientMsgType.SERVER_FULL,
                        "data": {"message": "Server is full"},
                    }
                )
                await player.websocket.close()
                return

            if self._waiting is None:
                self._waiting = player
                logger.info("Player %s is waiting for an opponent", player.id)
            else:
                opponent = self._waiting
                self._waiting = None
                room = Room(player, opponent, self)
                self._active_rooms.add(room)
                logger.info("Room created: %s vs %s", player.id, opponent.id)
                asyncio.create_task(room.run())
                return

        # Player is waiting — keep connection alive until cancelled or disconnected
        try:
            await player.websocket.wait_closed()
        except ConnectionClosed:
            pass
        finally:
            async with self._lock:
                if self._waiting is player:
                    self._waiting = None
                    logger.info("Player %s left while waiting", player.id)

    def _room_closed(self, room: Room) -> None:
        """Remove a finished room from the active set.

        Args:
            room: The room that has ended.
        """
        self._active_rooms.discard(room)


async def serve(
    host: str, port: int, server_version: str, max_rooms: int = 0
) -> None:
    """Start the WebSocket matchmaking server.

    Runs forever until a :exc:`KeyboardInterrupt` is received.

    Args:
        host: Address to bind (e.g. ``"0.0.0.0"``).
        port: TCP port to listen on.
        server_version: Expected client version string.
        max_rooms: Maximum concurrent game rooms (``0`` = unlimited).
    """
    matchmaker = Matchmaker(max_rooms=max_rooms)

    async def handler(websocket: websockets.WebSocketServerProtocol) -> None:
        # Version handshake
        try:
            raw = await asyncio.wait_for(websocket.recv(), timeout=10)
        except TimeoutError:
            logger.warning("Connection timed out waiting for hello")
            return
        try:
            msg: dict = json.loads(raw)
        except json.JSONDecodeError:
            return

        if msg.get("type") != WebClientMsgType.HELLO:
            return
        client_version: str = msg.get("data", {}).get("version", "")
        if client_version != server_version:
            await websocket.send(
                json.dumps(
                    {
                        "type": WebClientMsgType.ERROR,
                        "data": {
                            "message": f"Version mismatch: client {client_version} != server {server_version}"
                        },
                    }
                )
            )
            await websocket.close()
            logger.info(
                "Rejected player (version %s != %s)", client_version, server_version
            )
            return

        player = Player(websocket)
        await player.send(
            {
                "type": WebClientMsgType.HELLO_OK,
                "data": {"your_id": player.id},
            }
        )
        logger.info("Player %s connected (v%s)", player.id, client_version)
        await matchmaker.handle(player)
        # Keep connection alive until room ends or the player disconnects
        try:
            await websocket.wait_closed()
        except ConnectionClosed:
            pass

    logger.info("Starting tetris-server v%s on %s:%s", server_version, host, port)
    async with websockets.serve(handler, host, port):
        await asyncio.Future()  # run forever


def main() -> int:
    """CLI entry point for ``tetris-server``.

    Returns:
        Exit code (``0``).
    """
    server_version = get_version()

    parser = argparse.ArgumentParser(
        description="Tetris Terminal multiplayer server",
        epilog="Start the server, then connect two tetris clients for 1v1 battles.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"v{server_version}",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port to bind (default: 8765)",
    )
    parser.add_argument(
        "--max-rooms",
        type=int,
        default=0,
        help="Maximum concurrent game rooms (0 = unlimited, default: 0)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        asyncio.run(serve(args.host, args.port, server_version, args.max_rooms))
    except KeyboardInterrupt:
        logger.info("Server shutting down")
    return 0
