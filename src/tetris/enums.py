from enum import IntEnum, StrEnum

# fmt: off
class TetriminoShape(IntEnum):
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
    def normal_tetriminos(cls):
        return list(TetriminoShape)[1:-2]

    def __repr__(self) -> str:
        return f"TetriminoShape.{self.name}"


class Direction(IntEnum):
    NORTH = 0
    EAST  = 1
    SOUTH = 2
    WEST  = 3

    def __repr__(self) -> str:
        return f"Direction.{self.name}"


class GameMode(IntEnum):
    """
    game mode

    :0: 150 rows, when lines >= 150, settlement game.
    :1: casual mode, endless, max level 5
    :2: endless, max level 15
    :3: digging mode, max level 5, endless
    :4: time attack, clear as many lines as possible in 2 minutes
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
    """game mode selection"""

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
    """web client message type"""

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
