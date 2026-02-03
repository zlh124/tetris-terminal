import curses
import random

from collections import defaultdict, deque
from enum import Enum
import time

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


def rotate_points(
    points: list[tuple[int, int]],
    center: list[int | tuple[int, int]],
    ccw: bool = False,
) -> list[tuple[int, int]]:
    """rotate the point 90 degree"""
    if isinstance(center[0], (list, tuple)):
        cr = (center[0][0] + center[0][1]) / 2.0
        cc = (center[1][0] + center[1][1]) / 2.0  # type: ignore
    else:
        cr, cc = float(center[0]), float(center[1])  # type: ignore

    rotated_points = []

    for r, c in points:
        rel_r = r - cr
        rel_c = c - cc
        new_rel_r = -rel_c if ccw else rel_c
        new_rel_c = rel_r if ccw else -rel_r
        new_r = int(new_rel_r + cr)
        new_c = int(new_rel_c + cc)

        rotated_points.append((new_r, new_c))

    return rotated_points


class TetriminoShape(Enum):
    I = 1
    J = 2
    L = 3
    O = 4
    S = 5
    T = 6
    Z = 7

    def __repr__(self) -> str:
        return f"TetriminoShape.{self.name}"


class Direction(Enum):
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3

    def __repr__(self) -> str:
        return f"Direction.{self.name}"


SHAPE_TABLE = {
    TetriminoShape.I: [(0, 0), (0, 1), (0, 2), (0, 3)],
    TetriminoShape.J: [(0, 0), (1, 0), (1, 1), (1, 2)],
    TetriminoShape.L: [(0, 0), (0, 1), (0, 2), (-1, 2)],
    TetriminoShape.O: [(0, 0), (0, 1), (1, 0), (1, 1)],
    TetriminoShape.S: [(0, 0), (0, 1), (-1, 1), (-1, 2)],
    TetriminoShape.T: [(0, 0), (0, 1), (-1, 1), (0, 2)],
    TetriminoShape.Z: [(0, 0), (0, 1), (1, 1), (1, 2)],
}

ROTATE_AXIS = {
    TetriminoShape.I: [(0, 1), (1, 2)],
    TetriminoShape.J: [1, 1],
    TetriminoShape.L: [0, 1],
    TetriminoShape.O: [(0, 1), (0, 1)],
    TetriminoShape.S: [0, 1],
    TetriminoShape.T: [0, 1],
    TetriminoShape.Z: [1, 1],
}

GENERATE_POSITION = {
    TetriminoShape.I: (19, 3),
    TetriminoShape.J: (18, 3),
    TetriminoShape.L: (19, 3),
    TetriminoShape.O: (18, 4),
    TetriminoShape.S: (19, 3),
    TetriminoShape.T: (19, 3),
    TetriminoShape.Z: (18, 3),
}


# SRS system
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
for shape in list(TetriminoShape):
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


class Tetrimino:

    ## line0  0000000000 -
    ## ...               |>  buffer zone
    ## line19 0000000000 -
    ## line20 0000000000 -
    ## ...               |>   game zone
    ## line39 0000000000 -
    ## all the tetriminos are generated in the 18th and 19th line(buffer zone)

    def __init__(self, shape: TetriminoShape) -> None:
        self.shape = shape
        self.no = shape.value
        dx, dy = GENERATE_POSITION[shape]
        self.bodies = [(x + dx, y + dy) for (x, y) in SHAPE_TABLE[shape]]
        self.direction = Direction.NORTH

    def __iter__(self):
        for x, y in self.bodies:
            yield x, y

    def __getitem__(self, index: int) -> tuple[int, int]:
        return self.bodies[index]

    def __setitem__(self, index: int, value: tuple[int, int]) -> None:
        self.bodies[index] = value


