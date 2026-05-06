"""constants"""

from collections import defaultdict
import curses

from tetris.enums import Direction, TetriminoShape

EMPTY = 0

# keymap
MOVE_LEFT = [curses.KEY_LEFT, ord("A"), ord("a")]
MOVE_RIGHT = [curses.KEY_RIGHT, ord("D"), ord("d")]
SOFT_DROP = [curses.KEY_DOWN, ord("s"), ord("S")]
ROTATE_CW = [curses.KEY_UP, ord("x"), ord("X"), ord("w"), ord("W")]
ROTATE_CCW = [ord("z"), ord("Z")]
HOLD = [ord("c"), ord("C")]
HARD_DROP = [ord(" ")]
EXIT = [ord("q"), ord("Q")]
PAUSE = [ord("p"), ord("P")]

SHAPE_TABLE = {
    TetriminoShape.I: [(0, 0), (0, 1), (0, 2), (0, 3)],
    TetriminoShape.J: [(0, 0), (1, 0), (1, 1), (1, 2)],
    TetriminoShape.L: [(0, 0), (0, 1), (0, 2), (-1, 2)],
    TetriminoShape.O: [(0, 0), (0, 1), (1, 0), (1, 1)],
    TetriminoShape.S: [(0, 0), (0, 1), (-1, 1), (-1, 2)],
    TetriminoShape.T: [(0, 0), (0, 1), (-1, 1), (0, 2)],
    TetriminoShape.Z: [(0, 0), (0, 1), (1, 1), (1, 2)],
}

# the standard rotate axis
ROTATE_AXIS = {
    TetriminoShape.I: [(0, 1), (1, 2)],
    TetriminoShape.J: [1, 1],
    TetriminoShape.L: [0, 1],
    TetriminoShape.O: [(0, 1), (0, 1)],
    TetriminoShape.S: [0, 1],
    TetriminoShape.T: [0, 1],
    TetriminoShape.Z: [1, 1],
}

# the offset for preview and hold
SHOW_OFFSET = {
    TetriminoShape.I: (1, 0),
    TetriminoShape.J: (1, 0),
    TetriminoShape.L: (2, 0),
    TetriminoShape.O: (1, 0),
    TetriminoShape.S: (2, 0),
    TetriminoShape.T: (2, 0),
    TetriminoShape.Z: (1, 0),
}

# the tetrimino generation position in the board
GENERATE_POSITION = {
    TetriminoShape.I: (19, 3),
    TetriminoShape.J: (18, 3),
    TetriminoShape.L: (19, 3),
    TetriminoShape.O: (18, 4),
    TetriminoShape.S: (19, 3),
    TetriminoShape.T: (19, 3),
    TetriminoShape.Z: (18, 3),
}


# SRS (super rotate system), retrieve the table for rotate position
# {shape: {(start_direction, end_direction): {standard_rotate_diff: [x, y], offsets: [(x, y),...]}}}
ROTATE_TABLE = defaultdict(lambda: defaultdict(dict))


JLSTZ_WALL_KICK_OFFSET = {
    (Direction.NORTH, Direction.EAST): [(0, 0), (0, -1), (-1, -1), (2, 0), (2, -1)],
    (Direction.EAST, Direction.NORTH): [(0, 0), (0, 1), (1, 1), (-2, 0), (-2, 1)],
    (Direction.EAST, Direction.SOUTH): [(0, 0), (0, 1), (1, 1), (-2, 0), (-2, 1)],
    (Direction.SOUTH, Direction.EAST): [(0, 0), (0, -1), (-1, -1), (2, 0), (2, -1)],
    (Direction.SOUTH, Direction.WEST): [(0, 0), (0, 1), (-1, 1), (2, 0), (2, 1)],
    (Direction.WEST, Direction.SOUTH): [(0, 0), (0, -1), (1, -1), (-2, 0), (-2, -1)],
    (Direction.WEST, Direction.NORTH): [(0, 0), (0, -1), (1, -1), (-2, 0), (-2, -1)],
    (Direction.NORTH, Direction.WEST): [(0, 0), (0, 1), (-1, 1), (2, 0), (2, 1)],
}

O_WALL_KICK_OFFSET = {
    (Direction.NORTH, Direction.EAST): [(0, 0)],
    (Direction.EAST, Direction.NORTH): [(0, 0)],
    (Direction.EAST, Direction.SOUTH): [(0, 0)],
    (Direction.SOUTH, Direction.EAST): [(0, 0)],
    (Direction.SOUTH, Direction.WEST): [(0, 0)],
    (Direction.WEST, Direction.SOUTH): [(0, 0)],
    (Direction.WEST, Direction.NORTH): [(0, 0)],
    (Direction.NORTH, Direction.WEST): [(0, 0)],
}

I_WALL_KICK_OFFSET = {
    (Direction.NORTH, Direction.EAST): [(0, 0), (0, -2), (0, 1), (1, -2), (-2, 1)],
    (Direction.EAST, Direction.NORTH): [(0, 0), (0, 2), (0, -1), (-1, 2), (2, -1)],
    (Direction.EAST, Direction.SOUTH): [(0, 0), (0, -1), (0, 2), (-2, -1), (1, 2)],
    (Direction.SOUTH, Direction.EAST): [(0, 0), (0, 1), (0, -2), (2, 1), (-1, -2)],
    (Direction.SOUTH, Direction.WEST): [(0, 0), (0, 2), (0, -1), (-1, 2), (2, -1)],
    (Direction.WEST, Direction.SOUTH): [(0, 0), (0, -2), (0, 1), (1, -2), (-2, 1)],
    (Direction.WEST, Direction.NORTH): [(0, 0), (0, 1), (0, -2), (2, 1), (-1, -2)],
    (Direction.NORTH, Direction.WEST): [(0, 0), (0, -1), (0, 2), (-2, -1), (1, 2)],
}

# build the ROTATE_TABLE
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
        diff = [(rx - x, ry - y) for (rx, ry), (x, y) in list(zip(rotated, cur_pos))]
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
