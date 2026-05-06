"""game menu, mode selection"""

import curses

from tetris.config import Config
from tetris.enums import Sections
from tetris.utils import draw_win_border


class Menu:
    def __init__(self, stdscr: curses.window, config: Config) -> None:
        self.stdscr = stdscr
        self.config = config

        d = config.display
        self.title_window = curses.newwin(6, d.window_cols)
        self.sections_window = curses.newwin(d.window_rows - 8, d.window_cols, 6, 0)
        self.notice_window = curses.newwin(2, d.window_cols, d.window_rows - 2, 0)

        self.sections = [section.name.replace("_", " ").strip() for section in Sections]
        self.cur_section = 0
        self.confirm = False

    def draw_border(self) -> None:
        title_win = self.title_window
        sec_win = self.sections_window
        notice_win = self.notice_window

        d = self.config.display
        draw_win_border(title_win, d, bs="", bl=d.bd_v, br=d.bd_v)
        draw_win_border(sec_win, d, tl=d.bd_vr, tr=d.bd_vl, bl=d.bd_vr, br=d.bd_vl)
        draw_win_border(notice_win, d, ts="", tl=d.bd_v, tr=d.bd_v)

        title_win.refresh()
        sec_win.refresh()
        notice_win.refresh()

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

    def draw_notice(self) -> None:
        """draw version"""
        window = self.notice_window
        _, width = window.getmaxyx()

        notice = "tab, ↑, ↓ to select, enter to confirm"

        window.addstr(0, 1, f"{notice:^{width - 2}}")
        window.refresh()

    def draw(self) -> None:
        self.draw_border()
        self.draw_title()
        self.draw_sections()
        self.draw_notice()

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
        self.stdscr.timeout(100)
        self.loop()
        return self.cur_section
