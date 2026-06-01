"""game menu, mode selection"""

import curses


from .config import Config
from .enums import Sections
from .network import NetworkClient
from .utils import clear_win_without_border, draw_win_border, get_version


class Menu:
    def __init__(self, stdscr: curses.window, config: Config) -> None:
        self.stdscr = stdscr
        self.config = config

        d = config.display
        self.title_window = curses.newwin(6, d.window_cols)
        self.sections_window = curses.newwin(d.window_rows - 8, d.window_cols, 6, 0)
        self.notice_window = curses.newwin(2, d.window_cols, d.window_rows - 2, 0)

        self.sections = [str(section) for section in Sections]
        self.cur_section = 0
        self.confirm = False

    def versus_lobby(self) -> NetworkClient | None:
        """Connect to a multiplayer server and wait for an opponent.

        Shows status messages on *stdscr* which should already be cleared.
        Returns a connected :class:`NetworkClient` on success, or ``None``.
        """
        network = NetworkClient()
        win = self.sections_window
        clear_win_without_border(win)
        host, port = (
            self.config.multi_play.host,
            self.config.multi_play.port,
        )

        x, y = win.getmaxyx()
        x -= 2
        y -= 2

        win.addstr(5, 1, f"Connecting to {host}:{port}...".center(y))
        win.refresh()

        try:
            network.handshake(host, port, get_version())
        except OSError | RuntimeError:
            win.addstr(7, 1, f"Failed to connect.".center(y))
            win.addstr(9, 1, "Press any key to return...".center(y))
            win.refresh()
            win.getch()
            return None

        # handshake blocks until hello_ok; now wait for an opponent
        dots = 0
        while True:
            msg = network.recv(timeout=0.5)
            if msg is not None and msg.get("type") == "match_found":
                network.opponent_id = msg["data"]["opponent_id"]
                break
            dots = (dots + 1) % 4
            win.addstr(7, 1, f"Waiting for opponent{'.' * dots}".center(y))
            win.addstr(9, 1, f"Press 'q' to cancel.".center(y))
            if self.stdscr.getch() == ord("q"):
                network.send({"type": "leave_queue", "data": {}})
                network.close()
                return None
            win.refresh()

        return network

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
        width -= 2

        window.addstr(2, 1, "╺┳━┳━━┳━┳━┳┳┳━╸  ╺┳━┳━┏━┓┏┳┓┳┏┓┏━┓╻ ".center(width))
        window.addstr(3, 1, " ┃ ┣━ ┃ ┣┳┛┃┗━┓   ┃ ┣━┣┳┛┃┃┃┃┃┃┣━┫┃ ".center(width))
        window.addstr(4, 1, " ╹ ┗━ ╹ ╹┗╸┻╺━┛   ╹ ┗━┛┗━┛╹┗┻┛┗┛ ╹┗╸".center(width))
        window.refresh()

    def draw_sections(self) -> None:
        """draw sections"""
        window = self.sections_window
        height, width = window.getmaxyx()
        height -= 2
        width -= 2

        spaces = (height - len(self.sections)) // (len(self.sections) - 1)
        start_row = (
            (height - len(self.sections) - spaces * (len(self.sections) - 1)) >> 1
        ) + 1

        for i, section in enumerate(self.sections):
            if i == self.cur_section:
                window.addstr(
                    spaces * i + start_row + i,
                    1,
                    section.center(width),
                    curses.A_REVERSE,
                )
            else:
                window.addstr(spaces * i + start_row + i, 1, section.center(width))

        window.refresh()

    def draw_notice(self) -> None:
        """draw version"""
        window = self.notice_window
        _, width = window.getmaxyx()

        notice = "tab, ↑, ↓ to select, enter to confirm"

        window.addstr(0, 1, notice.center(width - 2))
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

    def loop(self) -> None | NetworkClient:
        while not self.confirm:
            self.handle_input()
            self.draw()

        if self.confirm and Sections(self.cur_section) == Sections.VERSUS:

            network = self.versus_lobby()
            if network is None:
                self.confirm = False
                clear_win_without_border(self.sections_window)
                self.loop()
            return network

    def main(self) -> tuple[int, NetworkClient | None]:
        self.stdscr.timeout(100)
        network = self.loop()
        return self.cur_section, network
