import curses
import random
import time
import logging

from collections import defaultdict, deque
from enum import Enum

logger = logging.getLogger("tetris.tetris")

EMPTY = 0

GAME_WINDOW_SIZE_HEIGHT = 22
GAME_WINDOW_SIZE_WIDTH = 50

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
    Z = 1
    S = 2
    O = 3
    J = 4
    T = 5
    I = 6
    L = 7

    def __repr__(self) -> str:
        return f"TetriminoShape.{self.name}"

    def __str__(self) -> str:
        return f"TetriminoShape.{self.name}"


class Direction(Enum):
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3

    def __repr__(self) -> str:
        return f"Direction.{self.name}"

    def __str__(self) -> str:
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

    def __str__(self) -> str:
        return f"Tetrimino.{self.shape}"


class Tetris:
    score = 0
    lines = 0

    lines_for_level = 0

    level = 1

    fps = 50  # 1 / 60 s per frame
    tick = 0.001  # calculate tick 1 ms

    failed = False

    cur_tetrimino = None
    shadow = []
    hold = None

    frame_timer = 0
    normal_fall_timer = 0
    soft_drop_timer = 0

    lock_down_timer = 0
    lock_down_rotate_counter = 0

    hold_once = False
    reach_bottom = False
    lowest = 0

    b2b_bones = False

    class Movement(Enum):
        MOVE = 0
        ROTATE = 1

    # for t-spin calculation
    last_move = Movement.MOVE

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

    def replenish_bag(self) -> None:
        """replenish the bag with 7 random tetriminos"""
        tmp = [Tetrimino(shape) for shape in list(TetriminoShape)]
        random.shuffle(tmp)
        logger.info(f"fill bag with {[t.shape.name for t in tmp]}")
        self.bag.extend(tmp)

    def init_bag(self) -> None:
        """fill the bag"""
        logger.info("init the bag...")
        for _ in range(2):
            self.replenish_bag()

    def get_tetrimino(self) -> Tetrimino:
        """get a tetrimino from the bag"""
        tetrimino = self.bag.popleft()
        if len(self.bag) == 7:
            self.replenish_bag()
        # move down one cell immediate
        return tetrimino

    def get_current_lowest(self) -> int:
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        return max(x for x, _ in self.cur_tetrimino)

    def generate_new_tetrimino(self) -> None:
        self.cur_tetrimino = self.get_tetrimino()
        logger.info("=" * 50)
        logger.info(f"generate new tetrimino {self.cur_tetrimino}")
        if any(self.board[x][y] != EMPTY for x, y in self.cur_tetrimino):
            logger.info("game failed, the new generated tetrimino is all in buff zone")
            self.failed = True
        self.do_fall_immediate()

    def line_clear(self) -> int:
        res = 0
        for row in range(len(self.board) - 1, -1, -1):
            while all(v != EMPTY for v in self.board[row]):
                res += 1

                for i in range(row - 1, -1, -1):
                    self.board[i + 1] = self.board[i]
                self.board[0] = [0] * 10
        return res

    def check_can_move_down(self) -> bool:
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        for x, y in self.cur_tetrimino:
            if x + 1 >= 40:
                return False
            if (x + 1, y) in self.cur_tetrimino:
                continue
            if self.board[x + 1][y] != EMPTY:
                return False
        return True

    def check_can_move_left(self) -> bool:
        if self.lock_down_rotate_counter >= 15:
            return False
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        for x, y in self.cur_tetrimino:
            if y - 1 < 0:
                return False
            if (x, y - 1) in self.cur_tetrimino:
                continue
            if self.board[x][y - 1] != EMPTY:
                return False
        return True

    def check_can_move_right(self) -> bool:
        if self.lock_down_rotate_counter >= 15:
            return False
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
        logger.info("move left...")
        if self.reach_bottom:
            self.lock_down_rotate_counter += 1

        self.last_move = self.Movement.MOVE

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
        logger.info("move right")
        if self.reach_bottom:
            self.lock_down_rotate_counter += 1

        self.last_move = self.Movement.MOVE

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
        if (
            self.lock_down_rotate_counter >= 15
        ):  # can only rotate 15 times when reach bottom
            return
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

                self.last_move = self.Movement.ROTATE
                logger.info("do rotate")
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

    def normal_fall(self) -> None:
        self.normal_fall_timer += self.tick
        if self.normal_fall_timer < self.fall_speed:
            return
        self.normal_fall_timer = 0
        if not self.do_fall_immediate():
            self.lowest = self.get_current_lowest()
            self.reach_bottom = True
        else:
            self.last_move = self.Movement.MOVE

    def do_soft_drop(self) -> None:
        # cancel normal fall
        self.normal_fall_timer = 0
        if not self.do_fall_immediate():
            self.lowest = self.get_current_lowest()
            self.reach_bottom = True
        else:
            # soft drop get level score
            self.score += self.level
            self.last_move = self.Movement.MOVE

    def do_hard_drop(self) -> None:
        while self.do_fall_immediate():
            # hard drop get 2 * level score
            self.score += self.level * 2
            pass
        self.lock_down()

    def do_hold(self) -> None:
        if self.hold_once:
            return
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        self.hold_once = True
        for x, y in self.cur_tetrimino:
            self.board[x][y] = EMPTY
        if self.hold is None:
            self.hold = self.cur_tetrimino
            self.generate_new_tetrimino()
        else:
            self.bag.appendleft(Tetrimino(self.hold.shape))
            self.hold = self.cur_tetrimino
            self.generate_new_tetrimino()

    def draw_board(self) -> None:
        self.frame_timer += self.tick
        if self.frame_timer < 1 / self.fps:
            return
        self.frame_timer = 0

        # draw border
        self.stdscr.move(0, 0)
        self.stdscr.addstr("┏")
        self.stdscr.move(0, GAME_WINDOW_SIZE_WIDTH - 1)
        self.stdscr.addstr("┓")
        self.stdscr.move(GAME_WINDOW_SIZE_HEIGHT - 1, 0)
        self.stdscr.addstr("┗")
        self.stdscr.move(GAME_WINDOW_SIZE_HEIGHT - 1, GAME_WINDOW_SIZE_WIDTH - 1)
        self.stdscr.addstr("┛")

        for i in range(1, GAME_WINDOW_SIZE_WIDTH - 1):
            self.stdscr.move(0, i)
            self.stdscr.addstr("━")
            self.stdscr.move(GAME_WINDOW_SIZE_HEIGHT - 1, i)
            self.stdscr.addstr("━")
        for i in range(1, GAME_WINDOW_SIZE_HEIGHT - 1):
            self.stdscr.move(i, 0)
            self.stdscr.addstr("┃")
            self.stdscr.move(i, GAME_WINDOW_SIZE_WIDTH - 1)
            self.stdscr.addstr("┃")

        self.stdscr.move(0, 21)
        self.stdscr.addstr("┳")
        for i in range(1, 21):
            self.stdscr.move(i, 21)
            self.stdscr.addstr("┃")
        self.stdscr.move(GAME_WINDOW_SIZE_HEIGHT - 1, 21)
        self.stdscr.addstr("┻")

        # title
        self.stdscr.move(3, 28)
        self.stdscr.addstr("━┳━┏━━━┳━┏━┓┳┏━╸")
        self.stdscr.move(4, 28)
        self.stdscr.addstr(" ┃ ┣━━ ┃ ┣┳┛┃┗━┓")
        self.stdscr.move(5, 28)
        self.stdscr.addstr(" ╹ ┗━━ ╹ ╹┗━┻━━┛")

        # game info
        self.stdscr.move(9, 27)
        self.stdscr.addstr("Next  : ")
        for i in range(5):
            self.stdscr.addstr(f"{self.bag[i].shape.name} ")

        self.stdscr.move(11, 27)
        self.stdscr.addstr(f"Score : {self.score}")
        self.stdscr.move(13, 27)
        self.stdscr.addstr(f"Lines : {self.lines}")
        self.stdscr.move(15, 27)
        self.stdscr.addstr(f"Level : {self.level}")
        self.stdscr.move(17, 27)
        self.stdscr.addstr(f"Hold  : {self.hold.shape.name if self.hold else ''}")

        # board
        for i in range(20, 40):
            self.stdscr.move(i - 19, 1)
            for j in range(10):
                # shadow
                if self.board[i][j] == EMPTY and (i, j) in self.shadow:
                    self.stdscr.addstr("[]")
                else:
                    self.stdscr.addstr("  ", curses.color_pair(self.board[i][j]))

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
            self.do_soft_drop()
        if c in ROTATE_CW:
            self.do_rotate_cw()
        if c in ROTATE_CCW:
            self.do_rotate_ccw()
        if c in HARD_DROP:
            self.do_hard_drop()
        if c in HOLD:
            self.do_hold()

    def is_t_spin(self) -> bool:
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        if (
            self.cur_tetrimino.shape != TetriminoShape.T
            or self.last_move != self.Movement.ROTATE
        ):
            return False
        cx, cy = self.cur_tetrimino[1]
        corners = 0
        for x, y in [
            (cx - 1, cy - 1),
            (cx + 1, cy - 1),
            (cx - 1, cy + 1),
            (cx + 1, cy + 1),
        ]:
            if (
                not ((0 <= x < len(self.board)) and (0 <= y < len(self.board[0])))
                or self.board[x][y] != EMPTY
            ):
                corners += 1
        return corners >= 3

    def lock_down(self) -> None:
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        # all cells in buff zone when lock down
        if all(x < 20 for x, _ in self.cur_tetrimino):
            self.failed = True

        is_t_spin = self.is_t_spin()
        cleared_lines = self.line_clear()

        logger.info("lock down, calculate score and lines.")
        logger.info(f"current level: {self.level}")
        logger.info(f"is t-spin: {is_t_spin}")

        # calculate the score and lines to add
        bonus = self.b2b_bones
        self.b2b_bones = False

        awarded_line = 0
        score2add = 0

        if is_t_spin:

            self.b2b_bones = True

            if cleared_lines == 0:
                awarded_line = 4
                score2add = 100 * self.level
            elif cleared_lines == 1:
                awarded_line = 7
                score2add = 400 * self.level
            elif cleared_lines == 2:
                awarded_line = 10
                score2add = 1200 * self.level
            elif cleared_lines == 3:
                awarded_line = 13
                score2add = 1600 * self.level
        else:
            if cleared_lines == 1:
                score2add = 100 * self.level
            elif cleared_lines == 2:
                awarded_line = 1
                score2add = 300 * self.level
            elif cleared_lines == 3:
                awarded_line = 2
                score2add = 500 * self.level
            elif cleared_lines == 4:
                awarded_line = 4
                self.b2b_bones = True

                score2add = 800 * self.level
        # if b2b, line clear bonus * 1.5 abd score * 1.5
        if bonus and self.b2b_bones:
            bonus_lines = int((awarded_line + cleared_lines) * 1.5)
            score2add += 1.5 * score2add
        else:
            bonus_lines = awarded_line + cleared_lines

        logger.info(f"b2b bonus: {bonus and self.b2b_bones}")
        logger.info("current lock down:")
        logger.info(f"score      : {score2add}")
        logger.info(f"bonus lines: {bonus_lines}")
        logger.info(f"lines      : {cleared_lines}")

        self.score += score2add

        self.score += score2add
        self.lines += cleared_lines
        self.lines_for_level += bonus_lines
        self.b2b_bones = bonus

        # level up
        # max level 15
        if (
            self.level < 15
            and self.lines_for_level >= 5 * self.level * (self.level + 1) / 2
        ):
            logger.info("level up...")
            self.level += 1

        logger.info("=" * 50)
        self.generate_new_tetrimino()

        self.reach_bottom = False
        self.lock_down_timer = 0
        self.lock_down_rotate_counter = 0
        self.hold_once = False

    def handle_lock_down(self) -> None:
        if not self.reach_bottom:
            return
        if self.lock_down_timer >= 0.5:
            self.lock_down()
            return
        # no longer move down and has cells below, continue timer
        # if self.get_current_lowest() == self.lowest and not self.check_can_move_down():
        if not self.check_can_move_down():
            self.lock_down_timer += self.tick
        # reach new lowest, reset timer and counter
        elif self.get_current_lowest() > self.lowest:
            self.reach_bottom = False
            self.lock_down_timer = 0
            self.lock_down_rotate_counter = 0

    def handle_shadow(self):
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        self.shadow = self.cur_tetrimino.bodies[::]

        def helper():
            assert self.cur_tetrimino is not None, "cur_tetrimino is None"
            for x, y in self.shadow:
                if x + 1 >= len(self.board):
                    return False
                if (x + 1, y) in self.board or (x + 1, y) in self.cur_tetrimino.bodies:
                    continue
                if self.board[x + 1][y] != EMPTY:
                    return False
            return True

        while helper():
            for i in range(len(self.shadow)):
                x, y = self.shadow[i]
                self.shadow[i] = x + 1, y

    def game_loop(self) -> None:
        while not self.failed:
            self.normal_fall()
            self.handle_input()
            self.handle_lock_down()
            self.handle_shadow()
            self.draw_board()
            time.sleep(self.tick)

    def init_color(self) -> None:
        if curses.can_change_color():
            curses.init_color(TetriminoShape.I.value, 0, 941, 941)
            curses.init_color(TetriminoShape.O.value, 941, 941, 0)
            curses.init_color(TetriminoShape.T.value, 627, 0, 941)
            curses.init_color(TetriminoShape.L.value, 941, 627, 0)
            curses.init_color(TetriminoShape.J.value, 0, 0, 941)
            curses.init_color(TetriminoShape.S.value, 0, 941, 0)
            curses.init_color(TetriminoShape.Z.value, 941, 0, 0)
        curses.use_default_colors()
        for tetrimino in list(TetriminoShape):
            curses.init_pair(tetrimino.value, tetrimino.value, tetrimino.value)

    def init_game(self) -> None:
        logger.info("init game...")
        self.init_bag()
        self.generate_new_tetrimino()
        self.init_color()

        curses.curs_set(0)
        self.stdscr.timeout(0)

    def main(self) -> None:
        self.init_game()
        self.game_loop()
