#!/usr/bin/python3
import curses
import time

from collections import deque
from copy import copy
from random import randint, shuffle


class Tetris:
    x = 431424
    y = 598356
    r = 427089
    c = 348480
    p = 615696

    px = 247872
    py = 799248
    pr = 0

    tick = 0

    board = [[0] * 10 for _ in range(20)]

    piece_chars = ["Z", "S", "O", "J", "T", "I", "L"]

    block = [
        [x, y, x, y],
        [r, p, r, p],
        [c, c, c, c],
        [599636, 431376, 598336, 432192],
        [411985, 610832, 415808, 595540],
        [px, py, px, py],
        [614928, 399424, 615744, 428369],
    ]

    def __init__(self, stdscr: curses.window):
        self.stdscr = stdscr

    queue = deque(maxlen=14)

    score = 0
    lock_until = 0

    def now_ms(self) -> int:
        return int(time.time() * 1000)

    def reset_lock_delay(self) -> None:
        self.lock_until = 0

    def start_lock_delay(self) -> None:
        if not self.lock_until:
            self.lock_until = self.now_ms() + 500

    def NUM(self, x: int, y: int) -> int:
        return 3 & self.block[self.p][x] >> y

    def fill_bag(self) -> None:
        bag = list(range(7))
        shuffle(bag)
        while bag:
            self.queue.append(bag.pop())

    def init_queue(self) -> None:
        self.fill_bag()
        self.fill_bag()

    def next_from_queue(self) -> int:
        if len(self.queue) == 7:
            self.fill_bag()
        return self.queue.popleft()

    def new_piece(self) -> None:
        self.y = self.py = 0
        self.p = self.next_from_queue()
        self.r = self.pr = randint(0, 3)
        self.x = self.px = randint(0, 9 - self.NUM(self.r, 16))
        self.reset_lock_delay()

    def frame(self, stdscr: curses.window) -> None:
        stdscr.move(0, 3)
        stdscr.addstr("Next: ")
        for i in range(5):
            stdscr.addstr(f"{self.piece_chars[self.queue[i]]} ")

        for i in range(20):
            stdscr.move(i + 1, 1)
            for j in range(10):
                if self.board[i][j]:
                    stdscr.attron(262176 | self.board[i][j] << 8)
                stdscr.addstr("  ")
                stdscr.attroff(262176 | self.board[i][j] << 8)
        stdscr.move(21, 1)
        stdscr.addstr(f"Score: {self.score}")
        stdscr.refresh()

    def set_piece(self, x: int, y: int, r: int, v: int) -> None:
        for i in range(0, 8, 2):
            self.board[self.NUM(r, i * 2) + y][self.NUM(r, (i * 2) + 2) + x] = v

    def update_piece(self) -> None:
        self.set_piece(self.px, self.py, self.pr, 0)
        self.px, self.py, self.pr = self.x, self.y, self.r
        self.set_piece(self.x, self.y, self.r, self.p + 1)

    def remove_line(self) -> None:
        for row in range(self.y, self.y + self.NUM(self.r, 18) + 1):
            self.c = 1
            for i in range(10):
                self.c *= self.board[row][i]
            if not self.c:
                continue
            for i in range(row - 1, 0, -1):
                self.board[i + 1] = copy(self.board[i])
            self.board[0] = [0] * 10
            self.score += 1

    def check_hit(self, x: int, y: int, r: int) -> int:
        if y + self.NUM(r, 18) > 19:
            return 1
        self.set_piece(self.px, self.py, self.pr, 0)
        self.c = 0
        for i in range(0, 8, 2):
            if self.board[y + self.NUM(r, i * 2)][x + self.NUM(r, (i * 2) + 2)]:
                self.c += 1
        self.set_piece(self.px, self.py, self.pr, self.p + 1)
        return self.c

    def do_tick(self) -> int:
        self.tick += 1
        if self.tick > 30:
            self.tick = 0
            if not self.check_hit(self.x, self.y + 1, self.r):
                self.y += 1
                self.update_piece()
                self.reset_lock_delay()
            else:
                if not self.y:
                    return 0
                self.start_lock_delay()
                if self.now_ms() >= self.lock_until:
                    self.remove_line()
                    self.new_piece()
        if self.lock_until and self.now_ms() >= self.lock_until:
            if self.check_hit(self.x, self.y + 1, self.r):
                self.remove_line()
                self.new_piece()
            else:
                self.reset_lock_delay()
        return 1

    def runloop(self) -> None:
        while self.do_tick():
            time.sleep(0.01)
            c = self.stdscr.getch()
            if (
                c == ord("a")
                and self.x > 0
                and not self.check_hit(self.x - 1, self.y, self.r)
            ):
                self.x -= 1
            if (
                c == ord("d")
                and self.x + self.NUM(self.r, 16) < 9
                and not self.check_hit(self.x + 1, self.y, self.r)
            ):
                self.x += 1
            if c == ord("s"):
                while not self.check_hit(self.x, self.y + 1, self.r):
                    self.y += 1
                    self.update_piece()
                self.reset_lock_delay()
                self.remove_line()
                self.new_piece()
            if c == ord("w"):
                self.r += 1
                self.r %= 4
                while self.x + self.NUM(self.r, 16) > 9:
                    self.x -= 1
                if self.check_hit(self.x, self.y, self.r):
                    self.x = self.px
                    self.r = self.pr
            if c == ord("q"):
                return
            self.update_piece()
            self.frame(self.stdscr)

    def main(self) -> None:
        curses.start_color()
        self.init_queue()
        for i in range(1, 8):
            curses.init_pair(i, i, 0)
        self.new_piece()
        curses.resizeterm(22, 22)
        curses.noecho()
        curses.curs_set(0)
        self.stdscr.timeout(0)
        self.stdscr.box()
        self.runloop()
