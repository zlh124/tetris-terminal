import curses
import random
import time

from collections import defaultdict, deque
from enum import Enum

from .utils import rotate_points

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


class GameMode(Enum):
    """
    game mode

    :0: 150 rows, when lines >= 150, settlement game.
    :1: casual mode, endless, max level 5
    :2: endless, max level 15
    :3: digging mode, max level 5, endless
    """

    _150_ROWS = 0
    CASUAL = 1
    ENDLESS = 2
    DIGGING = 3


class SettlementMessage:
    """game settlement message"""

    score = 0
    lines = 0
    single = 0
    double = 0
    triple = 0
    tetris = 0
    t_spin = 0
    t_spin_single = 0
    t_spin_double = 0
    t_spin_triple = 0

    def format(self, width: int) -> list[str]:
        return [
            f"{'Score : ' + str(self.score):^{width // 2}}"
            + f"{'Lines : ' + str(self.lines):^{width // 2}}",
            f"{'Single : ' + str(self.single):^{width // 2}}"
            + f"{'Double : ' + str(self.double):^{width // 2}}",
            f"{'Triple : ' + str(self.triple):^{width // 2}}"
            + f"{'Tetris : ' + str(self.tetris):^{width // 2}}",
            f"{'T-Spin : ' + str(self.t_spin):^{width // 2}}"
            + f"{'T-Spin Single : ' + str(self.t_spin_single):^{width // 2}}",
            f"{'T-Spin Double : ' + str(self.t_spin_double):^{width // 2}}"
            + f"{'T-Spin Triple : ' + str(self.t_spin_triple):^{width // 2}}",
        ]


