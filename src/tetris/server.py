"""WebSocket server for 1v1 multiplayer Tetris."""

import argparse
import asyncio
import json
import logging
from typing import Optional
import uuid

import websockets
from websockets.exceptions import ConnectionClosed

from .enums import WebClientMsgType
from .utils import get_version

logger = logging.getLogger(__name__)


class Player:
    """Wraps a WebSocket connection with a short human-readable ID."""

    def __init__(self, websocket):
        self.id = str(uuid.uuid4())[:8]
        self.websocket = websocket
        self.room: Optional[Room] = None

    async def send(self, data: dict) -> None:
        """Send a JSON message to this player."""
        await self.websocket.send(json.dumps(data))


class Room:
    """Holds two matched players and relays messages between them."""

    def __init__(self, player_a: Player, player_b: Player, matchmaker: "Matchmaker | None" = None):
        self.players = [player_a, player_b]
        player_a.room = self
        player_b.room = self
        self._matchmaker = matchmaker
        self._closed = False

    async def run(self) -> None:
        """Notify both players, start relay tasks, and wait for disconnection."""
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
        """Read messages from source and forward them to target."""
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
        """Notify remaining player and close connections."""
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
    """Manages the waiting queue for 1v1 matchmaking."""

    def __init__(self, max_rooms: int = 0):
        self._waiting: Player | None = None
        self._lock = asyncio.Lock()
        self._active_rooms: set[Room] = set()
        self._max_rooms = max_rooms  # 0 means unlimited

    async def handle(self, player: Player) -> None:
        """Match this player with a waiting opponent, or queue them."""
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
        """Remove a finished room from the active set."""
        self._active_rooms.discard(room)


async def serve(host: str, port: int, server_version: str, max_rooms: int = 0) -> None:
    """Start the WebSocket server."""
    matchmaker = Matchmaker(max_rooms=max_rooms)

    async def handler(websocket):
        # Version handshake
        try:
            raw = await asyncio.wait_for(websocket.recv(), timeout=10)
        except TimeoutError:
            logger.warning("Connection timed out waiting for hello")
            return
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        if msg.get("type") != WebClientMsgType.HELLO:
            return
        client_version = msg.get("data", {}).get("version", "")
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
    """CLI entry point for tetris-server."""
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