"""Settlement (game-over statistics) display UI."""

from __future__ import annotations

import curses

from .config import Config
from .utils import draw_win_border


class SettlementMessage:
    """Container for end-of-game statistics.

    Holds all the counters collected during a game session and formats
    them into a list of centred lines suitable for terminal display.

    Attributes:
        title: The settlement title (e.g. ``"GAME OVER"``, ``"YOU WIN!"``).
    """

    def __init__(
        self,
        title: str,
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
        self.title = title
        self._score = score
        self._lines = lines
        self._time = time
        self._game_mode = game_mode

        # Line clear counts
        self._single = single
        self._double = double
        self._triple = triple
        self._tetris = tetris

        # T-Spin counts
        self._t_spin = t_spin
        self._t_spin_single = t_spin_single
        self._t_spin_double = t_spin_double
        self._t_spin_triple = t_spin_triple
        self._mini_t_spin = mini_t_spin
        self._mini_t_spin_single = mini_t_spin_single

    def format(self, width: int) -> list[str]:
        """Format all statistics into centred lines fitting within *width*.

        Args:
            width: Available display width in columns.

        Returns:
            List of centred strings, each no wider than *width*.
        """
        harfw = width >> 1
        if self._game_mode:
            msgs = [f"Mode: {self._game_mode}"]
        else:
            msgs: list[str] = []
        msgs += [
            f"Score: {self._score}",
            f"Lines: {self._lines}",
            f"Time: {self._time}",
            f"Single: {self._single}",
            f"Double: {self._double}",
            f"Triple: {self._triple}",
            f"Tetris: {self._tetris}",
            f"T-Spin: {self._t_spin}",
            f"T-Spin Single: {self._t_spin_single}",
            f"T-Spin Double: {self._t_spin_double}",
            f"T-Spin Triple: {self._t_spin_triple}",
            f"Mini-T-Spin: {self._mini_t_spin}",
            f"Mini-T-Spin Single: {self._mini_t_spin_single}",
        ]
        i = 0
        res: list[str] = []
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
    """Game-over statistics screen.

    Renders the :class:`SettlementMessage` inside a bordered window and
    lets the player choose to retry or quit.
    """

    def __init__(
        self, stdscr: curses.window, set_msg: SettlementMessage, config: Config
    ) -> None:
        self._stdscr = stdscr
        self._set_msg = set_msg
        self._config = config

        d = config.display
        self._title_window = curses.newwin(6, d.window_cols)
        self._show_window = curses.newwin(d.window_rows - 8, d.window_cols, 6, 0)
        self._notice_window = curses.newwin(2, d.window_cols, d.window_rows - 2, 0)

    def _draw_border(self) -> None:
        """Draw the outer borders for all settlement sub-windows."""
        title_win = self._title_window
        show_win = self._show_window
        notice_win = self._notice_window

        d = self._config.display
        draw_win_border(title_win, d, bs="", bl=d.bd_v, br=d.bd_v)
        draw_win_border(show_win, d, tl=d.bd_vr, tr=d.bd_vl, bl=d.bd_vr, br=d.bd_vl)
        draw_win_border(notice_win, d, ts="", tl=d.bd_v, tr=d.bd_v)

        title_win.refresh()
        show_win.refresh()

    def _draw_title(self) -> None:
        """Render the "GAME OVER" ASCII-art title."""
        window = self._title_window
        _, width = window.getmaxyx()
        width -= 2

        window.addstr(2, 1, "┏━┓┏━┓┏┳┓┏━   ┏━┓╻ ╻┏━┏━┓".center(width))
        window.addstr(3, 1, "┃ ┳┣━┫┃┃┃┣━   ┃ ┃┗┓┃┣━┣┳┛".center(width))
        window.addstr(4, 1, "┗━┛╹ ╹╹╹╹┗━   ┗━┛ ┗┛┗━┛┗╸".center(width))
        window.refresh()

    def _draw_show(self) -> None:
        """Render the settlement statistics."""
        window = self._show_window
        height, width = window.getmaxyx()
        height -= 2
        width -= 2

        messages = self._set_msg.format(width)

        start_row = (height - len(messages)) >> 1

        window.addstr(start_row - 1, 1, self._set_msg.title.center(width))

        for i, line in enumerate(messages):
            window.addstr(i + start_row + 1, 1, line)

        window.refresh()

    def _draw_notice(self) -> None:
        """Render the footer notice (quit / retry)."""
        window = self._notice_window
        _, width = window.getmaxyx()

        notice = "'q' to quit, 'r' to retry."

        window.addstr(0, 1, notice.center(width - 2))
        window.refresh()

    def _draw(self) -> None:
        """Redraw the entire settlement screen."""
        self._draw_border()
        self._draw_title()
        self._draw_show()
        self._draw_notice()

    def _loop(self) -> int:
        """Input loop for the settlement screen.

        Returns:
            ``1`` if the player chose to retry, ``0`` to quit.
        """
        while True:
            self._draw()
            c = self._stdscr.getch()
            if c == ord("r") or c == ord("R"):
                return 1
            elif c == ord("q") or c == ord("Q"):
                return 0

    def main(self) -> int:
        """Run the settlement screen.

        Returns:
            ``1`` if the player chose to retry, ``0`` to quit.
        """
        self._stdscr.timeout(-1)
        return self._loop()
