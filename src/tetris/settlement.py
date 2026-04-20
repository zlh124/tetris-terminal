"""settlement display ui"""

import curses

from tetris.constants import WINDOW_COLS, WINDOW_ROWS


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

        messages = self.set_msg.format(width)

        start_row = (height - len(messages)) >> 1

        if self.set_msg.game_mode == "TIME ATTACK":
            title = "TIME UP!"
            window.addstr(start_row - 1, 1, f"{title:^{width}}")

        for i, line in enumerate(messages):
            window.addstr(i + start_row + 1, 1, line)

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
