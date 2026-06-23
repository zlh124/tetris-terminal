"""Main game logic — the TetrisCore engine.

Implements the full modern Tetris ruleset: 7-bag randomiser, SRS rotation
with wall kicks, lock-down mechanics, line-clear animation, scoring,
levelling, garbage system, T-Spin detection, and hold.
"""

from __future__ import annotations

import random
import time

from collections import deque
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Generator


from .config import Config
from .constants import (
    GENERATE_POSITION,
    ROTATE_TABLE,
    SHAPE_TABLE,
)
from .enums import Direction, GameMode, TetriminoShape
from .settlement import SettlementMessage


class Tetrimino:
    """A single tetrimino piece on the board.

    All pieces spawn in the buffer zone (rows 18-19), then fall into the
    visible game zone (rows 20-39).

    Attributes:
        direction: Current orientation of the piece.
        no: Numeric shape value (same as ``shape.value``).
        shape: The tetrimino shape identifier.
        bodies: List of ``(row, col)`` cells occupied by this piece.
    """

    def __init__(self, shape: TetriminoShape) -> None:
        self.direction: Direction = Direction.NORTH
        self.no: int = shape.value
        self.shape: TetriminoShape = shape
        dx, dy = GENERATE_POSITION[shape]
        self.bodies: list[tuple[int, int]] = [
            (x + dx, y + dy) for (x, y) in SHAPE_TABLE[shape]
        ]

    def __iter__(self) -> Generator[tuple[int, int], Any, None]:
        for x, y in self.bodies:
            yield x, y

    def __getitem__(self, index: int) -> tuple[int, int]:
        return self.bodies[index]

    def __setitem__(self, index: int, value: tuple[int, int]) -> None:
        self.bodies[index] = value


