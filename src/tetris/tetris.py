"""Main game rendering and input handling.

Provides the :class:`Tetris` class that wraps a :class:`TetrisCore` with
a full curses UI: board drawing, preview, hold, info panel, and input
dispatch. Also handles network polling for versus mode.
"""

from __future__ import annotations

import curses
import time

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .network import NetworkClient

from .config import Config
from .constants import (
    EXIT,
    HARD_DROP,
    HOLD,
    MOVE_LEFT,
    MOVE_RIGHT,
    PAUSE,
    ROTATE_CCW,
    ROTATE_CW,
    SHAPE_TABLE,
    SHOW_OFFSET,
    SOFT_DROP,
)
from .enums import GameMode, TetriminoShape, WebClientMsgType
from .settlement import SettlementMessage
from .utils import draw_win_border, clear_win_without_border
from .core import TetrisCore


class Tetris:
    """Top-level game loop with curses rendering and input handling.

    Wraps a :class:`TetrisCore` and manages the terminal UI: board,
    preview, hold, info panel, and (in versus mode) the opponent's board.
    """

    def __init__(
        self,
        stdscr: curses.window,
        game_mode: GameMode,
        config: Config,
        network: NetworkClient | None = None,
    ) -> None:
        self._core = TetrisCore(
            game_mode, config, self._do_lock_down, self._do_game_over
        )

        self._stdscr = stdscr
        self._game_mode = game_mode
        self._config = config

        # Multiplayer
        self._network = network
        self._player_id: str = ""
        self._opponent_id: str = ""

        self._hold_window = curses.newwin(7, 12, 2, 0)
        self._info_window = curses.newwin(15, 12, 9, 0)
        self._board_window = curses.newwin(22, 21, 2, 12)
        self._preview_window = curses.newwin(22, 12, 2, 32)

        if self._game_mode == GameMode.VERSUS:
            self._header_window = curses.newwin(2, 65, 0, 0)
            self._rival_window: curses.window | None = curses.newwin(22, 21, 2, 44)
            self._footer_window = curses.newwin(2, 65, 24, 0)
        else:
            self._header_window = curses.newwin(2, 44, 0, 0)
            self._rival_window = None
            self._footer_window = curses.newwin(2, 44, 24, 0)

        self._game_over = False
        self._set_msg: SettlementMessage | None = None

    def _draw_border(self) -> None:
        """Draw all window borders, adapting layout for versus mode."""
        header_win = self._header_window
        hold_win = self._hold_window
        info_win = self._info_window
        board_win = self._board_window
        preview_win = self._preview_window
        footer_win = self._footer_window
        rival_win = self._rival_window

        d = self._config.display
        if self._game_mode == GameMode.VERSUS:
            if rival_win:
                draw_win_border(
                    rival_win, d, ls="", tl=d.bd_h, tr=d.bd_vl, bl=d.bd_h, br=d.bd_vl
                )
                rival_win.refresh()
            draw_win_border(
                preview_win, d, tl=d.bd_hb, tr=d.bd_hb, bl=d.bd_ht, br=d.bd_ht
            )
        else:
            draw_win_border(
                preview_win, d, tl=d.bd_hb, tr=d.bd_vl, bl=d.bd_ht, br=d.bd_vl
            )

        draw_win_border(header_win, d, bl=d.bd_v, br=d.bd_v)
        draw_win_border(hold_win, d, tl=d.bd_vr, tr=d.bd_hb, bl=d.bd_vr, br=d.bd_vl)
        draw_win_border(
            info_win, d, ts="", tl=d.bd_v, tr=d.bd_v, bl=d.bd_vr, br=d.bd_ht
        )
        draw_win_border(board_win, d, ls="", tl=d.bd_h, tr="", bl=d.bd_h, br=d.bd_ht)
        draw_win_border(footer_win, d, ts="", tl=d.bd_v, tr=d.bd_v)

    def _draw_rival(self, board: list[list[int]]) -> None:
        """Render the opponent's board in the versus panel.

        Args:
            board: A 2D list of shape values from ``serialize_board()``.
        """
        window = self._rival_window
        if window is None:
            return

        _, width = window.getmaxyx()

        width -= 1

        for i in range(20, self._config.game_rules.board_height):
            line = i - 19
            for j in range(self._config.game_rules.board_width):
                cell = TetriminoShape(board[i][j])
                window.addstr(
                    line,
                    2 * j,
                    (
                        self._config.display.solid_cell
                        if cell != TetriminoShape.EMPTY
                        else self._config.display.empty_cell
                    ),
                    self._get_color(cell),
                )

        window.noutrefresh()

    def _draw_header(self) -> None:
        """Render the game-mode label in the header bar."""
        window = self._header_window

        _, width = window.getmaxyx()
        width -= 2

        window.addstr(1, 1, str(self._game_mode).center(width))
        window.noutrefresh()

    def _draw_board(self) -> None:
        """Render the playfield, including the active piece, shadow, and
        line-clear animation."""
        window = self._board_window
        _, width = window.getmaxyx()

        width -= 1

        if self._core.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")

        cur = self._core.cur_tetrimino
        cleared_lines: set[int] = set()

        for i in range(20, self._config.game_rules.board_height):
            line = i - 19
            for j in range(self._config.game_rules.board_width):
                cell = self._core.board[i][j]
                if cell == TetriminoShape.CLEAR:
                    cleared_lines.add(i)
                window.addstr(
                    line,
                    2 * j,
                    (
                        self._config.display.solid_cell
                        if cell != TetriminoShape.EMPTY
                        else self._config.display.empty_cell
                    ),
                    self._get_color(cell),
                )
                if (i, j) in self._core.shadow:
                    window.addstr(
                        line,
                        2 * j,
                        self._config.display.shadow_cell,
                        self._get_color(
                            TetriminoShape.CLEAR if i in cleared_lines else cur.shape
                        ),
                    )
                if (i, j) in cur:
                    window.addstr(
                        line,
                        2 * j,
                        self._config.display.solid_cell,
                        self._get_color(
                            TetriminoShape.CLEAR if i in cleared_lines else cur.shape
                        ),
                    )

        window.noutrefresh()

    def _draw_preview(self) -> None:
        """Render the next-piece preview panel."""
        window = self._preview_window
        height, width = window.getmaxyx()
        height -= 1
        width -= 2

        # Next row 1~height, col 0~10:
        window.addstr(1, 1, " Next:".ljust(width))
        # each preview takes 3 rows and 8 cols
        s_col = 2
        # clear the preview area
        clear_win_without_border(window, 2)

        # draw the preview
        for i, s_row in enumerate(range(2, height - 1, 3)):
            shape = self._core.bag[i].shape
            dx, dy = SHOW_OFFSET[shape]
            for x, y in SHAPE_TABLE[shape]:
                window.addstr(
                    s_row + x + dx,
                    s_col + (y + dy) * 2,
                    self._config.display.solid_cell,
                    self._get_color(shape),
                )

        window.noutrefresh()

    def _draw_hold(self) -> None:
        """Render the hold piece panel."""
        window = self._hold_window
        height, width = window.getmaxyx()
        height -= 1
        width -= 2

        window.addstr(1, 1, " Hold:".ljust(width))
        # clear the hold area
        clear_win_without_border(window, 2)

        if self._core.hold:
            shape = self._core.hold.shape
            s_row = 2
            s_col = 2
            dx, dy = SHOW_OFFSET[shape]
            for x, y in SHAPE_TABLE[shape]:
                window.addstr(
                    s_row + x + dx,
                    s_col + (y + dy) * 2,
                    self._config.display.solid_cell,
                    self._get_color(shape),
                )

        window.noutrefresh()

    def _draw_info(self) -> None:
        """Render the info panel (time, score, lines, level, garbage)."""
        window = self._info_window
        height, width = window.getmaxyx()

        height -= 1
        width -= 2

        # clear the info area
        clear_win_without_border(window, 1)

        window.addstr(2, 1, "Time:".ljust(width))
        if self._game_mode == GameMode.TIME_ATTACK:
            window.addstr(3, 1, self._core.time_remaining.rjust(width))
        else:
            window.addstr(3, 1, self._core.game_time_str.rjust(width))
        window.addstr(4, 1, "Score:".ljust(width))
        window.addstr(5, 1, str(self._core.score).rjust(width))
        window.addstr(6, 1, "Lines:".ljust(width))
        window.addstr(7, 1, str(self._core.lines).rjust(width))
        window.addstr(8, 1, "Level:".ljust(width))
        window.addstr(9, 1, str(self._core.level).rjust(width))

        if self._game_mode in (GameMode.VERSUS, GameMode.DIGGING):
            window.addstr(10, 1, "Garbage:".ljust(width))
            window.addstr(11, 1, str(self._core.garbage_queue).rjust(width))

        window.noutrefresh()

    def _draw_footer(self) -> None:
        """Render the notice / status bar."""
        window = self._footer_window
        height, width = window.getmaxyx()

        height -= 1
        width -= 2

        # notice
        window.addstr(0, 1, " " * width)

        notice = self._core.get_notice()
        if notice:
            window.addstr(0, 1, notice.center(width))

        window.noutrefresh()

    def _draw(self, dt: float) -> None:
        """Update all visible windows, throttled to ``fps``.

        Args:
            dt: Delta time since last call (seconds).
        """
        self._core.frame_timer += dt
        if self._core.frame_timer < 1 / self._config.timing.fps:
            return
        self._core.frame_timer = 0

        self._draw_border()
        self._draw_header()
        self._draw_board()
        self._draw_preview()
        self._draw_hold()
        self._draw_info()
        self._draw_footer()

        curses.doupdate()

    def _handle_input(self) -> None:
        """Read one terminal key-press and dispatch to the game core."""
        c = self._stdscr.getch()

        # versus mode is not pauseable
        if c in PAUSE:
            self._core.toggle_pause()
        if c in EXIT:
            self._core.forced_game_over("game over!")
        if not self._core.controllable():
            return
        if c in MOVE_LEFT:
            self._core.do_move_left()
        if c in MOVE_RIGHT:
            self._core.do_move_right()
        if c in SOFT_DROP:
            self._core.do_soft_drop()
        if c in ROTATE_CW:
            self._core.do_rotate_cw()
        if c in ROTATE_CCW:
            self._core.do_rotate_ccw()
        if c in HARD_DROP:
            self._core.do_hard_drop()
        if c in HOLD:
            self._core.do_hold()

    def _do_game_over(self, set_title: str, set_msg: SettlementMessage) -> None:
        """Callback invoked by the core when the game ends.

        Args:
            set_title: The settlement title (e.g. ``"GAME OVER"``).
            set_msg: Pre-populated :class:`SettlementMessage`.
        """
        self._game_over = True
        self._set_msg = set_msg
        self._set_msg.title = set_title

    def _do_lock_down(self, garbage_lines: int) -> None:
        """Callback invoked by the core after every lock-down.

        Sends garbage lines and the updated board to the opponent over
        the network.

        Args:
            garbage_lines: Number of garbage lines to send.
        """
        if not self._network:
            return

        if garbage_lines > 0:
            self._network.send(
                {"type": WebClientMsgType.GARBAGE, "data": {"lines": garbage_lines}}
            )
        self._network.send(
            {
                "type": WebClientMsgType.BOARD,
                "data": {"board": self._core.serialize_board()},
            }
        )

    def _handle_network(self) -> None:
        """Poll for incoming network messages and dispatch them.

        Handles garbage, board updates, game-over notifications, and
        opponent disconnects.
        """
        if self._network is None:
            return
        msg = self._network.recv(timeout=0)
        if msg is None:
            if not self._network.connected:
                self._core.forced_game_over("Opponent disconnected!")
            return
        msg_type = msg.get("type", -1)
        if msg_type == WebClientMsgType.GARBAGE:
            lines: int = msg["data"]["lines"]
            self._core.add_garbage_lines(lines)
        elif msg_type == WebClientMsgType.BOARD:
            self._draw_rival(msg["data"]["board"])
        elif msg_type in (
            WebClientMsgType.GAME_OVER,
            WebClientMsgType.OPPONENT_DISCONNECTED,
        ):
            self._core.forced_game_over("You Win!")

    def _game_loop(self) -> None:
        """Main game loop with fixed-timestep accumulator.

        Runs until :attr:`_game_over` is set, processing input, network
        messages, and fixed-step core updates at ``fps``.
        """
        FIXED_DT: float = 1.0 / self._config.timing.fps
        MAX_FRAME_TIME: float = 0.25

        accumulator: float = 0.0
        last_time = time.perf_counter()

        while not self._game_over:
            current_time = time.perf_counter()
            frame_time = current_time - last_time
            last_time = current_time

            if frame_time > MAX_FRAME_TIME:
                frame_time = MAX_FRAME_TIME

            self._handle_input()
            self._handle_network()

            if not self._core.paused:
                accumulator += frame_time
                while accumulator >= FIXED_DT:
                    self._core.process(FIXED_DT)
                    accumulator -= FIXED_DT

            self._draw(frame_time)
            time.sleep(0.002)

    def _init_color(self) -> None:
        """Initialise terminal colour pairs for each tetrimino shape.

        Uses extended colours (8+) when the terminal supports them;
        otherwise falls back to the default 8-colour palette.
        """
        colorful = curses.COLORS > 16 and curses.can_change_color()
        if colorful:
            # the color 0~7 is the default terminal color, use 8 or higher
            # fmt: off
            curses.init_color(TetriminoShape.I.value + 7, 0,   941, 941)  # cyan
            curses.init_color(TetriminoShape.O.value + 7, 941, 941, 0)    # yellow
            curses.init_color(TetriminoShape.T.value + 7, 627, 0,   941)  # purple
            curses.init_color(TetriminoShape.L.value + 7, 941, 627, 0)    # orange
            curses.init_color(TetriminoShape.J.value + 7, 0,   0,   941)  # blue
            curses.init_color(TetriminoShape.S.value + 7, 0,   941, 0)    # green
            curses.init_color(TetriminoShape.Z.value + 7, 941, 0,   0)    # red
            # fmt: on
        for tetrimino in TetriminoShape.normal_tetriminos():
            curses.init_pair(
                tetrimino.value,
                tetrimino.value + 7 if colorful else tetrimino.value,
                -1,
            )
        curses.init_pair(TetriminoShape.CLEAR.value, curses.COLOR_WHITE, -1)

    def _get_color(self, shape: TetriminoShape) -> int:
        """Return the curses colour attribute for a given shape.

        Args:
            shape: The tetrimino shape.

        Returns:
            A ``curses.color_pair(...)`` for normal shapes, or
            ``A_REVERSE`` for GARBAGE. CLEAR cells alternate between
            the colour pair and ``A_REVERSE`` for a flashing effect.
        """
        if shape == TetriminoShape.CLEAR:
            if (
                self._core.game_time // self._config.timing.clear_anim_flash_interval
            ) % 2:
                return curses.color_pair(shape.value)
            else:
                return curses.A_REVERSE

        if shape != TetriminoShape.GARBAGE:
            return curses.color_pair(shape.value)
        return 0

    def _init_game(self) -> None:
        """Initialise colours and set stdin non-blocking."""
        self._init_color()
        self._stdscr.timeout(0)

    def main(self) -> SettlementMessage:
        """Initialise and run the game.

        Returns:
            The :class:`SettlementMessage` collected during this session.

        Raises:
            RuntimeError: If no settlement message was produced.
        """
        self._init_game()
        self._game_loop()

        # Notify opponent and clean up network
        if self._network:
            self._network.send({"type": WebClientMsgType.GAME_OVER, "data": {}})
            self._network.close()

        self._stdscr.clear()
        self._stdscr.refresh()

        # return the settlement message
        if not self._set_msg:
            raise RuntimeError("Settlement Message is None")

        return self._set_msg