class Tetris:
    score = 0
    level = 2
    fps = 60  # 1 / 60 s per frame
    tick = 0.001  # calculate tick 1 ms

    failed = False

    cur_tetrimino = None

    frame_timer = 0
    normal_fall_timer = 0
    soft_drop_timer = 0

    board = [[0] * 10 for _ in range(40)]
    bag: deque[Tetrimino] = deque(maxlen=14)

    @property
    def fall_speed(self) -> float:
        return (0.8 - ((self.level - 1) * 0.007)) ** (self.level - 1)

    @property
    def soft_drop_speed(self) -> float:
        return self.fall_speed / 20

    def __init__(self, stdscr: curses.window) -> None:
        self.stdscr = stdscr

    def replenish_bag(self):
        """replenish the bag with 7 random tetriminos"""
        tmp = [Tetrimino(shape) for shape in list(TetriminoShape)]
        random.shuffle(tmp)
        self.bag.extend(tmp)

    def init_bag(self) -> None:
        """fill the bag"""
        for _ in range(2):
            self.replenish_bag()

    def get_tetrimino(self) -> Tetrimino:
        """get a tetrimino from the bag"""
        tetrimino = self.bag.popleft()
        if len(self.bag) == 7:
            self.replenish_bag()
        # move down one cell immediate
        return tetrimino

    def generate_new_tetrimino(self):
        self.cur_tetrimino = self.get_tetrimino()
        self.do_fall_immediate()

    def check_can_move_down(self):
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        for x, y in self.cur_tetrimino:
            if x + 1 >= 40:
                return False
            if (x + 1, y) in self.cur_tetrimino:
                continue
            if self.board[x + 1][y] != EMPTY:
                return False
        return True

    def check_can_move_left(self):
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        for x, y in self.cur_tetrimino:
            if y - 1 < 0:
                return False
            if (x, y - 1) in self.cur_tetrimino:
                continue
            if self.board[x][y - 1] != EMPTY:
                return False
        return True

    def check_can_move_right(self):
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        for x, y in self.cur_tetrimino:
            if y + 1 >= 10:
                return False
            if (x, y + 1) in self.cur_tetrimino:
                continue
            if self.board[x][y + 1] != EMPTY:
                return False
        return True

    def do_fall_immediate(self) -> bool:
        if not self.check_can_move_down():
            return False
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        # clean old pos
        for x, y in self.cur_tetrimino:
            self.board[x][y] = EMPTY
        # move down
        for i, (x, y) in enumerate(self.cur_tetrimino):
            self.cur_tetrimino[i] = (x + 1, y)
        # draw new pos
        for x, y in self.cur_tetrimino:
            self.board[x][y] = self.cur_tetrimino.no
        return True

    def do_move_left(self) -> bool:
        if not self.check_can_move_left():
            return False
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        for x, y in self.cur_tetrimino:
            self.board[x][y] = EMPTY
        for i, (x, y) in enumerate(self.cur_tetrimino):
            self.cur_tetrimino[i] = (x, y - 1)
        for x, y in self.cur_tetrimino:
            self.board[x][y] = self.cur_tetrimino.no
        return True

    def do_move_right(self) -> bool:
        if not self.check_can_move_right():
            return False
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        for x, y in self.cur_tetrimino:
            self.board[x][y] = EMPTY
        for i, (x, y) in enumerate(self.cur_tetrimino):
            self.cur_tetrimino[i] = (x, y + 1)
        for x, y in self.cur_tetrimino:
            self.board[x][y] = self.cur_tetrimino.no
        return True

    def check_empty(self, points: list[tuple[int, int]]) -> bool:
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        m, n = len(self.board), len(self.board[0])
        for x, y in points:
            if (x, y) in self.cur_tetrimino.bodies:
                continue
            if not (0 <= x < m and 0 <= y < n) or self.board[x][y] != EMPTY:
                return False
        return True

    def do_rotate(self, cur_direction: Direction, next_direction: Direction):
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        standard_rotate_diff, offsets = ROTATE_TABLE[self.cur_tetrimino.shape][
            (cur_direction), (next_direction)
        ].values()

        rotated = [
            (x + dx, y + dy)
            for (x, y), (dx, dy) in list(
                zip(self.cur_tetrimino.bodies, standard_rotate_diff)
            )
        ]

        for dx, dy in offsets:
            tmp = rotated[::]
            for i, (x, y) in enumerate(rotated):
                tmp[i] = x + dx, y + dy

            if self.check_empty(tmp):
                for x, y in self.cur_tetrimino.bodies:
                    self.board[x][y] = EMPTY
                for x, y in tmp:
                    self.board[x][y] = self.cur_tetrimino.shape.value
                self.cur_tetrimino.bodies = tmp
                self.cur_tetrimino.direction = next_direction
                return

    def do_rotate_cw(self) -> None:
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        cur_direction = self.cur_tetrimino.direction
        directions = list(Direction)
        next_direction = directions[
            (directions.index(cur_direction) + 1) % len(directions)
        ]
        self.do_rotate(cur_direction, next_direction)

    def do_rotate_ccw(self) -> None:
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        cur_direction = self.cur_tetrimino.direction
        directions = list(Direction)
        next_direction = directions[
            (len(directions) + (directions.index(cur_direction) - 1)) % len(directions)
        ]
        self.do_rotate(cur_direction, next_direction)

    def normal_fall(self):
        self.normal_fall_timer += self.tick
        if self.normal_fall_timer < self.fall_speed:
            return
        self.normal_fall_timer = 0
        if not self.do_fall_immediate():
            self.generate_new_tetrimino()

    def soft_drop(self):
        # cancel normal fall
        self.normal_fall_timer = 0
        if not self.do_fall_immediate():
            self.generate_new_tetrimino()

    def draw_board(self):
        self.frame_timer += self.tick
        if self.frame_timer < 1 / self.fps:
            return
        self.frame_timer = 0
        self.stdscr.move(0, 3)
        self.stdscr.addstr("Next: ")
        for i in range(5):
            self.stdscr.addstr(f"{self.bag[i].shape.name} ")

        for i in range(20, 40):
            self.stdscr.move(i - 19, 1)
            for j in range(10):
                self.stdscr.addstr("  ", curses.color_pair(self.board[i][j]))
        self.stdscr.move(21, 1)
        self.stdscr.addstr(f"Score: {self.score}")
        self.stdscr.refresh()

    def handle_input(self) -> None:
        """handle the input
        Terminal input relies on the operating system's control
        over the rate at which keyboard characters are entered.
        it't hard to ctrl the long press and normal press
        """
        c = self.stdscr.getch()
        if c in EXIT:
            self.failed = True
        if c in MOVE_LEFT:
            self.do_move_left()
        if c in MOVE_RIGHT:
            self.do_move_right()
        if c in SOFT_DROP:
            self.soft_drop()
        if c in ROTATE_CW:
            self.do_rotate_cw()
        if c in ROTATE_CCW:
            self.do_rotate_ccw()

    def game_loop(self):
        while not self.failed:
            self.normal_fall()
            self.draw_board()
            self.handle_input()
            time.sleep(self.tick)

    def init_game(self):
        self.init_bag()
        self.generate_new_tetrimino()
        for i in range(1, 8):
            curses.init_pair(i, i, i)

        curses.resize_term(22, 22)
        self.stdscr.box()
        self.stdscr.timeout(0)

    def main(self):
        self.init_game()
        self.game_loop()


def wrapper(stdscr: curses.window):
    Tetris(stdscr).main()


if __name__ == "__main__":
    curses.wrapper(wrapper)