class Tetris:
    score = 0
    lines = 0
    lines_for_level = 0

    level = 1

    fps = 30  # 1 / 60 s per frame
    tick = 0.001  # calculate tick 1 ms

    game_over = False
    paused = False

    cur_tetrimino = None
    shadow = []
    hold = None
    notice = ""

    frame_timer = 0
    normal_fall_timer = 0
    soft_drop_timer = 0
    line_increment_timer = 0

    lock_down_timer = 0
    lock_down_move_counter = 0

    notice_timer = 0

    hold_once = False
    lowest = 0

    b2b_bonus = False

    set_msg = SettlementMessage()

    class Movement(Enum):
        MOVE = 0
        ROTATE = 1

    # for t-spin calculation
    last_move = Movement.MOVE

    BOARD_WIDTH = 10
    BOARD_HEIGHT = 40

    MAX_LOCK_DOWN_MOVE_COUNT = 15

    bag: deque[Tetrimino] = deque(maxlen=14)

    @property
    def fall_speed(self) -> float:
        return (0.8 - ((self.level - 1) * 0.007)) ** (self.level - 1)

    @property
    def soft_drop_speed(self) -> float:
        return self.fall_speed / 20

    def __init__(self, stdscr: curses.window, game_mode: GameMode) -> None:
        self.stdscr = stdscr
        self.game_mode = game_mode

        self.board = [[0] * self.BOARD_WIDTH for _ in range(self.BOARD_HEIGHT)]

        self.board_window = curses.newwin(22, 22, 0, 0)
        self.preview_window = curses.newwin(22, 11, 0, 22)
        self.hold_window = curses.newwin(7, 11, 0, 33)
        self.info_window = curses.newwin(11, 11, 7, 33)
        self.notice_window = curses.newwin(4, 11, 18, 33)

        # can't use from curses import ***. only curses.initscr() is called
        LTEE = curses.ACS_LTEE
        RTEE = curses.ACS_RTEE
        TTEE = curses.ACS_TTEE
        BTEE = curses.ACS_BTEE

        VLINE = curses.ACS_VLINE
        HLINE = curses.ACS_HLINE

        self.board_window.border(0, 0, 0, 0, 0, TTEE, 0, BTEE)
        self.preview_window.border(0, 0, 0, 0, HLINE, TTEE, HLINE, BTEE)
        self.hold_window.border(0, 0, 0, 0, HLINE, 0, HLINE, RTEE)
        self.info_window.border(0, 0, 0, 0, HLINE, VLINE, HLINE, RTEE)
        self.notice_window.border(0, 0, 0, 0, HLINE, VLINE, HLINE, 0)

    def replenish_bag(self) -> None:
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

    def get_current_lowest(self) -> int:
        """get the lowest row of the current tetrimino"""
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        return max(x for x, _ in self.cur_tetrimino)

    def generate_new_tetrimino(self) -> None:
        """generate a new tetrimino"""
        self.cur_tetrimino = self.get_tetrimino()
        if any(self.board[x][y] != EMPTY for x, y in self.cur_tetrimino):
            self.game_over = True
        self.do_fall_immediate()

    def line_clear(self) -> int:
        """clear lines, called when current tetrimino is locked

        :return: the number of lines cleared
        :rtype: int
        """
        res = 0
        for row in range(self.BOARD_HEIGHT - 1, -1, -1):
            while all(v != EMPTY for v in self.board[row]):
                res += 1

                for i in range(row - 1, -1, -1):
                    self.board[i + 1] = self.board[i]
                self.board[0] = [0] * 10
        return res

    def check_can_move_down(self) -> bool:
        """check if the current tetrimino can move down

        :return: True if the current tetrimino can move down, False otherwise
        :rtype: bool
        """
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        for x, y in self.cur_tetrimino:
            if x + 1 >= self.BOARD_HEIGHT:
                return False
            if self.board[x + 1][y] != EMPTY:
                return False
        return True

    def check_can_move_left(self) -> bool:
        """check if the current tetrimino can move left

        :return: True if the current tetrimino can move left, False otherwise
        :rtype: bool
        """
        if self.lock_down_move_counter >= self.MAX_LOCK_DOWN_MOVE_COUNT:
            return False
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        for x, y in self.cur_tetrimino:
            if y - 1 < 0:
                return False
            if self.board[x][y - 1] != EMPTY:
                return False
        return True

    def check_can_move_right(self) -> bool:
        """check if the current tetrimino can move right

        :return: True if the current tetrimino can move right, False otherwise
        :rtype: bool
        """
        if self.lock_down_move_counter >= self.MAX_LOCK_DOWN_MOVE_COUNT:
            return False
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        for x, y in self.cur_tetrimino:
            if y + 1 >= self.BOARD_WIDTH:
                return False
            if self.board[x][y + 1] != EMPTY:
                return False
        return True

    def do_fall_immediate(self) -> bool:
        """move the current tetrimino down immediately

        :return: True if the success, False otherwise
        :rtype: bool
        """
        if not self.check_can_move_down():
            return False
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
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

        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
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

        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        for i, (x, y) in enumerate(self.cur_tetrimino):
            self.cur_tetrimino[i] = (x, y + 1)
        return True

    def check_empty(self, points: list[tuple[int, int]]) -> bool:
        """check if the given points are empty in the board

        :param points: the points to check
        :return: True if the points are empty, False otherwise
        :rtype: bool
        """
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        for x, y in points:
            if (x, y) in self.cur_tetrimino.bodies:
                continue
            if (
                not (0 <= x < self.BOARD_HEIGHT and 0 <= y < self.BOARD_WIDTH)
                or self.board[x][y] != EMPTY
            ):
                return False
        return True

    def do_rotate(self, cur_direction: Direction, next_direction: Direction) -> None:
        """rotate the current tetrimino

        :param cur_direction: the current direction of the tetrimino
        :param next_direction: the next direction of the tetrimino
        """
        if (
            self.lock_down_move_counter >= self.MAX_LOCK_DOWN_MOVE_COUNT
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
                self.cur_tetrimino.bodies = tmp
                self.cur_tetrimino.direction = next_direction

                self.last_move = self.Movement.ROTATE

                # counter++ reset timer
                self.lock_down_move_counter += 1
                self.lock_down_timer = 0

                return

    def do_rotate_cw(self) -> None:
        """rotate the current tetrimino clockwise, called when key cw is pressed"""
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        cur_direction = self.cur_tetrimino.direction
        directions = list(Direction)
        next_direction = directions[
            (directions.index(cur_direction) + 1) % len(directions)
        ]
        self.do_rotate(cur_direction, next_direction)

    def do_rotate_ccw(self) -> None:
        """rotate the current tetrimino counterclockwise, called when key ccw is pressed"""
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        cur_direction = self.cur_tetrimino.direction
        directions = list(Direction)
        next_direction = directions[
            (len(directions) + (directions.index(cur_direction) - 1)) % len(directions)
        ]
        self.do_rotate(cur_direction, next_direction)

    def normal_fall(self) -> None:
        """fall the current tetrimino normally, called when normal fall timer is up"""
        self.normal_fall_timer += self.tick
        if self.normal_fall_timer < self.fall_speed:
            return
        self.normal_fall_timer = 0
        if self.do_fall_immediate():
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
        if self.do_fall_immediate():
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
        while self.do_fall_immediate():
            # hard drop get 2 * level * lines score
            self.score += self.level * 2
            pass
        self.lock_down()

    def do_hold(self) -> None:
        """hold the current tetrimino, called when hold key is pressed"""
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
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        for i in range(20, self.BOARD_HEIGHT):
            line = i - 19
            for j in range(self.BOARD_WIDTH):
                self.board_window.addstr(
                    line, 2 * j + 1, "  ", curses.color_pair(self.board[i][j])
                )
                # shadow
                if self.board[i][j] == EMPTY and (i, j) in self.shadow:
                    self.board_window.addstr(line, 2 * j + 1, "[]")
                if (i, j) in self.cur_tetrimino:
                    self.board_window.addstr(
                        line,
                        2 * j + 1,
                        "  ",
                        curses.color_pair(self.cur_tetrimino.shape.value),
                    )
        self.board_window.refresh()

    def draw_preview(self) -> None:
        """draw preview"""
        window = self.preview_window
        height, width = window.getmaxyx()
        height -= 1
        width -= 1

        # Next row 1~height, col 0~10:
        window.addstr(1, 0, f"{' Next:':<{width}}")
        # each preview takes 3 rows and 8 cols
        s_col = 1
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
                    "  ",
                    curses.color_pair(shape.value),
                )

        hold_win_h = self.hold_window.getmaxyx()[0]
        info_win_h = self.info_window.getmaxyx()[0]

        window.addch(hold_win_h - 1, width, curses.ACS_LTEE)
        window.addch(hold_win_h + info_win_h - 1, width, curses.ACS_LTEE)

        window.refresh()

    def draw_hold(self) -> None:
        """draw hold"""
        window = self.hold_window
        height, width = window.getmaxyx()
        height -= 1
        width -= 1

        window.addstr(1, 0, f"{' Hold:':<{width}}")
        for row in range(2, height):
            window.addstr(row, 0, " " * 10)

        if self.hold:
            shape = self.hold.shape
            s_row = 2
            s_col = 1
            dx, dy = SHOW_OFFSET[shape]
            for x, y in SHAPE_TABLE[shape]:
                window.addstr(
                    s_row + x + dx,
                    s_col + (y + dy) * 2,
                    "  ",
                    curses.color_pair(shape.value),
                )

        window.refresh()

    def draw_info(self) -> None:
        window = self.info_window
        height, width = window.getmaxyx()

        height -= 1
        width -= 1

        for row in range(0, height):
            window.addstr(row, 0, " " * (width))

        window.addstr(1, 0, f"{' Score:':<{width}}")
        window.addstr(2, 0, f"{str(self.score) + ' ':>{width}}")
        window.addstr(4, 0, f"{' Lines:':<{width}}")
        window.addstr(5, 0, f"{str(self.lines) + ' ':>{width}}")
        window.addstr(7, 0, f"{' Level:':<{width}}")
        window.addstr(8, 0, f"{str(self.level) + ' ':>{width}}")

        window.refresh()

    def draw_notice(self) -> None:
        """draw info"""

        window = self.notice_window
        height, width = window.getmaxyx()

        height -= 1
        width -= 1

        # notice
        for row in range(0, height):
            window.addstr(row, 0, " " * width)

        notice = self.get_notice()
        if notice:
            if len(notice) > width:
                lines = [notice[i : i + width] for i in range(0, len(notice), width)]
                lines = lines[:height]
                for row, line in enumerate(lines):
                    window.addstr(row, 0, line)
            else:
                window.addstr(height // 2, 0, f"{notice:^{width}}")

        window.refresh()

    def draw(self) -> None:
        """draw the game"""
        self.frame_timer += self.tick
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

    def is_t_spin(self) -> bool:
        """check t-spin when lock down"""
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
        """lock down the current tetrimino, calculate the score and lines and so on"""
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        # all cells in buff zone when lock down
        if all(x < 20 for x, _ in self.cur_tetrimino):
            self.game_over = True

        # fill cur tetrimino to the board
        for x, y in self.cur_tetrimino:
            self.board[x][y] = self.cur_tetrimino.no

        is_t_spin = self.is_t_spin()
        cleared_lines = self.line_clear()

        # calculate the score and lines to add
        bonus = self.b2b_bonus
        self.b2b_bonus = True

        awarded_line = 0
        score2add = 0

        if is_t_spin:
            if cleared_lines == 0:
                awarded_line = 4
                score2add = 100 * self.level
                self.set_msg.t_spin += 1
            elif cleared_lines == 1:
                awarded_line = 7
                score2add = 400 * self.level
                self.set_msg.t_spin_single += 1
            elif cleared_lines == 2:
                awarded_line = 10
                score2add = 1200 * self.level
                self.set_msg.t_spin_double += 1
            elif cleared_lines == 3:
                awarded_line = 13
                score2add = 1600 * self.level
                self.set_msg.t_spin_triple += 1
        else:
            if cleared_lines == 0:
                # no lines cleared, do not reset b2b
                self.b2b_bonus = bonus
            elif cleared_lines == 1:
                score2add = 100 * self.level
                self.b2b_bonus = False
                self.set_msg.single += 1
            elif cleared_lines == 2:
                awarded_line = 1
                score2add = 300 * self.level
                self.b2b_bonus = False
                self.set_msg.double += 1
            elif cleared_lines == 3:
                awarded_line = 2
                score2add = 500 * self.level
                self.b2b_bonus = False
                self.set_msg.triple += 1
            elif cleared_lines == 4:
                awarded_line = 4
                score2add = 800 * self.level
                self.set_msg.tetris += 1

        # if b2b, line clear bonus * 1.5 abd score * 1.5
        if bonus and self.b2b_bonus:
            self.lines_for_level += int((awarded_line + cleared_lines) * 1.5)
            self.score += int(1.5 * score2add)

        else:
            self.lines_for_level += awarded_line + cleared_lines
            self.score += score2add

        self.lines += cleared_lines

        if self.game_mode == GameMode._150_ROWS and self.lines >= 150:
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

        self.generate_new_tetrimino()

        self.lock_down_timer = 0
        self.lock_down_move_counter = 0
        self.hold_once = False

        # show notice
        notice = ""
        if is_t_spin:
            if cleared_lines == 0:
                notice = "T-Spin!"
            elif cleared_lines == 1:
                notice = "T-Spin Single!"
            elif cleared_lines == 2:
                notice = "T-Spin Double!"
            elif cleared_lines == 3:
                notice = "T-Spin Triple!"
        elif cleared_lines == 1:
            notice = "Single!"
        elif cleared_lines == 2:
            notice = "Double!"
        elif cleared_lines == 3:
            notice = "Triple!"
        elif cleared_lines == 4:
            notice = "Tetris!"

        if notice:
            if self.b2b_bonus and bonus:
                notice += " B2B!"
            self.set_notice(notice)

    def handle_lock_down(self) -> None:
        """handle lock down"""
        if self.check_can_move_down():
            return
        else:
            # reset when move and rotate successfully
            self.lock_down_timer += self.tick

        if self.lock_down_timer >= 0.5:
            self.lock_down()

    def handle_shadow(self):
        """handle shadow tetrimino"""
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

    def handle_digging_mode(self) -> None:
        """for digging mode, auto add one line at the bottom of the board in fixed time"""
        self.line_increment_timer += self.tick

        if self.game_mode != GameMode.DIGGING or self.line_increment_timer < 5:
            return
        self.line_increment_timer = 0

        # add one line at the bottom of the board
        self.board.pop(0)

        # randomly set some empty cells
        new_line = [
            list(TetriminoShape)[random.randint(0, len(TetriminoShape) - 1)].value
            for _ in range(self.BOARD_WIDTH)
        ]

        indexes = list(range(self.BOARD_WIDTH))
        random.shuffle(indexes)

        for i in range(random.randint(1, 5)):
            new_line[indexes[i]] = EMPTY

        self.board.append(new_line)

    def game_loop(self) -> None:
        """main game loop"""
        while not self.game_over:
            self.handle_input()
            time.sleep(self.tick)
            self.draw()

            if not self.paused:
                self.normal_fall()
                self.handle_lock_down()
                self.handle_shadow()
                self.handle_digging_mode()

    def init_color(self) -> None:
        if curses.COLORS > 16 and curses.can_change_color():
            # the color 0~7 is the default terminal color, use 8 or higher
            curses.init_color(TetriminoShape.I.value + 7, 0, 941, 941)  # cyan
            curses.init_color(TetriminoShape.O.value + 7, 941, 941, 0)  # yellow
            curses.init_color(TetriminoShape.T.value + 7, 627, 0, 941)  # purple
            curses.init_color(TetriminoShape.L.value + 7, 941, 627, 0)  # orange
            curses.init_color(TetriminoShape.J.value + 7, 0, 0, 941)  # blue
            curses.init_color(TetriminoShape.S.value + 7, 0, 941, 0)  # green
            curses.init_color(TetriminoShape.Z.value + 7, 941, 0, 0)  # red
            for tetrimino in list(TetriminoShape):
                curses.init_pair(
                    tetrimino.value, tetrimino.value + 7, tetrimino.value + 7
                )
        else:
            for tetrimino in list(TetriminoShape):
                curses.init_pair(tetrimino.value, tetrimino.value, tetrimino.value)

    def init_game(self) -> None:
        """init the game"""
        self.init_bag()
        self.generate_new_tetrimino()
        self.init_color()
        self.stdscr.timeout(0)

    def main(self) -> SettlementMessage:
        self.init_game()
        self.game_loop()

        # return the settlement message
        self.set_msg.lines = self.lines
        self.set_msg.score = self.score

        return self.set_msg