class TetrisCore:
    """Main game engine implementing modern Tetris rules.

    Call the methods below from the control / UI layer:

    **Lifecycle**
    ``process(time_delta)`` — advance game state by *dt* seconds
    ``controllable()`` — whether input should be dispatched
    ``toggle_pause()`` — pause / resume

    **Movement**
    ``do_move_left()`` / ``do_move_right()``
    ``do_rotate_cw()`` / ``do_rotate_ccw()``
    ``do_soft_drop()`` / ``do_hard_drop()``
    ``do_hold()``

    **Multiplayer**
    ``add_garbage_lines(count)`` — queue incoming garbage
    ``serialize_board()`` — export board for network sync

    **Status**
    ``get_notice()`` — current action label (e.g. "Tetris!")
    ``forced_game_over(title)`` — end the game immediately

    **Callbacks**
    ``lock_down_callback(garbage_lines)`` — called after each lock-down
    ``game_over_callback(title, settlement)`` — called when the game ends

    **Properties**
    ``game_time``, ``game_time_str``, ``time_remaining``,
    ``cur_tetrimino``, ``board``, ``bag``, ``hold``,
    ``frame_timer``, ``score``, ``lines``, ``level``,
    ``shadow``, ``garbage_queue``, ``paused``.
    """

    class Movement(Enum):
        """Type of last successful move (for T-Spin detection)."""

        MOVE = 0
        ROTATE = 1

    @property
    def _fall_speed(self) -> float:
        """Current normal-fall interval in seconds.

        Calculated from the standard Tetris guideline formula.

        Returns:
            Seconds per normal-fall step.
        """
        return (0.8 - ((self.level - 1) * 0.007)) ** (self.level - 1)

    @property
    def game_time(self) -> float:
        """Elapsed game time in seconds (pauses excluded).

        Returns:
            Total seconds the game has been running.
        """
        if self._running_since is not None:
            elapsed = self._elapsed + (datetime.now() - self._running_since)
        else:
            elapsed = self._elapsed
        return elapsed.total_seconds()

    @property
    def game_time_str(self) -> str:
        """Elapsed game time formatted as ``MM:SS:CC``.

        Returns:
            Formatted time string.
        """
        time_diff = self.game_time
        minutes = int(time_diff // 60)
        seconds = int(time_diff % 60)
        milliseconds = int((time_diff * 100) % 100)
        return f"{minutes:02d}:{seconds:02d}:{milliseconds:02d}"

    @property
    def time_remaining(self) -> str:
        """Countdown for Time Attack mode, formatted as ``MM:SS:CC``.

        Returns:
            Formatted remaining-time string (``"00:00:00"`` when expired).
        """
        if self._running_since is not None:
            elapsed = self._elapsed + (datetime.now() - self._running_since)
        else:
            elapsed = self._elapsed
        remaining = (
            self._config.game_rules.time_attack_duration - elapsed.total_seconds()
        )
        if remaining <= 0:
            return "00:00:00"
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        milliseconds = int((remaining * 100) % 100)
        return f"{minutes:02d}:{seconds:02d}:{milliseconds:02d}"

    @property
    def _digging_mode_line_increment_time(self) -> float:
        if self.lines <= 50:
            return 5
        elif self.lines <= 100:
            return 4
        elif self.lines <= 200:
            return 3
        elif self.lines <= 300:
            return 2
        elif self.lines <= 400:
            return 1
        else:
            return 0.5

    def __init__(
        self,
        game_mode: GameMode,
        config: Config,
        lock_down_callback: Callable[[int], Any],
        game_over_callback: Callable[[str, SettlementMessage], Any],
    ) -> None:
        """Initialise the game core.

        Args:
            game_mode: The selected game mode.
            config: Configuration container.
            lock_down_callback: Called with ``(garbage_lines)`` after
                every lock-down so the UI can relay data to the network.
            game_over_callback: Called with ``(title, settlement)`` when
                the game ends.
        """
        self._game_mode = game_mode
        self._config = config
        self._lock_down_callback = lock_down_callback
        self._game_over_callback = game_over_callback

        # Multiplayer
        self.garbage_queue = 0  # pending garbage line count

        # Score / progress
        self.score = 0
        self.lines = 0
        self.level = 1
        self._elapsed = timedelta(0)
        self._running_since: datetime | None = datetime.now()
        self._lines_for_level = 0

        # settlement
        self._single = 0
        self._double = 0
        self._triple = 0
        self._tetris = 0
        self._t_spin = 0
        self._t_spin_single = 0
        self._t_spin_double = 0
        self._t_spin_triple = 0
        self._mini_t_spin = 0
        self._mini_t_spin_single = 0

        # Game flow
        self.paused = False
        self._animating = False
        self._clear_anim_played: float = 0
        self._pending_t_spin: int = 0

        # Piece state
        self.cur_tetrimino = None
        self.hold = None
        self._hold_once = False

        # Timers
        self.frame_timer = 0.0
        self._normal_fall_timer = 0
        self._soft_drop_timer = 0
        self._line_increment_timer = 0
        self._lock_down_timer = 0
        self._notice_timer = 0

        # Lock-down tracking
        self._lock_down_move_counter = 0
        self._lowest = 0

        # Combo / T-Spin tracking
        self._b2b_bonus = False
        self._last_move = self.Movement.MOVE
        self._rotate_offset = 0

        # Notice
        self._notice = ""

        # Board, bag, shadow, settlement message
        self.board = [
            [TetriminoShape.EMPTY] * self._config.game_rules.board_width
            for _ in range(self._config.game_rules.board_height)
        ]
        self.shadow: list[tuple[int, int]] = []
        self.bag: deque[Tetrimino] = deque(maxlen=14)

        self._init_game()

    def _replenish_bag(self) -> None:
        """Add 7 shuffled tetriminos to the bag (one of each shape)."""
        tmp = [Tetrimino(shape) for shape in TetriminoShape.normal_tetriminos()]
        random.shuffle(tmp)
        self.bag.extend(tmp)

    def _init_bag(self) -> None:
        """Fill the bag with two cycles (14 pieces) at game start."""
        for _ in range(2):
            self._replenish_bag()

    def _get_tetrimino(self) -> Tetrimino:
        """Pop the next piece from the bag.

        Replenishes the bag when it drops to 7 pieces (one cycle).

        Returns:
            The next :class:`Tetrimino`.
        """
        tetrimino = self.bag.popleft()
        if len(self.bag) == 7:
            self._replenish_bag()
        # move down one cell immediate
        return tetrimino

    def _get_current_lowest(self) -> int:
        """Return the bottom-most row occupied by the current piece.

        Returns:
            Lowest row index.

        Raises:
            RuntimeError: If ``cur_tetrimino`` is ``None``.
        """
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        return max(x for x, _ in self.cur_tetrimino)

    def _generate_new_tetrimino(self) -> None:
        """Spawn the next piece.

        If the spawn position is blocked the game-over callback is
        invoked immediately.
        """
        self.cur_tetrimino = self._get_tetrimino()
        if any(self.board[x][y] != TetriminoShape.EMPTY for x, y in self.cur_tetrimino):
            self._game_over_callback("game over!", self._get_current_settlement())
            return
        self._do_move_down()

    def _line_clear(self) -> int:
        """Remove all fully-filled rows after a lock-down.

        Rows are shifted down to fill the gaps and the top rows are
        replaced with empty cells.

        Returns:
            Number of rows cleared.
        """
        res = 0
        for row in range(self._config.game_rules.board_height - 1, -1, -1):
            while all(v != TetriminoShape.EMPTY for v in self.board[row]):
                res += 1

                for i in range(row - 1, -1, -1):
                    self.board[i + 1] = self.board[i]
                self.board[0] = [
                    TetriminoShape.EMPTY
                ] * self._config.game_rules.board_width
        return res

    def _check_can_move_down(self) -> bool:
        """Check whether the current piece can fall one row.

        Returns:
            ``True`` if a downward move is legal, ``False`` otherwise.

        Raises:
            RuntimeError: If ``cur_tetrimino`` is ``None``.
        """
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        for x, y in self.cur_tetrimino:
            if (
                x + 1 >= self._config.game_rules.board_height
                or self.board[x + 1][y] != TetriminoShape.EMPTY
            ):
                return False
        return True

    def _check_can_move_left(self) -> bool:
        """Check whether the current piece can move left.

        Returns ``False`` when the lock-down move counter has exceeded the
        configured maximum, preventing infinite stalling.

        Returns:
            ``True`` if a left move is legal, ``False`` otherwise.

        Raises:
            RuntimeError: If ``cur_tetrimino`` is ``None``.
        """
        if (
            self._lock_down_move_counter
            >= self._config.game_rules.max_lock_down_move_count
        ):
            return False
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        for x, y in self.cur_tetrimino:
            if y - 1 < 0 or self.board[x][y - 1] != TetriminoShape.EMPTY:
                return False
        return True

    def _check_can_move_right(self) -> bool:
        """Check whether the current piece can move right.

        Returns ``False`` when the lock-down move counter has exceeded the
        configured maximum, preventing infinite stalling.

        Returns:
            ``True`` if a right move is legal, ``False`` otherwise.

        Raises:
            RuntimeError: If ``cur_tetrimino`` is ``None``.
        """
        if (
            self._lock_down_move_counter
            >= self._config.game_rules.max_lock_down_move_count
        ):
            return False
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        for x, y in self.cur_tetrimino:
            if (
                y + 1 >= self._config.game_rules.board_width
                or self.board[x][y + 1] != TetriminoShape.EMPTY
            ):
                return False
        return True

    def _check_point_empty(self, point: tuple[int, int]) -> bool:
        """Return ``True`` if *point* is within board bounds and empty.

        Args:
            point: The ``(row, col)`` coordinate to check.

        Returns:
            ``True`` if the cell is within bounds and is
            ``TetriminoShape.EMPTY``.
        """
        x, y = point
        return (
            0 <= x < self._config.game_rules.board_height
            and 0 <= y < self._config.game_rules.board_width
        ) and self.board[x][y] == TetriminoShape.EMPTY

    def _check_points_empty(self, points: list[tuple[int, int]]) -> bool:
        """Return ``True`` if all *points* are within bounds and empty.

        Args:
            points: List of ``(row, col)`` coordinates to check.

        Returns:
            ``True`` if every point is within bounds and
            ``TetriminoShape.EMPTY``.
        """
        return all(self._check_point_empty(point) for point in points)

    def _do_rotate(self, cur_direction: Direction, next_direction: Direction) -> None:
        """Rotate the current piece using SRS wall-kick offsets.

        Tries each offset from the rotation table in order; the first
        collision-free offset is applied.

        Args:
            cur_direction: Current orientation.
            next_direction: Target orientation.
        """
        if (
            self._lock_down_move_counter
            >= self._config.game_rules.max_lock_down_move_count
        ):  # can only rotate 15 times when reach bottom
            return
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        rotate_data = ROTATE_TABLE[self.cur_tetrimino.shape][
            (cur_direction, next_direction)
        ]
        standard_rotate_diff = rotate_data["standard_rotate_diff"]
        offsets = rotate_data["offsets"]

        rotated = [
            (x + dx, y + dy)
            for (x, y), (dx, dy) in list(zip(self.cur_tetrimino, standard_rotate_diff))
        ]

        for i, (dx, dy) in enumerate(offsets):
            tmp = rotated[::]
            for i, (x, y) in enumerate(rotated):
                tmp[i] = x + dx, y + dy

            if self._check_points_empty(tmp):
                self.cur_tetrimino.bodies = tmp
                self.cur_tetrimino.direction = next_direction

                self._last_move = self.Movement.ROTATE

                # counter++ reset timer
                self._lock_down_move_counter += 1
                self._lock_down_timer = 0

                # record the rotate offset for t-spin calculation
                self._rotate_offset = i

                return

    def _do_move_down(self) -> bool:
        """Move the current piece down one row.

        Returns:
            ``True`` if the move succeeded.
        """
        if not self._check_can_move_down():
            return False
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        # move down
        for i, (x, y) in enumerate(self.cur_tetrimino):
            self.cur_tetrimino[i] = (x + 1, y)
        return True

    def _normal_fall(self, dt: float) -> None:
        """Progress normal gravity fall by *dt* seconds.

        Invokes ``_do_move_down()`` when the accumulated time exceeds
        :attr:`_fall_speed`.

        Args:
            dt: Delta time in seconds.
        """
        self._normal_fall_timer += dt
        if self._normal_fall_timer < self._fall_speed:
            return
        self._normal_fall_timer = 0
        if self._do_move_down():
            self._last_move = self.Movement.MOVE

            # reset lock down timer and counter
            if self._get_current_lowest() > self._lowest:
                self._lock_down_timer = 0
                self._lowest = self._get_current_lowest()
            self._lock_down_move_counter = 0

    def _set_notice(self, notice: str) -> None:
        """Set the on-screen action notice and reset its display timer."""
        self._notice = notice
        self._notice_timer = time.time()

    def _is_t_spin(self) -> int:
        """Detect T-Spin status on lock-down.

        A T-Spin is when the T-piece was rotated last, and at least 3 of
        the 4 corner cells are blocked.

        Returns:
            ``0`` for no T-Spin, ``1`` for full T-Spin,
            ``2`` for Mini T-Spin.
        """
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        if (
            self.cur_tetrimino.shape != TetriminoShape.T
            or self._last_move != self.Movement.ROTATE
        ):
            return 0
        cx, cy = self.cur_tetrimino[1]

        corners = 0
        for p in [
            (cx - 1, cy - 1),
            (cx + 1, cy - 1),
            (cx - 1, cy + 1),
            (cx + 1, cy + 1),
        ]:
            if not self._check_point_empty(p):
                corners += 1

        if corners < 3:
            return 0
        # if rotate offset is 4th point, it's t-spin
        if self._rotate_offset == 4:
            return 1

        slots = []
        if self.cur_tetrimino.direction == Direction.NORTH:
            slots = [(cx - 1, cy - 1), (cx - 1, cy + 1)]
        if self.cur_tetrimino.direction == Direction.EAST:
            slots = [(cx - 1, cy + 1), (cx + 1, cy + 1)]
        if self.cur_tetrimino.direction == Direction.SOUTH:
            slots = [(cx + 1, cy - 1), (cx + 1, cy + 1)]
        if self.cur_tetrimino.direction == Direction.WEST:
            slots = [(cx - 1, cy - 1), (cx + 1, cy - 1)]
        return 1 if all(not self._check_point_empty(p) for p in slots) else 2

    def _lock_down(self) -> None:
        """Lock the current piece onto the board.

        Marks full rows with ``CLEAR`` for the line-clear animation.
        Invokes the game-over callback if the piece is entirely in the
        buffer zone.
        """
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        # all cells in buff zone when lock down
        if all(x < 20 for x, _ in self.cur_tetrimino):
            self._game_over_callback("game over!", self._get_current_settlement())
            return

        # fill cur tetrimino to the board
        for x, y in self.cur_tetrimino:
            self.board[x][y] = self.cur_tetrimino.shape

        self._pending_t_spin = self._is_t_spin()

        # mark full rows with CLEAR for animation
        has_clear = False
        for row in range(self._config.game_rules.board_height - 1, -1, -1):
            if all(v != TetriminoShape.EMPTY for v in self.board[row]):
                for col in range(self._config.game_rules.board_width):
                    self.board[row][col] = TetriminoShape.CLEAR
                has_clear = True

        # reset lock down
        self._lock_down_timer = 0
        self._lock_down_move_counter = 0
        self._hold_once = False

        if has_clear:
            self._animating = True
        else:
            self._finish_lock_down()

    def _finish_lock_down(self) -> None:
        """Clear marked rows, update score, and spawn the next piece.

        Also handles garbage offset (incoming garbage is cancelled by
        simultaneous line clears) and invokes the lock-down callback for
        network sync.
        """
        cleared_lines = self._line_clear()
        was_b2b = self._calculate_score(self._pending_t_spin, cleared_lines)

        # Multiplayer garbage offset mechanism
        outgoing = self._calc_garbage_lines(
            self._pending_t_spin, cleared_lines, was_b2b
        )
        if outgoing > 0:
            cancelled = min(outgoing, self.garbage_queue)
            self.garbage_queue -= cancelled
            outgoing -= cancelled

        self._apply_incoming_garbage()
        # send garbage lines to control level
        self._lock_down_callback(outgoing)
        self._generate_new_tetrimino()
        self._build_notice(self._pending_t_spin, cleared_lines, was_b2b)
        self._pending_t_spin = 0

    def _calc_garbage_lines(
        self, is_t_spin: int, cleared_lines: int, was_b2b: bool
    ) -> int:
        """Calculate garbage lines to send to the opponent.

        Args:
            is_t_spin: ``1`` (T-Spin), ``2`` (Mini T-Spin), or ``0``.
            cleared_lines: Number of lines cleared.
            was_b2b: Whether a back-to-back bonus was active.

        Returns:
            Number of garbage lines to send.
        """
        lines = 0
        if is_t_spin == 1:  # T-Spin
            if cleared_lines == 1:
                lines = 2
            elif cleared_lines == 2:
                lines = 4
            elif cleared_lines == 3:
                lines = 6
        elif is_t_spin == 2:  # Mini T-Spin — no garbage
            lines = 0
        else:  # Normal clear
            if cleared_lines == 2:
                lines = 1
            elif cleared_lines == 3:
                lines = 2
            elif cleared_lines == 4:
                lines = 4
        if lines > 0 and was_b2b:
            lines += 1
        return lines

    def _apply_incoming_garbage(self) -> None:
        """Inject pending garbage lines from the queue into the board.

        Each garbage row is pushed from the bottom, shifting everything up.
        Every group of 8 lines shares the same random hole column.
        """
        width = self._config.game_rules.board_width
        count = self.garbage_queue
        self.garbage_queue = 0

        col = 0
        for i in range(count):
            if i % 8 == 0:
                col = random.randint(0, width - 1)
            self.board.pop(0)
            new_line = [TetriminoShape.GARBAGE] * width
            new_line[col] = TetriminoShape.EMPTY
            self.board.append(new_line)

    def _handle_line_clear_anim(self, delta: float) -> None:
        """Progress the line-clear animation by *delta* seconds.

        When the animation duration is exceeded, starts the actual
        line-clear processing.

        Args:
            delta: Delta time in seconds.
        """
        if self._clear_anim_played >= self._config.timing.clear_anim_duration:
            self._clear_anim_played = 0
            self._animating = False
            self._finish_lock_down()
        self._clear_anim_played += delta

    def _get_current_settlement(self) -> SettlementMessage:
        """Build a :class:`SettlementMessage` from current counters.

        Returns:
            A populated settlement message.
        """
        return SettlementMessage(
            "",
            self.score,
            self.lines,
            self.game_time_str,
            self._single,
            self._double,
            self._triple,
            self._tetris,
            self._t_spin,
            self._t_spin_single,
            self._t_spin_double,
            self._t_spin_triple,
            self._mini_t_spin,
            self._mini_t_spin_single,
            game_mode=str(self._game_mode),
        )

    def _calculate_score(self, is_t_spin: int, cleared_lines: int) -> bool:
        """Update score, lines, and level counters after a lock-down.

        Follows the modern Tetris scoring table with back-to-back
        multiplier.  T-Spin combos are tracked separately from
        normal line clears.

        Args:
            is_t_spin: ``1`` (full T-Spin), ``2`` (Mini), or ``0``.
            cleared_lines: Number of lines cleared.

        Returns:
            ``True`` if a back-to-back bonus was active before this
            lock-down.
        """
        bonus = self._b2b_bonus
        self._b2b_bonus = True

        awarded_line = 0
        score2add = 0

        if is_t_spin == 1:
            if cleared_lines == 0:
                awarded_line = 4
                score2add = 100 * self.level
                self._t_spin += 1
            elif cleared_lines == 1:
                awarded_line = 7
                score2add = 400 * self.level
                self._t_spin_single += 1
            elif cleared_lines == 2:
                awarded_line = 10
                score2add = 1200 * self.level
                self._t_spin_double += 1
            elif cleared_lines == 3:
                awarded_line = 13
                score2add = 1600 * self.level
                self._t_spin_triple += 1
        elif is_t_spin == 2:
            if cleared_lines == 0:
                awarded_line = 1
                score2add = 100 * self.level
                self._mini_t_spin += 1
            elif cleared_lines == 1:
                awarded_line = 2
                score2add = 200 * self.level
                self._mini_t_spin_single += 1
        else:
            if cleared_lines == 0:
                # no lines cleared, do not reset b2b
                self._b2b_bonus = bonus
            elif cleared_lines == 1:
                score2add = 100 * self.level
                self._b2b_bonus = False
                self._single += 1
            elif cleared_lines == 2:
                awarded_line = 1
                score2add = 300 * self.level
                self._b2b_bonus = False
                self._double += 1
            elif cleared_lines == 3:
                awarded_line = 2
                score2add = 500 * self.level
                self._b2b_bonus = False
                self._triple += 1
            elif cleared_lines == 4:
                awarded_line = 4
                score2add = 800 * self.level
                self._tetris += 1

        # if b2b, line clear bonus * 1.5 and score * 1.5
        if bonus and self._b2b_bonus:
            self._lines_for_level += int((awarded_line + cleared_lines) * 1.5)
            self.score += int(1.5 * score2add)
        else:
            self._lines_for_level += awarded_line + cleared_lines
            self.score += score2add

        self.lines += cleared_lines

        if self._game_mode == GameMode._150_LINES and self.lines >= 150:
            self._game_over_callback("game over!", self._get_current_settlement())
            return False

        if (
            self._game_mode == GameMode.TIME_ATTACK
            and self._running_since is not None
            and (self._elapsed + (datetime.now() - self._running_since)).total_seconds()
            >= self._config.game_rules.time_attack_duration
        ):
            self._game_over_callback("game over!", self._get_current_settlement())
            return False

        # level up
        # max level 15
        if (
            self.level < 15
            and self._lines_for_level >= 5 * self.level * (self.level + 1) / 2
        ):
            self.level += 1

        # if casual or digging mode, max level is 5
        if (
            self._game_mode == GameMode.CASUAL or self._game_mode == GameMode.DIGGING
        ) and self.level > 5:
            self.level = 5

        return bonus

    def _build_notice(self, is_t_spin: int, cleared_lines: int, was_b2b: bool) -> None:
        """Build and show the lock-down action notice.

        Examples: ``"T-Spin Double! B2B!"``, ``"Tetris!"``.

        Args:
            is_t_spin: ``1`` (T-Spin), ``2`` (Mini), or ``0``.
            cleared_lines: Number of lines cleared.
            was_b2b: Whether back-to-back was active before this
                lock-down.
        """
        notice = ""
        if is_t_spin == 1:
            if cleared_lines == 0:
                notice = "T-Spin!"
            elif cleared_lines == 1:
                notice = "T-Spin Single!"
            elif cleared_lines == 2:
                notice = "T-Spin Double!"
            elif cleared_lines == 3:
                notice = "T-Spin Triple!"
        elif is_t_spin == 2:
            if cleared_lines == 0:
                notice = "T-Spin Mini!"
            elif cleared_lines == 1:
                notice = "T-Spin Mini Single!"
        elif cleared_lines == 1:
            notice = "Single!"
        elif cleared_lines == 2:
            notice = "Double!"
        elif cleared_lines == 3:
            notice = "Triple!"
        elif cleared_lines == 4:
            notice = "Tetris!"

        if notice:
            if self._b2b_bonus and was_b2b:
                notice += " B2B!"
            self._set_notice(notice)

    def _handle_lock_down(self, dt: float) -> None:
        """Progress the lock-down timer.

        When the piece can no longer move down, the lock-down timer runs;
        after 0.5 seconds the piece locks.

        Args:
            dt: Delta time in seconds.
        """
        if self._check_can_move_down():
            return
        # reset when move and rotate successfully
        self._lock_down_timer += dt

        if self._lock_down_timer >= 0.5:
            self._lock_down()

    def _handle_shadow(self) -> None:
        """Project the ghost piece to the lowest valid position."""
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        self.shadow = self.cur_tetrimino.bodies[::]

        def helper():
            if self.cur_tetrimino is None:
                raise RuntimeError("cur_tetrimino is None")
            for x, y in self.shadow:
                if x + 1 >= len(self.board):
                    return False
                if (x + 1, y) in self.cur_tetrimino.bodies:
                    continue
                if self.board[x + 1][y] != TetriminoShape.EMPTY:
                    return False
            return True

        while helper():
            for i in range(len(self.shadow)):
                x, y = self.shadow[i]
                self.shadow[i] = x + 1, y

    def _handle_digging_mode(self, dt: float) -> None:
        """Automatically add garbage rows in Digging mode.

        Adds one garbage line every 10 seconds when the game mode is
        ``GameMode.DIGGING``.

        Args:
            dt: Delta time in seconds.
        """
        self._line_increment_timer += dt

        if (
            self._game_mode != GameMode.DIGGING
            or self._line_increment_timer < self._digging_mode_line_increment_time
        ):
            return
        self._line_increment_timer = 0

        # add one line in the garbage
        self.garbage_queue += 1

    def _init_game(self) -> None:
        """Initialise bag, timers, and first piece.

        Also adds 10 initial garbage rows for Digging mode to simulate
        a partially filled board.
        """
        self._init_bag()
        self._generate_new_tetrimino()

    def process(self, time_delta: float) -> None:
        """Advance game state by *time_delta* seconds.

        Handles animation, digging, normal-fall, lock-down, and
        shadow updates. This is the main entry point called by the
        UI layer each tick.

        Args:
            time_delta: Delta time in seconds.
        """

        if self._animating:
            self._handle_line_clear_anim(time_delta)
        else:
            self._handle_digging_mode(time_delta)
            self._normal_fall(time_delta)
            self._handle_lock_down(time_delta)

        self._handle_shadow()

        if (
            self._game_mode == GameMode.TIME_ATTACK
            and self._running_since is not None
            and (self._elapsed + (datetime.now() - self._running_since)).total_seconds()
            >= self._config.game_rules.time_attack_duration
        ):
            self._game_over_callback("game over!", self._get_current_settlement())
            return

    def do_move_left(self) -> bool:
        """Move the current piece left one cell.

        Returns:
            ``True`` if the move succeeded.
        """
        if not self._check_can_move_left():
            return False

        # counter++ reset timer
        self._lock_down_move_counter += 1
        self._lock_down_timer = 0

        self._last_move = self.Movement.MOVE

        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        for i, (x, y) in enumerate(self.cur_tetrimino):
            self.cur_tetrimino[i] = (x, y - 1)
        return True

    def do_move_right(self) -> bool:
        """Move the current piece right one cell.

        Returns:
            ``True`` if the move succeeded.
        """
        if not self._check_can_move_right():
            return False

        # counter++ reset timer
        self._lock_down_move_counter += 1
        self._lock_down_timer = 0

        self._last_move = self.Movement.MOVE

        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        for i, (x, y) in enumerate(self.cur_tetrimino):
            self.cur_tetrimino[i] = (x, y + 1)
        return True

    def do_rotate_cw(self) -> None:
        """Rotate the current piece clockwise (SRS)."""
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        cur_direction = self.cur_tetrimino.direction
        directions = list(Direction)
        next_direction = directions[
            (directions.index(cur_direction) + 1) % len(directions)
        ]
        self._do_rotate(cur_direction, next_direction)

    def do_rotate_ccw(self) -> None:
        """Rotate the current piece counter-clockwise (SRS)."""
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        cur_direction = self.cur_tetrimino.direction
        directions = list(Direction)
        next_direction = directions[
            (len(directions) + (directions.index(cur_direction) - 1)) % len(directions)
        ]
        self._do_rotate(cur_direction, next_direction)

    def add_garbage_lines(self, count: int) -> None:
        """Queue incoming garbage lines from the opponent.

        Args:
            count: Number of garbage lines to add.
        """
        self._set_notice(f"Garbage +{count}!")
        self.garbage_queue += count

    def do_soft_drop(self) -> None:
        """Perform one soft-drop step.

        Awards 1 × level score per cell dropped.
        """
        # cancel normal fall
        self._normal_fall_timer = 0
        if self._do_move_down():
            # soft drop get level score
            self.score += self.level
            self._last_move = self.Movement.MOVE

            # reset lock down timer and counter
            if self._get_current_lowest() > self._lowest:
                self._lock_down_timer = 0
                self._lowest = self._get_current_lowest()
            self._lock_down_move_counter = 0

    def do_hard_drop(self) -> None:
        """Instantly drop the piece to the bottom and lock it.

        Awards 2 × level × rows_dropped score for each row the piece
        falls before locking.
        """
        while self._do_move_down():
            # hard drop get 2 * level * lines score
            self.score += self.level * 2
        self._lock_down()

    def do_hold(self) -> None:
        """Swap the current piece with the hold piece.

        Can only be used once per lock-down cycle.
        """
        if self._hold_once:
            return
        if self.cur_tetrimino is None:
            raise RuntimeError("cur_tetrimino is None")
        self._hold_once = True
        for x, y in self.cur_tetrimino:
            self.board[x][y] = TetriminoShape.EMPTY
        if self.hold is None:
            self.hold = self.cur_tetrimino
            self._generate_new_tetrimino()
        else:
            self.bag.appendleft(Tetrimino(self.hold.shape))
            self.hold = self.cur_tetrimino
            self._generate_new_tetrimino()

    def get_notice(self) -> str:
        """Return the current action notice string.

        Shows ``"PAUSED"`` while paused. Notices expire after one second.

        Returns:
            The notice string (empty string when no notice is active).
        """
        if self.paused:
            return "PAUSED"
        # show notice for 1 second
        if time.time() - self._notice_timer >= 1:
            return ""
        return self._notice

    def serialize_board(self) -> list[list[int]]:
        """Export the board as a 2D list of shape values.

        Used for network synchronisation in versus mode.

        Returns:
            A 2D list of integers (one per cell).
        """
        return [[v.value for v in row] for row in self.board]

    def forced_game_over(self, set_title: str) -> None:
        """Immediately end the game.

        Args:
            set_title: The settlement title (e.g. ``"YOU WIN!"``).
        """
        self._game_over_callback(set_title, self._get_current_settlement())

    def toggle_pause(self) -> None:
        """Toggle the pause state.

        Not available in versus mode (the call is silently ignored).
        When unpausing, the elapsed-time clock resumes.
        """
        if self._game_mode == GameMode.VERSUS:
            return
        self.paused = not self.paused
        if self.paused:
            if self._running_since is not None:
                self._elapsed += datetime.now() - self._running_since
                self._running_since = None
        else:
            self._running_since = datetime.now()

    def controllable(self) -> bool:
        """Return ``True`` if the core should process player input.

        Input is ignored while paused or during the line-clear animation.

        Returns:
            ``True`` if input should be accepted.
        """
        return not (self.paused or self._animating)
