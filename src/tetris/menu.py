import curses
from enum import Enum
import time

from . import WINDOW_ROWS, WINDOW_COLS
from .utils import get_version


class Sections(Enum):
    _150_ROWS = 0
    CASUAL = 1
    ENDLESS = 2
    DIGGING = 3
    QUIT = 4


class Menu:
    def __init__(self, stdscr: curses.window) -> None:
        self.stdscr = stdscr

        self.title_window = curses.newwin(6, WINDOW_COLS)
        self.sections_window = curses.newwin(WINDOW_ROWS - 8, WINDOW_COLS, 6, 0)
        self.version_window = curses.newwin(2, WINDOW_COLS, WINDOW_ROWS - 2, 0)

        self.title_window.border(
            0, 0, 0, ord(" "), 0, 0, curses.ACS_VLINE, curses.ACS_VLINE
        )
        self.sections_window.border(
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

        self.sections = [section.name.replace("_", " ").strip() for section in Sections]
        self.cur_section = 0
        self.confirm = False

    def draw_title(self) -> None:
        """draw title"""
        window = self.title_window
        _, width = window.getmaxyx()
        window.addstr(2, 1, f"{'╺┳━┳━━┳━┳━┳┳┳━╸  ╺┳━┳━┏━┓┏┳┓┳┏┓┏━┓╻ ':^{width - 2}}")
        window.addstr(3, 1, f"{' ┃ ┣━ ┃ ┣┳┛┃┗━┓   ┃ ┣━┣┳┛┃┃┃┃┃┃┣━┫┃ ':^{width - 2}}")
        window.addstr(4, 1, f"{' ╹ ┗━ ╹ ╹┗╸┻╺━┛   ╹ ┗━┛┗━┛╹┗┻┛┗┛ ╹┗╸':^{width - 2}}")
        window.refresh()

    def draw_sections(self) -> None:
        """draw sections"""
        window = self.sections_window
        height, width = window.getmaxyx()
        height -= 2
        width -= 2
        start_row = (height - len(self.sections) * 2) // 2 + 1

        for i, section in enumerate(self.sections):
            if i == self.cur_section:
                window.addstr(
                    start_row + i * 2, 1, f"{section:^{width}}", curses.A_REVERSE
                )
            else:
                window.addstr(start_row + i * 2, 1, f"{section:^{width}}")

        window.refresh()

    def draw_version(self) -> None:
        """draw version"""
        window = self.version_window
        _, width = window.getmaxyx()

        notice = "tab, ↑, ↓ to select, enter to confirm"

        window.addstr(0, 1, f"{notice:^{width - 2}}")
        window.refresh()

    def draw(self) -> None:
        self.draw_title()
        self.draw_sections()
        self.draw_version()

    def handle_input(self) -> None:
        c = self.stdscr.getch()
        if c == ord("\n"):
            self.confirm = True
        if c == curses.KEY_UP:
            self.cur_section = (self.cur_section - 1) % len(self.sections)
        if c == curses.KEY_DOWN or c == ord("\t"):
            self.cur_section = (self.cur_section + 1) % len(self.sections)

    def loop(self) -> None:
        while not self.confirm:
            self.handle_input()
            self.draw()

    def main(self) -> int:
        self.stdscr.timeout(0)
        self.loop()
        return self.cur_section


if __name__ == "__main__":
    def wrapper(stdscr: curses.window) -> int:
        curses.curs_set(0)
        curses.use_default_colors()
        return Menu(stdscr).main()

    print(curses.wrapper(wrapper))
