"""Constants and lookup tables for tetris-terminal.

Defines key bindings, tetrimino shapes, SRS rotation tables, wall-kick
offsets, and generation positions used by the game core.
"""

from __future__ import annotations

from collections import defaultdict
import curses
from typing import Any

from .enums import Direction, TetriminoShape

EMPTY: int = 0

# ---------------------------------------------------------------------------
# Key mappings
# ---------------------------------------------------------------------------
MOVE_LEFT: list[int] = [curses.KEY_LEFT, ord("A"), ord("a")]
MOVE_RIGHT: list[int] = [curses.KEY_RIGHT, ord("D"), ord("d")]
SOFT_DROP: list[int] = [curses.KEY_DOWN, ord("s"), ord("S")]
ROTATE_CW: list[int] = [curses.KEY_UP, ord("x"), ord("X"), ord("w"), ord("W")]
ROTATE_CCW: list[int] = [ord("z"), ord("Z")]
HOLD: list[int] = [ord("c"), ord("C")]
HARD_DROP: list[int] = [ord(" ")]
EXIT: list[int] = [ord("q"), ord("Q")]
PAUSE: list[int] = [ord("p"), ord("P")]

# ---------------------------------------------------------------------------
# Tetrimino shapes — cells relative to the standard rotation centre
# ---------------------------------------------------------------------------
SHAPE_TABLE: dict[TetriminoShape, list[tuple[int, int]]] = {
    TetriminoShape.I: [(0, 0), (0, 1), (0, 2), (0, 3)],
    TetriminoShape.J: [(0, 0), (1, 0), (1, 1), (1, 2)],
    TetriminoShape.L: [(0, 0), (0, 1), (0, 2), (-1, 2)],
    TetriminoShape.O: [(0, 0), (0, 1), (1, 0), (1, 1)],
    TetriminoShape.S: [(0, 0), (0, 1), (-1, 1), (-1, 2)],
    TetriminoShape.T: [(0, 0), (0, 1), (-1, 1), (0, 2)],
    TetriminoShape.Z: [(0, 0), (0, 1), (1, 1), (1, 2)],
}

# ---------------------------------------------------------------------------
# Standard rotation axis (row, col), from the first cell of the shape table.
# The I and O pieces use a double-axis midpoint.
# ---------------------------------------------------------------------------
ROTATE_AXIS: dict[TetriminoShape, list[int | tuple[int, int]]] = {
    TetriminoShape.I: [(0, 1), (1, 2)],
    TetriminoShape.J: [1, 1],
    TetriminoShape.L: [0, 1],
    TetriminoShape.O: [(0, 1), (0, 1)],
    TetriminoShape.S: [0, 1],
    TetriminoShape.T: [0, 1],
    TetriminoShape.Z: [1, 1],
}

# ---------------------------------------------------------------------------
# Drawing offsets for the preview / hold windows so each piece is centred
# ---------------------------------------------------------------------------
SHOW_OFFSET: dict[TetriminoShape, tuple[int, int]] = {
    TetriminoShape.I: (1, 0),
    TetriminoShape.J: (1, 0),
    TetriminoShape.L: (2, 0),
    TetriminoShape.O: (1, 0),
    TetriminoShape.S: (2, 0),
    TetriminoShape.T: (2, 0),
    TetriminoShape.Z: (1, 0),
}

# ---------------------------------------------------------------------------
# Spawn positions in the board (row, col) — top of the buffer zone
# ---------------------------------------------------------------------------
GENERATE_POSITION: dict[TetriminoShape, tuple[int, int]] = {
    TetriminoShape.I: (19, 3),
    TetriminoShape.J: (18, 3),
    TetriminoShape.L: (19, 3),
    TetriminoShape.O: (18, 4),
    TetriminoShape.S: (19, 3),
    TetriminoShape.T: (19, 3),
    TetriminoShape.Z: (18, 3),
}


# ---------------------------------------------------------------------------
# SRS (Super Rotation System) wall-kick offset tables.
#
# ROTATE_TABLE shape:
#   {shape: {(start_dir, end_dir): {"standard_rotate_diff": [(dx, dy), ...],
#                                    "offsets":              [(dx, dy), ...]}}}
# ---------------------------------------------------------------------------

