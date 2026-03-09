"""settlement display ui"""

import curses
from .tetris import WINDOW_ROWS, WINDOW_COLS
from .tetris import SettlementMessage


class Settlement:
    def __init__(self, stdscr: curses.window, set_msg: SettlementMessage) -> None:
        self.stdscr = stdscr
        self.set_msg = set_msg

        self.title_window = curses.newwin(6, WINDOW_COLS)
        self.show_window = curses.newwin(WINDOW_ROWS - 8, WINDOW_COLS, 6, 0)
        self.version_window = curses.newwin(2, WINDOW_COLS, WINDOW_ROWS - 2, 0)

        self.title_window.border(
            0, 0, 0, ord(" "), 0, 0, curses.ACS_VLINE, curses.ACS_VLINE
        )
        self.show_window.border(
            0,
            0,
            0,
            0,
            curses.ACS_LTEE,
            curses.ACS_RTEE,
            curses.ACS_LTEE,
            curses.ACS_RTEE,
        )
        self.version_window.border(
            0, 0, ord(" "), 0, curses.ACS_VLINE, curses.ACS_VLINE
        )

    def draw_title(self) -> None:
        """draw title"""
        window = self.title_window
        _, width = window.getmaxyx()
        window.addstr(2, 1, f"{'┏━┓┏━┓┏┳┓┏━   ┏━┓╻ ╻┏━┏━┓':^{width - 2}}")
        window.addstr(3, 1, f"{'┃ ┳┣━┫┃┃┃┣━   ┃ ┃┗┓┃┣━┣┳┛':^{width - 2}}")
        window.addstr(4, 1, f"{'┗━┛╹ ╹╹╹╹┗━   ┗━┛ ┗┛┗━┛┗╸':^{width - 2}}")
        window.refresh()

    def draw_show(self) -> None:
        """draw sections"""
        window = self.show_window
        height, width = window.getmaxyx()
        height -= 2
        width -= 2

        messages = self.set_msg.format(width - 2)
        for i, line in enumerate(messages):
            window.addstr(i * 2 + (height - 2 * len(messages)) // 2 + 1, 1, line)

        window.refresh()

    def draw_version(self) -> None:
        """draw version"""
        window = self.version_window
        _, width = window.getmaxyx()

        notice = "'q' to quit, 'r' to retry."

        window.addstr(0, 1, f"{notice:^{width - 2}}")
        window.refresh()

    def draw(self) -> None:
        self.draw_title()
        self.draw_show()
        self.draw_version()

    def loop(self) -> int:
        while True:
            self.draw()
            c = self.stdscr.getch()
            if c == ord("r") or c == ord("R"):
                return 1
            elif c == ord("q") or c == ord("Q"):
                return 0

    def main(self) -> int:
        self.stdscr.timeout(-1)
        return self.loop()
