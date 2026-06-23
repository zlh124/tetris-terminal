"""Enumerations used throughout tetris-terminal."""

from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import ClassVar

# fmt: off
class TetriminoShape(IntEnum):
    """Tetrimino piece identifier (matches standard Tetris piece numbering)."""

    EMPTY   = 0
    Z       = 1
    S       = 2
    O       = 3
    J       = 4
    T       = 5
    I       = 6
    L       = 7
    GARBAGE = 8  # Garbage Tetrimino
    CLEAR   = 9  # Cells in rows pending line-clear animation

    @classmethod
    def normal_tetriminos(cls) -> list[TetriminoShape]:
        """Return the seven standard tetriminos (excluding EMPTY, GARBAGE and CLEAR).

        Returns:
            List of the seven playable TetriminoShape values.
        """
        return list(TetriminoShape)[1:-2]

    def __repr__(self) -> str:
        return f"TetriminoShape.{self.name}"


class Direction(IntEnum):
    """Cardinal direction (0-3, clockwise from NORTH)."""

    NORTH = 0
    EAST  = 1
    SOUTH = 2
    WEST  = 3

    def __repr__(self) -> str:
        return f"Direction.{self.name}"


class GameMode(IntEnum):
    """Game mode identifiers.

    Attributes:
        _150_LINES: 150-row challenge; game ends when lines >= 150.
        CASUAL: Endless mode with level cap at 5.
        ENDLESS: Endless mode with level cap at 15.
        DIGGING: Digging mode with level cap at 5.
        TIME_ATTACK: Clear as many lines as possible in 2 minutes.
        VERSUS: 1v1 multiplayer battle.
    """

    _150_LINES  = 0
    CASUAL      = 1
    ENDLESS     = 2
    DIGGING     = 3
    TIME_ATTACK = 4
    VERSUS      = 5

    def __str__(self) -> str:
        return self.name.replace("_", " ").strip()


class Sections(IntEnum):
    """Menu section identifiers."""

    _150_LINES  = 0
    CASUAL      = 1
    ENDLESS     = 2
    DIGGING     = 3
    TIME_ATTACK = 4
    VERSUS      = 5
    QUIT        = 6

    def __str__(self) -> str:
        return self.name.replace("_", " ").strip()


class WebClientMsgType(StrEnum):
    """WebSocket message type identifiers used by client-server protocol."""

    BOARD                 = "board"
    ERROR                 = "error"
    GARBAGE               = "garbage"
    GAME_OVER             = "game_over"
    HELLO                 = "hello"
    HELLO_OK              = "hello_ok"
    LEAVE_QUEUE           = "leave_queue"
    MATCH_FOUND           = "match_found"
    OPPONENT_DISCONNECTED = "opponent_disconnected"
    SERVER_FULL           = "server_full"

# fmt: on
