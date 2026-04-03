"""main game logic"""

import curses
import random
import time

from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Generator

from .utils import rotate_points

WINDOW_ROWS = 22
WINDOW_COLS = 44

EMPTY = 0

EMPTY_CELL = "  "
SOLID_CELL = "██"
SHADOW_CELL = "░░"

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

    @classmethod
    def normal_tetriminos(cls):
        return list(TetriminoShape)[1:-1]

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

    def __iter__(self) -> Generator[tuple[int, int], Any, None]:
        for x, y in self.bodies:
            yield x, y

    def __getitem__(self, index: int) -> tuple[int, int]:
        return self.bodies[index]

    def __setitem__(self, index: int, value: tuple[int, int]) -> None:
        self.bodies[index] = value


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


class SettlementMessage:
    """game settlement message"""

    def __init__(
        self,
        score: int,
        lines: int,
        time: str,
        single: int,
        double: int,
        triple: int,
        tetris: int,
        t_spin: int,
        t_spin_single: int,
        t_spin_double: int,
        t_spin_triple: int,
        mini_t_spin: int,
        mini_t_spin_single: int,
        game_mode: str = "",
    ) -> None:
        # Summary
        self.score = score
        self.lines = lines
        self.time = time
        self.game_mode = game_mode

        # Line clear counts
        self.single = single
        self.double = double
        self.triple = triple
        self.tetris = tetris

        # T-Spin counts
        self.t_spin = t_spin
        self.t_spin_single = t_spin_single
        self.t_spin_double = t_spin_double
        self.t_spin_triple = t_spin_triple
        self.mini_t_spin = mini_t_spin
        self.mini_t_spin_single = mini_t_spin_single

    def format(self, width: int) -> list[str]:
        harfw = width >> 1
        if self.game_mode:
            msgs = [f"Mode: {self.game_mode}"]
        else:
            msgs = []
        msgs += [
            f"Score: {self.score}",
            f"Lines: {self.lines}",
            f"Time: {self.time}",
            f"Single: {self.single}",
            f"Double: {self.double}",
            f"Triple: {self.triple}",
            f"Tetris: {self.tetris}",
            f"T-Spin: {self.t_spin}",
            f"T-Spin Single: {self.t_spin_single}",
            f"T-Spin Double: {self.t_spin_double}",
            f"T-Spin Triple: {self.t_spin_triple}",
            f"Mini-T-Spin: {self.mini_t_spin}",
            f"Mini-T-Spin Single: {self.mini_t_spin_single}",
        ]
        i = 0
        res = []
        cur_line = ""
        while i < len(msgs):
            if len(cur_line) + harfw > width or len(msgs[i]) > harfw:
                res.append(f"{cur_line:^{width}}")
                cur_line = ""
            else:
                cur_line += f"{msgs[i]:^{harfw}}"
                i += 1
            if i == len(msgs):
                res.append(f"{cur_line:^{width}}")
        return res


