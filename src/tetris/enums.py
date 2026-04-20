from enum import Enum


class TetriminoShape(Enum):
    EMPTY = 0
    Z = 1
    S = 2
    O = 3
    J = 4
    T = 5
    I = 6
    L = 7
    GARBAGE = 8  # Garbage Tetrimino
    CLEAR = 9  # Cells in rows pending line-clear animation

    @classmethod
    def normal_tetriminos(cls):
        return list(TetriminoShape)[1:-2]

    def __repr__(self) -> str:
        return f"TetriminoShape.{self.name}"


class Direction(Enum):
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3

    def __repr__(self) -> str:
        return f"Direction.{self.name}"


class GameMode(Enum):
    """
    game mode

    :0: 150 rows, when lines >= 150, settlement game.
    :1: casual mode, endless, max level 5
    :2: endless, max level 15
    :3: digging mode, max level 5, endless
    :4: time attack, clear as many lines as possible in 2 minutes
    """

    _150_ROWS = 0
    CASUAL = 1
    ENDLESS = 2
    DIGGING = 3
    TIME_ATTACK = 4


class Sections(Enum):
    """game mode selection"""

    _150_ROWS = 0
    CASUAL = 1
    ENDLESS = 2
    DIGGING = 3
    TIME_ATTACK = 4
    QUIT = 5
