import curses
import random

from collections import deque
from enum import Enum
import time
from typing import Deque

EMPTY = 0


class TetriminoShape(Enum):
    I = 1
    J = 2
    L = 3
    O = 4
    S = 5
    T = 6
    Z = 7


class Tetrimino:

    ## line0  0000000000 -
    ## ...               |  buffer zone
    ## line19 0000000000 -
    ## line20 0000000000 -
    ## ...               |   game zone
    ## line39 0000000000 -
    ## all the tetriminos are generated in the 18th and 19th line(buffer zone)

    shape_table = {
        TetriminoShape.I: [(19, 3), (19, 4), (19, 5), (19, 6)],
        TetriminoShape.J: [(18, 3), (19, 3), (19, 4), (19, 5)],
        TetriminoShape.L: [(19, 3), (19, 4), (19, 5), (18, 5)],
        TetriminoShape.O: [(18, 4), (18, 5), (19, 4), (19, 5)],
        TetriminoShape.S: [(19, 3), (19, 4), (18, 4), (19, 5)],
        TetriminoShape.T: [(19, 3), (19, 4), (18, 4), (19, 5)],
        TetriminoShape.Z: [(18, 3), (18, 4), (19, 4), (19, 5)],
    }

    def __init__(self, shape: TetriminoShape) -> None:
        self.shape = shape
        self.no = shape.value
        self.bodies = self.shape_table[shape][::]

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
    bag: Deque[Tetrimino] = deque(maxlen=14)

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
        tmp = [Tetrimino(TetriminoShape(i)) for i in range(1, 8)]
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
        return tetrimino

    def check_can_move_down(self):
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        for x, y in [
            pos
            for pos in self.cur_tetrimino
            if pos[0] == max(x for x, _ in self.cur_tetrimino)
        ]:
            if x + 1 >= 40 or self.board[x + 1][y] != 0:
                return False
        return True

    def check_can_move_left(self):
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        for x, y in [
            pos
            for pos in self.cur_tetrimino
            if pos[1] == min(y for _, y in self.cur_tetrimino)
        ]:
            if y - 1 < 0 or self.board[x][y - 1] != 0:
                return False
        return True

    def check_can_move_right(self):
        assert self.cur_tetrimino is not None, "cur_tetrimino is None"
        for x, y in [
            pos
            for pos in self.cur_tetrimino
            if pos[1] == max(y for _, y in self.cur_tetrimino)
        ]:
            if y + 1 >= 10 or self.board[x][y + 1] != 0:
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

    def normal_fall(self):
        self.normal_fall_timer += self.tick
        if self.normal_fall_timer < self.fall_speed:
            return
        self.normal_fall_timer = 0
        if not self.do_fall_immediate():
            self.cur_tetrimino = self.get_tetrimino()

    def soft_drop(self):
        # cancel normal fall
        self.normal_fall_timer = 0
        self.soft_drop_timer += self.tick
        if self.soft_drop_timer < self.soft_drop_speed:
            return
        self.soft_drop_timer = 0
        if not self.do_fall_immediate():
            self.cur_tetrimino = self.get_tetrimino()

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

    def handle_input(self):
        c = self.stdscr.getch()
        if c == ord("q"):
            self.failed = True
        if c == ord("a"):
            self.do_move_left()
        if c == ord("d"):
            self.do_move_right()
        if c == ord("s"):
            self.soft_drop()
    def game_loop(self):
        while not self.failed:
            self.normal_fall()
            self.draw_board()
            self.handle_input()
            time.sleep(self.tick)

    def init_game(self):
        self.init_bag()
        self.cur_tetrimino = self.get_tetrimino()

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