class Tetris:
    # Game configuration
    fps = 30  # target 30 FPS
    frame_interval = 1.0 / fps  # seconds per frame (~0.0333s)
    time_attack_duration = 120  # 2 minutes for time attack mode

    # Board dimensions
    BOARD_WIDTH = 10
    BOARD_HEIGHT = 40

    MAX_LOCK_DOWN_MOVE_COUNT = 15

    class Movement(Enum):
        MOVE = 0
        ROTATE = 1

    @property
    def fall_speed(self) -> float:
        return (0.8 - ((self.level - 1) * 0.007)) ** (self.level - 1)

    @property
    def game_time(self) -> str:
        if self.running_since is not None:
            elapsed = self.elapsed + (datetime.now() - self.running_since)
        else:
            elapsed = self.elapsed
        time_diff = elapsed.total_seconds()
        minutes = int(time_diff // 60)
        seconds = int(time_diff % 60)
        milliseconds = int((time_diff * 100) % 100)
        return f"{minutes:02d}:{seconds:02d}:{milliseconds:02d}"

    @property
    def time_remaining(self) -> str:
        """remaining time for time attack mode"""
        if self.running_since is not None:
            elapsed = self.elapsed + (datetime.now() - self.running_since)
        else:
            elapsed = self.elapsed
        remaining = self.time_attack_duration - elapsed.total_seconds()
        if remaining <= 0:
            return "00:00:00"
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        milliseconds = int((remaining * 100) % 100)
        return f"{minutes:02d}:{seconds:02d}:{milliseconds:02d}"

    def __init__(self, stdscr: curses.window, game_mode: GameMode) -> None:
        self.stdscr = stdscr
        self.game_mode = game_mode

        # Score / progress
        self.score = 0
        self.lines = 0
        self.lines_for_level = 0
        self.level = 1
        self.elapsed = timedelta(0)
        self.running_since = datetime.now()

        # settlement
        self.single = 0
        self.double = 0
        self.triple = 0
        self.tetris = 0
        self.t_spin = 0
        self.t_spin_single = 0
        self.t_spin_double = 0
        self.t_spin_triple = 0
        self.mini_t_spin = 0
        self.mini_t_spin_single = 0

        # Game flow
        self.game_over = False
        self.paused = False

        # Piece state
        self.cur_tetrimino = None
        self.hold = None
        self.hold_once = False

        # Timers
        self.frame_timer = 0
        self.normal_fall_timer = 0
        self.soft_drop_timer = 0
        self.line_increment_timer = 0
        self.lock_down_timer = 0
        self.notice_timer = 0

        # Lock-down tracking
        self.lock_down_move_counter = 0
        self.lowest = 0

        # Combo / T-Spin tracking
        self.b2b_bonus = False
        self.last_move = self.Movement.MOVE
        self.rotate_offset = 0

        # Notice
        self.notice = ""

        # Board, bag, shadow, settlement message
        self.board = [
            [TetriminoShape.EMPTY] * self.BOARD_WIDTH for _ in range(self.BOARD_HEIGHT)
        ]
        self.shadow: list[tuple[int, int]] = []
        self.bag: deque[Tetrimino] = deque(maxlen=14)

        self.hold_window = curses.newwin(7, 12, 0, 0)
        self.info_window = curses.newwin(11, 12, 7, 0)
        self.notice_window = curses.newwin(4, 12, 18, 0)
        self.board_window = curses.newwin(22, 21, 0, 12)
        self.preview_window = curses.newwin(22, 12, 0, 32)

        # can't use from curses import ***. only curses.initscr() is called
        LTEE = curses.ACS_LTEE
        RTEE = curses.ACS_RTEE
        TTEE = curses.ACS_TTEE
        BTEE = curses.ACS_BTEE

        VLINE = curses.ACS_VLINE
        HLINE = curses.ACS_HLINE

        self.hold_window.border(0, 0, 0, 0, 0, TTEE, LTEE, RTEE)
        self.info_window.border(0, 0, 0, 0, VLINE, VLINE, LTEE, RTEE)
        self.notice_window.border(0, 0, 0, 0, VLINE, VLINE, 0, BTEE)
        self.preview_window.border(0, 0, 0, 0, TTEE, 0, BTEE, 0)
        self.board_window.border(0, 0, 0, 0, HLINE, 0, HLINE, BTEE)

    def replenish_bag(self) -> None:
        """replenish the bag with 7 random tetriminos"""
        tmp = [Tetrimino(shape) for shape in TetriminoShape.normal_tetriminos()]
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

    def get_current_lowest(self) -> int:
        """get the lowest row of the current tetrimino"""
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        return max(x for x, _ in self.cur_tetrimino)

    def generate_new_tetrimino(self) -> None:
        """generate a new tetrimino"""
        self.cur_tetrimino = self.get_tetrimino()
        if any(self.board[x][y] != TetriminoShape.EMPTY for x, y in self.cur_tetrimino):
            self.game_over = True
        self.do_move_down()

    def line_clear(self) -> int:
        """clear lines, called when current tetrimino is locked

        :return: the number of lines cleared
        :rtype: int
        """
        res = 0
        for row in range(self.BOARD_HEIGHT - 1, -1, -1):
            while all(v != TetriminoShape.EMPTY for v in self.board[row]):
                res += 1

                for i in range(row - 1, -1, -1):
                    self.board[i + 1] = self.board[i]
                self.board[0] = [TetriminoShape.EMPTY] * self.BOARD_WIDTH
        return res

    def check_can_move_down(self) -> bool:
        """check if the current tetrimino can move down

        :return: True if the current tetrimino can move down, False otherwise
        :rtype: bool
        """
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        for x, y in self.cur_tetrimino:
            if (
                x + 1 >= self.BOARD_HEIGHT
                or self.board[x + 1][y] != TetriminoShape.EMPTY
            ):
                return False
        return True

    def check_can_move_left(self) -> bool:
        """check if the current tetrimino can move left

        :return: True if the current tetrimino can move left, False otherwise
        :rtype: bool
        """
        if self.lock_down_move_counter >= self.MAX_LOCK_DOWN_MOVE_COUNT:
            return False
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        for x, y in self.cur_tetrimino:
            if y - 1 < 0 or self.board[x][y - 1] != TetriminoShape.EMPTY:
                return False
        return True

    def check_can_move_right(self) -> bool:
        """check if the current tetrimino can move right

        :return: True if the current tetrimino can move right, False otherwise
        :rtype: bool
        """
        if self.lock_down_move_counter >= self.MAX_LOCK_DOWN_MOVE_COUNT:
            return False
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        for x, y in self.cur_tetrimino:
            if (
                y + 1 >= self.BOARD_WIDTH
                or self.board[x][y + 1] != TetriminoShape.EMPTY
            ):
                return False
        return True

    def do_move_down(self) -> bool:
        """move the current tetrimino down immediately

        :return: True if the success, False otherwise
        :rtype: bool
        """
        if not self.check_can_move_down():
            return False
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        # move down
        for i, (x, y) in enumerate(self.cur_tetrimino):
            self.cur_tetrimino[i] = (x + 1, y)
        return True

    def do_move_left(self) -> bool:
        """move the current tetrimino left, called when key left is pressed

        :return: True if the success, False otherwise
        :rtype: bool
        """
        if not self.check_can_move_left():
            return False

        # counter++ reset timer
        self.lock_down_move_counter += 1
        self.lock_down_timer = 0

        self.last_move = self.Movement.MOVE

        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        for i, (x, y) in enumerate(self.cur_tetrimino):
            self.cur_tetrimino[i] = (x, y - 1)
        return True

    def do_move_right(self) -> bool:
        """move the current tetrimino right, called when key right is pressed

        :return: True if the success, False otherwise
        :rtype: bool
        """
        if not self.check_can_move_right():
            return False

        # counter++ reset timer
        self.lock_down_move_counter += 1
        self.lock_down_timer = 0

        self.last_move = self.Movement.MOVE

        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        for i, (x, y) in enumerate(self.cur_tetrimino):
            self.cur_tetrimino[i] = (x, y + 1)
        return True

    def check_point_empty(self, point: tuple[int, int]) -> bool:
        """check if the given point is empty in the board

        :param point: the point to check
        :return: True if the point is empty, False otherwise
        :rtype: bool
        """
        x, y = point
        return (
            0 <= x < self.BOARD_HEIGHT and 0 <= y < self.BOARD_WIDTH
        ) and self.board[x][y] == TetriminoShape.EMPTY

    def check_points_empty(self, points: list[tuple[int, int]]) -> bool:
        """check if the given points are empty in the board

        :param points: the points to check
        :return: True if the points are empty, False otherwise
        :rtype: bool
        """
        return all(self.check_point_empty(point) for point in points)

    def do_rotate(self, cur_direction: Direction, next_direction: Direction) -> None:
        """rotate the current tetrimino

        :param cur_direction: the current direction of the tetrimino
        :param next_direction: the next direction of the tetrimino
        """
        if (
            self.lock_down_move_counter >= self.MAX_LOCK_DOWN_MOVE_COUNT
        ):  # can only rotate 15 times when reach bottom
            return
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        rotate_data = ROTATE_TABLE[self.cur_tetrimino.shape][
            (cur_direction, next_direction)
        ]
        standard_rotate_diff = rotate_data["standard_rotate_diff"]
        offsets = rotate_data["offsets"]

        rotated = [
            (x + dx, y + dy)
            for (x, y), (dx, dy) in list(
                zip(self.cur_tetrimino.bodies, standard_rotate_diff)
            )
        ]

        for i, (dx, dy) in enumerate(offsets):
            tmp = rotated[::]
            for i, (x, y) in enumerate(rotated):
                tmp[i] = x + dx, y + dy

            if self.check_points_empty(tmp):
                self.cur_tetrimino.bodies = tmp
                self.cur_tetrimino.direction = next_direction

                self.last_move = self.Movement.ROTATE

                # counter++ reset timer
                self.lock_down_move_counter += 1
                self.lock_down_timer = 0

                # record the rotate offset for t-spin calculation
                self.rotate_offset = i

                return

    def do_rotate_cw(self) -> None:
        """try rotate the current tetrimino clockwise, called when key cw is pressed"""
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        cur_direction = self.cur_tetrimino.direction
        directions = list(Direction)
        next_direction = directions[
            (directions.index(cur_direction) + 1) % len(directions)
        ]
        self.do_rotate(cur_direction, next_direction)

    def do_rotate_ccw(self) -> None:
        """try rotate the current tetrimino counterclockwise, called when key ccw is pressed"""
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        cur_direction = self.cur_tetrimino.direction
        directions = list(Direction)
        next_direction = directions[
            (len(directions) + (directions.index(cur_direction) - 1)) % len(directions)
        ]
        self.do_rotate(cur_direction, next_direction)

    def normal_fall(self, dt: float) -> None:
        """fall the current tetrimino normally, called when normal fall timer is up"""
        self.normal_fall_timer += dt
        if self.normal_fall_timer < self.fall_speed:
            return
        self.normal_fall_timer = 0
        if self.do_move_down():
            self.last_move = self.Movement.MOVE

            # reset lock down timer and counter
            if self.get_current_lowest() > self.lowest:
                self.lock_down_timer = 0
                self.lowest = self.get_current_lowest()
            self.lock_down_move_counter = 0

    def do_soft_drop(self) -> None:
        """soft drop, called when soft drop key is pressed"""
        # cancel normal fall
        self.normal_fall_timer = 0
        if self.do_move_down():
            # soft drop get level score
            self.score += self.level
            self.last_move = self.Movement.MOVE

            # reset lock down timer and counter
            if self.get_current_lowest() > self.lowest:
                self.lock_down_timer = 0
                self.lowest = self.get_current_lowest()
            self.lock_down_move_counter = 0

    def do_hard_drop(self) -> None:
        """hard drop, called when hard drop key is pressed"""
        while self.do_move_down():
            # hard drop get 2 * level * lines score
            self.score += self.level * 2
        self.lock_down()

    def do_hold(self) -> None:
        """hold the current tetrimino, called when hold key is pressed"""
        if self.hold_once:
            return
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        self.hold_once = True
        for x, y in self.cur_tetrimino:
            self.board[x][y] = TetriminoShape.EMPTY
        if self.hold is None:
            self.hold = self.cur_tetrimino
            self.generate_new_tetrimino()
        else:
            self.bag.appendleft(Tetrimino(self.hold.shape))
            self.hold = self.cur_tetrimino
            self.generate_new_tetrimino()

    def set_notice(self, notice: str) -> None:
        """set notice

        :param notice: the notice to set
        """
        self.notice = notice
        self.notice_timer = time.time()

    def get_notice(self) -> str:
        """get notice

        :return: the notice
        :rtype: str
        """
        if self.paused:
            return "PAUSED"
        # show notice for 1 second
        if time.time() - self.notice_timer >= 1:
            return ""
        return self.notice

    def draw_board(self) -> None:
        """draw board"""
        window = self.board_window
        _, width = window.getmaxyx()

        width -= 1

        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        for i in range(20, self.BOARD_HEIGHT):
            line = i - 19
            for j in range(self.BOARD_WIDTH):
                cell = self.board[i][j]
                window.addstr(
                    line,
                    2 * j,
                    SOLID_CELL if cell != TetriminoShape.EMPTY else EMPTY_CELL,
                    self.get_color(cell),
                )
                # shadow
                if (i, j) in self.shadow:
                    window.addstr(
                        line,
                        2 * j,
                        SHADOW_CELL,
                        self.get_color(self.cur_tetrimino.shape),
                    )
                if (i, j) in self.cur_tetrimino:
                    window.addstr(
                        line,
                        2 * j,
                        SOLID_CELL,
                        self.get_color(self.cur_tetrimino.shape),
                    )

        self.board_window.refresh()

    def draw_preview(self) -> None:
        """draw preview"""
        window = self.preview_window
        height, width = window.getmaxyx()
        height -= 1
        width -= 2

        # Next row 1~height, col 0~10:
        window.addstr(1, 1, f"{' Next:':<{width}}")
        # each preview takes 3 rows and 8 cols
        s_col = 2
        # clear the preview area
        for row in range(2, height):
            window.addstr(row, s_col - 1, " " * (width))

        # draw the preview
        for i, s_row in enumerate(range(2, height - 1, 3)):
            shape = self.bag[i].shape
            dx, dy = SHOW_OFFSET[shape]
            for x, y in SHAPE_TABLE[shape]:
                window.addstr(
                    s_row + x + dx,
                    s_col + (y + dy) * 2,
                    SOLID_CELL,
                    self.get_color(shape),
                )

        window.refresh()

    def draw_hold(self) -> None:
        """draw hold"""
        window = self.hold_window
        height, width = window.getmaxyx()
        height -= 1
        width -= 2

        window.addstr(1, 1, f"{' Hold:':<{width}}")
        for row in range(2, height):
            window.addstr(row, 1, " " * width)

        if self.hold:
            shape = self.hold.shape
            s_row = 2
            s_col = 2
            dx, dy = SHOW_OFFSET[shape]
            for x, y in SHAPE_TABLE[shape]:
                window.addstr(
                    s_row + x + dx,
                    s_col + (y + dy) * 2,
                    SOLID_CELL,
                    self.get_color(shape),
                )

        window.refresh()

    def draw_info(self) -> None:
        """draw info"""
        window = self.info_window
        height, width = window.getmaxyx()

        height -= 1
        width -= 2

        for row in range(0, height):
            window.addstr(row, 1, " " * (width))

        if self.game_mode == GameMode.TIME_ATTACK:
            window.addstr(1, 1, f"{'Time:':<{width}}")
            window.addstr(2, 1, f"{self.time_remaining:>{width}}")
        else:
            window.addstr(1, 1, f"{'Time:':<{width}}")
            window.addstr(2, 1, f"{self.game_time:>{width}}")
        window.addstr(3, 1, f"{'Score:':<{width}}")
        window.addstr(4, 1, f"{str(self.score):>{width}}")
        window.addstr(5, 1, f"{'Lines:':<{width}}")
        window.addstr(6, 1, f"{str(self.lines):>{width}}")
        window.addstr(7, 1, f"{'Level:':<{width}}")
        window.addstr(8, 1, f"{str(self.level):>{width}}")

        window.refresh()

    def draw_notice(self) -> None:
        """draw info"""

        window = self.notice_window
        height, width = window.getmaxyx()

        height -= 1
        width -= 2

        # notice
        for row in range(0, height):
            window.addstr(row, 1, " " * width)

        notice = self.get_notice()
        if notice:
            if len(notice) > width:
                lines = [notice[i : i + width] for i in range(0, len(notice), width)]
                lines = lines[:height]
                for row, line in enumerate(lines):
                    window.addstr(row, 1, line)
            else:
                window.addstr(height // 2, 1, f"{notice:^{width}}")

        window.refresh()

    def draw(self, dt: float) -> None:
        """draw the game"""
        self.frame_timer += dt
        if self.frame_timer < 1 / self.fps:
            return
        self.frame_timer = 0

        self.draw_board()
        self.draw_preview()
        self.draw_hold()
        self.draw_info()
        self.draw_notice()

    def handle_input(self) -> None:
        """handle the input
        Terminal input relies on the operating system's control
        over the rate at which keyboard characters are entered.
        it't hard to ctrl the long press and normal press
        """
        c = self.stdscr.getch()
        if c in PAUSE:
            self.paused = not self.paused
            if self.paused:
                if self.running_since is not None:
                    self.elapsed += datetime.now() - self.running_since
                    self.running_since = None
            else:
                self.running_since = datetime.now()
        if c in EXIT:
            self.game_over = True

        if self.paused:
            return

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

    def is_t_spin(self) -> int:
        """check t-spin when lock down

        :return: t-spin or not: 0 not t-spin, 1 t-spin, 2 t-spin mini
        :rtype: int
        """
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        if (
            self.cur_tetrimino.shape != TetriminoShape.T
            or self.last_move != self.Movement.ROTATE
        ):
            return 0
        cx, cy = self.cur_tetrimino[1]

        corners = 0
        for p in [
            (cx - 1, cy - 1),
            (cx + 1, cy - 1),
            (cx - 1, cy + 1),
            (cx + 1, cy + 1),
        ]:
            if not self.check_point_empty(p):
                corners += 1

        if corners < 3:
            return 0
        # if rotate offset is 4th point, it's t-spin
        if self.rotate_offset == 4:
            return 1
        if self.cur_tetrimino.direction == Direction.NORTH:
            slots = [(cx - 1, cy - 1), (cx - 1, cy + 1)]
        if self.cur_tetrimino.direction == Direction.EAST:
            slots = [(cx - 1, cy + 1), (cx + 1, cy + 1)]
        if self.cur_tetrimino.direction == Direction.SOUTH:
            slots = [(cx + 1, cy - 1), (cx + 1, cy + 1)]
        if self.cur_tetrimino.direction == Direction.WEST:
            slots = [(cx - 1, cy - 1), (cx + 1, cy - 1)]
        return 1 if all(not self.check_point_empty(p) for p in slots) else 2

    def lock_down(self) -> None:
        """lock down the current tetrimino"""
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        # all cells in buff zone when lock down
        if all(x < 20 for x, _ in self.cur_tetrimino):
            self.game_over = True

        # fill cur tetrimino to the board
        for x, y in self.cur_tetrimino:
            self.board[x][y] = self.cur_tetrimino.shape

        is_t_spin = self.is_t_spin()
        cleared_lines = self.line_clear()

        was_b2b = self.calculate_score(is_t_spin, cleared_lines)

        self.generate_new_tetrimino()

        self.lock_down_timer = 0
        self.lock_down_move_counter = 0
        self.hold_once = False

        self.build_notice(is_t_spin, cleared_lines, was_b2b)

    def calculate_score(self, is_t_spin: int, cleared_lines: int) -> bool:
        """calculate and apply score, lines, level, and settlement stats for a lock-down event.

        :param is_t_spin: whether the lock-down was a T-Spin
        :param cleared_lines: number of lines cleared
        :return: whether back-to-back bonus was active before this lock-down
        :rtype: bool
        """
        bonus = self.b2b_bonus
        self.b2b_bonus = True

        awarded_line = 0
        score2add = 0

        if is_t_spin == 1:
            if cleared_lines == 0:
                awarded_line = 4
                score2add = 100 * self.level
                self.t_spin += 1
            elif cleared_lines == 1:
                awarded_line = 7
                score2add = 400 * self.level
                self.t_spin_single += 1
            elif cleared_lines == 2:
                awarded_line = 10
                score2add = 1200 * self.level
                self.t_spin_double += 1
            elif cleared_lines == 3:
                awarded_line = 13
                score2add = 1600 * self.level
                self.t_spin_triple += 1
        elif is_t_spin == 2:
            if cleared_lines == 0:
                awarded_line = 1
                score2add = 100 * self.level
                self.mini_t_spin += 1
            elif cleared_lines == 1:
                awarded_line = 2
                score2add = 200 * self.level
                self.mini_t_spin_single += 1
        else:
            if cleared_lines == 0:
                # no lines cleared, do not reset b2b
                self.b2b_bonus = bonus
            elif cleared_lines == 1:
                score2add = 100 * self.level
                self.b2b_bonus = False
                self.single += 1
            elif cleared_lines == 2:
                awarded_line = 1
                score2add = 300 * self.level
                self.b2b_bonus = False
                self.double += 1
            elif cleared_lines == 3:
                awarded_line = 2
                score2add = 500 * self.level
                self.b2b_bonus = False
                self.triple += 1
            elif cleared_lines == 4:
                awarded_line = 4
                score2add = 800 * self.level
                self.tetris += 1

        # if b2b, line clear bonus * 1.5 and score * 1.5
        if bonus and self.b2b_bonus:
            self.lines_for_level += int((awarded_line + cleared_lines) * 1.5)
            self.score += int(1.5 * score2add)
        else:
            self.lines_for_level += awarded_line + cleared_lines
            self.score += score2add

        self.lines += cleared_lines

        if self.game_mode == GameMode._150_ROWS and self.lines >= 150:
            self.game_over = True

        if (
            self.game_mode == GameMode.TIME_ATTACK
            and self.running_since is not None
            and (self.elapsed + (datetime.now() - self.running_since)).total_seconds()
            >= self.time_attack_duration
        ):
            self.game_over = True

        # level up
        # max level 15
        if (
            self.level < 15
            and self.lines_for_level >= 5 * self.level * (self.level + 1) / 2
        ):
            self.level += 1

        # if casual or digging mode, max level is 5
        if (
            self.game_mode == GameMode.CASUAL or self.game_mode == GameMode.DIGGING
        ) and self.level > 5:
            self.level = 5

        return bonus

    def build_notice(self, is_t_spin: int, cleared_lines: int, was_b2b: bool) -> None:
        """build and display the lock-down action notice.

        :param is_t_spin: whether the lock-down was a T-Spin
        :param cleared_lines: number of lines cleared
        :param was_b2b: whether back-to-back bonus was active before this lock-down
        """
        notice = ""
        if is_t_spin == 1:
            if cleared_lines == 0:
                notice = "T-Spin!"
            elif cleared_lines == 1:
                notice = "T-Spin Single!"
            elif cleared_lines == 2:
                notice = "T-Spin Double!"
            elif cleared_lines == 3:
                notice = "T-Spin Triple!"
        elif is_t_spin == 2:
            if cleared_lines == 0:
                notice = "T-Spin Mini!"
            elif cleared_lines == 1:
                notice = "T-Spin Mini Single!"
        elif cleared_lines == 1:
            notice = "Single!"
        elif cleared_lines == 2:
            notice = "Double!"
        elif cleared_lines == 3:
            notice = "Triple!"
        elif cleared_lines == 4:
            notice = "Tetris!"

        if notice:
            if self.b2b_bonus and was_b2b:
                notice += " B2B!"
            self.set_notice(notice)

    def handle_lock_down(self, dt: float) -> None:
        """handle lock down"""
        if self.check_can_move_down():
            return
        # reset when move and rotate successfully
        self.lock_down_timer += dt

        if self.lock_down_timer >= 0.5:
            self.lock_down()

    def handle_shadow(self):
        """handle shadow tetrimino"""
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        self.shadow = self.cur_tetrimino.bodies[::]

        def helper():
            if self.cur_tetrimino is None:
                raise RuntimeError("cur_tetrimino is None")
            for x, y in self.shadow:
                if x + 1 >= len(self.board):
                    return False
                if (x + 1, y) in self.cur_tetrimino.bodies:
                    continue
                if self.board[x + 1][y] != TetriminoShape.EMPTY:
                    return False
            return True

        while helper():
            for i in range(len(self.shadow)):
                x, y = self.shadow[i]
                self.shadow[i] = x + 1, y

    def handle_digging_mode(self, dt: float) -> None:
        """for digging mode, auto add one line at the bottom of the board in fixed time"""
        self.line_increment_timer += dt

        if (
            self.game_mode != GameMode.DIGGING
            or self.line_increment_timer < 5
            or not self.check_can_move_down()  # when reach bottom, stop the line increment
        ):
            return
        self.line_increment_timer = 0

        # add one line at the bottom of the board
        self.board.pop(0)

        # randomly set some empty cells
        new_line = [TetriminoShape.GARBAGE] * self.BOARD_WIDTH

        indexes = list(range(self.BOARD_WIDTH))
        random.shuffle(indexes)

        for i in range(random.randint(1, 5)):
            new_line[indexes[i]] = TetriminoShape.EMPTY

        self.board.append(new_line)

    def game_loop(self) -> None:
        """main game loop"""
        last_time = time.time()
        while not self.game_over:
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time

            self.handle_input()
            self.draw(dt)

            if not self.paused:
                self.handle_digging_mode(dt)
                self.normal_fall(dt)
                self.handle_lock_down(dt)
                self.handle_shadow()

                if (
                    self.game_mode == GameMode.TIME_ATTACK
                    and self.running_since is not None
                    and (
                        self.elapsed + (datetime.now() - self.running_since)
                    ).total_seconds()
                    >= self.time_attack_duration
                ):
                    self.game_over = True

            # Sleep remaining time to maintain target frame rate
            elapsed = time.time() - current_time
            sleep_time = self.frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def init_color(self) -> None:
        """initialize terminal color pairs for each tetrimino shape"""
        colorful = curses.COLORS > 16 and curses.can_change_color()
        if colorful:
            # the color 0~7 is the default terminal color, use 8 or higher
            curses.init_color(TetriminoShape.I.value + 7, 0, 941, 941)  # cyan
            curses.init_color(TetriminoShape.O.value + 7, 941, 941, 0)  # yellow
            curses.init_color(TetriminoShape.T.value + 7, 627, 0, 941)  # purple
            curses.init_color(TetriminoShape.L.value + 7, 941, 627, 0)  # orange
            curses.init_color(TetriminoShape.J.value + 7, 0, 0, 941)  # blue
            curses.init_color(TetriminoShape.S.value + 7, 0, 941, 0)  # green
            curses.init_color(TetriminoShape.Z.value + 7, 941, 0, 0)  # red
        for tetrimino in TetriminoShape.normal_tetriminos():
            curses.init_pair(
                tetrimino.value,
                tetrimino.value + 7 if colorful else tetrimino.value,
                -1,
            )

    def get_color(self, shape: TetriminoShape) -> int:
        """return the curses attribute for the given shape value

        :param shape: the shape value (TetriminoShape.value)
        :return: curses color pair for normal shapes, or A_REVERSE for GARBAGE
        :rtype: int
        """
        if shape != TetriminoShape.GARBAGE:
            return curses.color_pair(shape.value)
        return 0

    def init_game(self) -> None:
        """init the game"""
        self.init_bag()
        self.generate_new_tetrimino()
        self.init_color()
        self.stdscr.timeout(0)

    def main(self) -> SettlementMessage:
        """initialize and run the game, returning the settlement message on exit

        :return: statistics collected during the game session
        :rtype: SettlementMessage
        """
        self.init_game()
        self.game_loop()

        # return the settlement message
        mode_names = {
            GameMode._150_ROWS: "150 ROWS",
            GameMode.CASUAL: "CASUAL",
            GameMode.ENDLESS: "ENDLESS",
            GameMode.DIGGING: "DIGGING",
            GameMode.TIME_ATTACK: "TIME ATTACK",
        }
        return SettlementMessage(
            self.score,
            self.lines,
            self.game_time,
            self.single,
            self.double,
            self.triple,
            self.tetris,
            self.t_spin,
            self.t_spin_single,
            self.t_spin_double,
            self.t_spin_triple,
            self.mini_t_spin,
            self.mini_t_spin_single,
            game_mode=mode_names.get(self.game_mode, ""),
        )