JLSTZ_WALL_KICK_OFFSET: dict[tuple[Direction, Direction], list[tuple[int, int]]] = {
    (Direction.NORTH, Direction.EAST): [(0, 0), (0, -1), (-1, -1), (2, 0), (2, -1)],
    (Direction.EAST, Direction.NORTH): [(0, 0), (0, 1), (1, 1), (-2, 0), (-2, 1)],
    (Direction.EAST, Direction.SOUTH): [(0, 0), (0, 1), (1, 1), (-2, 0), (-2, 1)],
    (Direction.SOUTH, Direction.EAST): [(0, 0), (0, -1), (-1, -1), (2, 0), (2, -1)],
    (Direction.SOUTH, Direction.WEST): [(0, 0), (0, 1), (-1, 1), (2, 0), (2, 1)],
    (Direction.WEST, Direction.SOUTH): [(0, 0), (0, -1), (1, -1), (-2, 0), (-2, -1)],
    (Direction.WEST, Direction.NORTH): [(0, 0), (0, -1), (1, -1), (-2, 0), (-2, -1)],
    (Direction.NORTH, Direction.WEST): [(0, 0), (0, 1), (-1, 1), (2, 0), (2, 1)],
}

O_WALL_KICK_OFFSET: dict[tuple[Direction, Direction], list[tuple[int, int]]] = {
    (Direction.NORTH, Direction.EAST): [(0, 0)],
    (Direction.EAST, Direction.NORTH): [(0, 0)],
    (Direction.EAST, Direction.SOUTH): [(0, 0)],
    (Direction.SOUTH, Direction.EAST): [(0, 0)],
    (Direction.SOUTH, Direction.WEST): [(0, 0)],
    (Direction.WEST, Direction.SOUTH): [(0, 0)],
    (Direction.WEST, Direction.NORTH): [(0, 0)],
    (Direction.NORTH, Direction.WEST): [(0, 0)],
}

I_WALL_KICK_OFFSET: dict[tuple[Direction, Direction], list[tuple[int, int]]] = {
    (Direction.NORTH, Direction.EAST): [(0, 0), (0, -2), (0, 1), (1, -2), (-2, 1)],
    (Direction.EAST, Direction.NORTH): [(0, 0), (0, 2), (0, -1), (-1, 2), (2, -1)],
    (Direction.EAST, Direction.SOUTH): [(0, 0), (0, -1), (0, 2), (-2, -1), (1, 2)],
    (Direction.SOUTH, Direction.EAST): [(0, 0), (0, 1), (0, -2), (2, 1), (-1, -2)],
    (Direction.SOUTH, Direction.WEST): [(0, 0), (0, 2), (0, -1), (-1, 2), (2, -1)],
    (Direction.WEST, Direction.SOUTH): [(0, 0), (0, -2), (0, 1), (1, -2), (-2, 1)],
    (Direction.WEST, Direction.NORTH): [(0, 0), (0, 1), (0, -2), (2, 1), (-1, -2)],
    (Direction.NORTH, Direction.WEST): [(0, 0), (0, -1), (0, 2), (-2, -1), (1, 2)],
}

# ---------------------------------------------------------------------------
# Build the complete ROTATE_TABLE
# ---------------------------------------------------------------------------
ROTATE_TABLE: defaultdict[
    TetriminoShape,
    dict[tuple[Direction, Direction], dict[str, Any]],
] = defaultdict(lambda: defaultdict(dict))

for shape in TetriminoShape.normal_tetriminos():
    directions = list(Direction)
    _cw = [
        (directions[i], directions[(i + 1) % len(directions)], False)
        for i in range(len(directions))
    ]
    _ccw = [
        (
            directions[i],
            directions[(len(directions) + (i - 1)) % len(directions)],
            True,
        )
        for i in range(0, -len(directions), -1)
    ]

    cur_pos = SHAPE_TABLE[shape][::]
    for start, end, ccw in _cw + _ccw:
        from tetris.utils import rotate_points

        rotated = rotate_points(cur_pos, ROTATE_AXIS[shape], ccw)
        diff: list[tuple[int, int]] = [
            (rx - x, ry - y) for (rx, ry), (x, y) in list(zip(rotated, cur_pos))
        ]
        cur_pos = rotated

        ROTATE_TABLE[shape][(start, end)]["standard_rotate_diff"] = diff

        if shape == TetriminoShape.I:
            ROTATE_TABLE[shape][(start, end)]["offsets"] = I_WALL_KICK_OFFSET[
                (start, end)
            ]
        elif shape == TetriminoShape.O:
            ROTATE_TABLE[shape][(start, end)]["offsets"] = O_WALL_KICK_OFFSET[
                (start, end)
            ]
        else:
            ROTATE_TABLE[shape][(start, end)]["offsets"] = JLSTZ_WALL_KICK_OFFSET[
                (start, end)
            ]
