"""Unit tests for the TetrisCore game engine (``tetris/core.py``).

The core is pure logic — no curses — so it is exercised directly. Two
strategies are combined:

* **White-box setup** — ``board`` / ``cur_tetrimino`` are public attributes,
  so tests inject exact piece positions to reproduce specific mechanics
  (T-Spin corners, wall kicks, garbage injection) that would be fragile to
  reach by "playing" the game.
* **Behavioural integration** — a handful of tests drive the public
  ``do_*`` / ``process`` API end-to-end (full game, deterministic replay).

Randomness is controlled via ``seed=``; wall-clock time is frozen with
``monkeypatch`` so time-based mechanics (Time Attack, notice expiry) are
deterministic. No third-party dependencies are introduced.
"""

from __future__ import annotations

from copy import copy
from datetime import datetime, timedelta

import pytest

import tetris.core
from tetris.config import Config
from tetris.core import Tetrimino, TetrisCore
from tetris.enums import Direction, GameMode, TetriminoShape

# Board geometry (matches Config defaults).
W: int = 10
H: int = 40


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def make_core(
    mode: GameMode = GameMode.ENDLESS,
    seed: int | None = 0,
    lock=None,
    over=None,
) -> TetrisCore:
    """Build a core instance with no-op callbacks by default.

    Args:
        mode: Game mode (default ENDLESS).
        seed: RNG seed. ``None`` leaves the global RNG untouched.
        lock: ``lock_down_callback`` (receives garbage-line count).
        over: ``game_over_callback`` (receives title, settlement).
    """
    lock_cb = lock if lock is not None else (lambda n: None)
    over_cb = over if over is not None else (lambda title, msg: None)
    return TetrisCore(mode, Config(), lock_cb, over_cb, seed=seed)


def set_current(
    core: TetrisCore,
    shape: TetriminoShape,
    bodies: list[tuple[int, int]],
    direction: Direction = Direction.NORTH,
) -> None:
    """Inject a piece as the current tetrimino, bypassing the bag/spawn flow.

    Used for method-level isolation tests (rotation, collision, T-Spin).
    """
    t = Tetrimino(shape)
    t.bodies = copy(bodies)
    t.direction = direction
    core.cur_tetrimino = t


def force_next(core: TetrisCore, shape: TetriminoShape) -> None:
    """Make the next ``_generate_new_tetrimino`` produce *shape*."""
    core.bag.appendleft(Tetrimino(shape))


def block(core: TetrisCore, cells, shape: TetriminoShape = TetriminoShape.Z) -> None:
    """Mark board cells as occupied (assumes an already-empty board)."""
    for r, c in cells:
        core.board[r][c] = shape


def freeze_now(monkeypatch, fixed: datetime) -> None:
    """Patch ``tetris.core.datetime`` so ``datetime.now()`` returns *fixed*."""

    class FakeDateTime:
        @classmethod
        def now(cls):
            return fixed

    monkeypatch.setattr(tetris.core, "datetime", FakeDateTime)


def frozen_clock(monkeypatch, start: datetime | None = None):
    """Patch ``tetris.core.datetime`` with a controllable clock.

    Returns an ``advance(seconds)`` callable that moves the fake clock
    forward. Lets pause/time tests drive elapsed time deterministically
    without real sleeping.
    """
    state = {"now": start or datetime(2026, 1, 1)}

    class FakeDateTime:
        @classmethod
        def now(cls):
            return state["now"]

    monkeypatch.setattr(tetris.core, "datetime", FakeDateTime)

    def advance(seconds: float) -> None:
        state["now"] = state["now"] + timedelta(seconds=seconds)

    return advance


# ---------------------------------------------------------------------------
# 7-bag randomiser
# ---------------------------------------------------------------------------


class TestBag:
    """Tests for the 7-bag tetrimino generator."""

    def test_bag_cycle_has_all_seven(self) -> None:
        """One bag cycle contains exactly one of each standard shape.

        The first cycle is ``cur_tetrimino`` (popped at init) plus the next
        six pieces still in the bag.
        """
        core = make_core(seed=1)
        assert core.cur_tetrimino, "cur_tetrimino is None"
        drawn = [core.cur_tetrimino.shape] + [
            core.bag.popleft().shape for _ in range(6)
        ]
        assert sorted(drawn) == sorted(TetriminoShape.normal_tetriminos())

    def test_bag_replenishes_at_seven(self) -> None:
        """``_get_tetrimino`` refills the bag when it drops to 7 pieces."""
        core = make_core(seed=1)
        # Bag starts at 13 (one piece already spawned). Drawing 6 leaves 7,
        # which triggers a refill back to 14.
        for _ in range(6):
            core._get_tetrimino()
        assert len(core.bag) == 14

    def test_same_seed_same_sequence(self) -> None:
        """Two cores with the same seed produce identical piece sequences.

        Note: ``TetrisCore`` seeds the *global* ``random`` module (not an
        instance RNG), and ``_get_tetrimino``'s bag-replenish shuffle
        consumes global state. So the second core must be created *after*
        the first's sequence is fully drawn — its ``__init__`` re-seeds,
        resetting the shared RNG.
        """
        a = make_core(seed=42)
        assert a.cur_tetrimino, "cur_tetrimino is None"
        seq_a = [a.cur_tetrimino.shape] + [a._get_tetrimino().shape for _ in range(20)]
        b = make_core(seed=42)
        assert b.cur_tetrimino, "cur_tetrimino is None"
        seq_b = [b.cur_tetrimino.shape] + [b._get_tetrimino().shape for _ in range(20)]
        assert seq_a == seq_b

    def test_different_seed_different_sequence(self) -> None:
        """Different seeds (almost surely) produce different sequences."""
        a = make_core(seed=1)
        assert a.cur_tetrimino, "cur_tetrimino is None"
        seq_a = [a.cur_tetrimino.shape] + [a._get_tetrimino().shape for _ in range(20)]
        b = make_core(seed=2)
        assert b.cur_tetrimino, "cur_tetrimino is None"
        seq_b = [b.cur_tetrimino.shape] + [b._get_tetrimino().shape for _ in range(20)]
        assert seq_a != seq_b


# ---------------------------------------------------------------------------
# movement & collision
# ---------------------------------------------------------------------------


class TestMovement:
    """Tests for left/right movement and wall/collision blocking."""

    def test_move_left_succeeds(self) -> None:
        core = make_core()
        assert core.cur_tetrimino, "cur_tetrimino is None"
        set_current(core, TetriminoShape.T, [(25, 4), (25, 5), (24, 5), (25, 6)])
        assert core.do_move_left() is True
        assert core.cur_tetrimino.bodies == [(25, 3), (25, 4), (24, 4), (25, 5)]

    def test_move_right_succeeds(self) -> None:
        core = make_core()
        assert core.cur_tetrimino, "cur_tetrimino is None"
        set_current(core, TetriminoShape.T, [(25, 4), (25, 5), (24, 5), (25, 6)])
        assert core.do_move_right() is True
        assert core.cur_tetrimino.bodies == [(25, 5), (25, 6), (24, 6), (25, 7)]

    def test_move_left_blocked_at_wall(self) -> None:
        core = make_core()
        set_current(core, TetriminoShape.T, [(25, 0), (25, 1), (24, 1), (25, 2)])
        assert core.do_move_left() is False

    def test_move_right_blocked_at_wall(self) -> None:
        core = make_core()
        set_current(core, TetriminoShape.T, [(25, 7), (25, 8), (24, 8), (25, 9)])
        assert core.do_move_right() is False

    def test_move_blocked_by_occupied_cell(self) -> None:
        core = make_core()
        block(core, [(25, 3)])  # target of the leftmost cell when moving left
        set_current(core, TetriminoShape.T, [(25, 4), (25, 5), (24, 5), (25, 6)])
        assert core.do_move_left() is False

    def test_lock_down_move_counter_caps_movement(self) -> None:
        """Once the move counter hits the cap, sideways moves are refused."""
        core = make_core()
        set_current(core, TetriminoShape.O, [(38, 4), (38, 5), (39, 4), (39, 5)])
        core._lock_down_move_counter = core._config.game_rules.max_lock_down_move_count
        assert core.do_move_left() is False
        assert core.do_move_right() is False

    def test_lock_down_move_counter_caps_rotation(self) -> None:
        """Once the move counter hits the cap, rotation is a no-op."""
        core = make_core()
        assert core.cur_tetrimino, "cur_tetrimino is None"
        set_current(core, TetriminoShape.T, [(25, 4), (25, 5), (24, 5), (25, 6)])
        before = core.cur_tetrimino.direction
        core._lock_down_move_counter = core._config.game_rules.max_lock_down_move_count
        core.do_rotate_cw()
        assert core.cur_tetrimino.direction == before


# ---------------------------------------------------------------------------
# rotation & SRS wall kicks
# ---------------------------------------------------------------------------


class TestRotation:
    """Tests for SRS rotation and wall-kick offset recording."""

    def test_rotate_cw_changes_direction(self) -> None:
        core = make_core()
        assert core.cur_tetrimino, "cur_tetrimino is None"
        set_current(
            core,
            TetriminoShape.T,
            [(25, 4), (25, 5), (24, 5), (25, 6)],
            Direction.NORTH,
        )
        core.do_rotate_cw()
        assert core.cur_tetrimino.direction == Direction.EAST
        # Standard SRS rotation (no kick needed on an empty board).
        assert set(map(tuple, core.cur_tetrimino.bodies)) == {
            (24, 5),
            (25, 5),
            (25, 6),
            (26, 5),
        }

    def test_rotate_ccw_changes_direction(self) -> None:
        core = make_core()
        assert core.cur_tetrimino, "cur_tetrimino is None"
        set_current(
            core,
            TetriminoShape.T,
            [(25, 4), (25, 5), (24, 5), (25, 6)],
            Direction.NORTH,
        )
        core.do_rotate_ccw()
        assert core.cur_tetrimino.direction == Direction.WEST

    def test_o_piece_rotation_is_positional_noop(self) -> None:
        """The O piece occupies the same cells after rotation (just reordered)."""
        core = make_core()
        assert core.cur_tetrimino, "cur_tetrimino is None"
        set_current(
            core,
            TetriminoShape.O,
            [(25, 4), (25, 5), (26, 4), (26, 5)],
            Direction.NORTH,
        )
        before = set(map(tuple, core.cur_tetrimino.bodies))
        core.do_rotate_cw()
        assert set(map(tuple, core.cur_tetrimino.bodies)) == before

    def test_rotate_records_offset_zero(self) -> None:
        """A rotation that succeeds on the first (0,0) kick records offset 0.

        Regression for the ``_rotate`` inner-loop variable shadowing bug,
        which left ``_rotate_offset`` stuck at 3 regardless of the kick used.
        """
        core = make_core()
        set_current(
            core,
            TetriminoShape.T,
            [(25, 4), (25, 5), (24, 5), (25, 6)],
            Direction.NORTH,
        )
        core.do_rotate_cw()
        assert core._rotate_offset == 0

    def test_srs_wall_kick_uses_second_offset(self) -> None:
        """When the (0,0) kick is blocked, rotation falls to the next kick.

        Blocks the standard landing cell (26, 5) so the (0,0) offset fails;
        the JLSTZ NORTH→EAST table's second offset (0, -1) must then apply,
        shifting the piece one column left.
        """
        core = make_core()
        assert core.cur_tetrimino, "cur_tetrimino is None"
        set_current(
            core,
            TetriminoShape.T,
            [(25, 4), (25, 5), (24, 5), (25, 6)],
            Direction.NORTH,
        )
        block(core, [(26, 5)])  # block the (0,0)-offset landing cell
        core.do_rotate_cw()
        assert core.cur_tetrimino.direction == Direction.EAST
        assert set(map(tuple, core.cur_tetrimino.bodies)) == {
            (24, 4),
            (25, 4),
            (25, 5),
            (26, 4),
        }
        # The second kick (index 1) was used — not stuck at 3 (the old bug).
        assert core._rotate_offset == 1


# ---------------------------------------------------------------------------
# fall, lock-down, line clear
# ---------------------------------------------------------------------------


class TestFallLock:
    """Tests for soft/hard drop, lock-down, and top-out conditions."""

    def test_soft_drop_awards_score_and_moves_down(self) -> None:
        core = make_core()
        assert core.cur_tetrimino, "cur_tetrimino is None"
        set_current(core, TetriminoShape.T, [(25, 4), (25, 5), (24, 5), (25, 6)])
        core.do_soft_drop()
        assert core.score == core.level  # 1 × level per cell
        assert core.cur_tetrimino.bodies == [(26, 4), (26, 5), (25, 5), (26, 6)]

    def test_hard_drop_score(self) -> None:
        """Hard drop awards 2 × level per row fallen."""
        core = make_core()
        # O at rows 25-26 falls to rows 38-39: 13 rows.
        set_current(core, TetriminoShape.O, [(25, 4), (25, 5), (26, 4), (26, 5)])
        core.do_hard_drop()
        assert core.score == 2 * core.level * 13

    def test_hard_drop_locks_and_spawns_next(self) -> None:
        core = make_core()
        set_current(core, TetriminoShape.O, [(25, 4), (25, 5), (26, 4), (26, 5)])
        core.do_hard_drop()
        # Piece locked onto the board at the bottom.
        assert core.board[38][4] == TetriminoShape.O
        assert core.board[38][5] == TetriminoShape.O
        assert core.board[39][4] == TetriminoShape.O
        assert core.board[39][5] == TetriminoShape.O
        # A new piece has been spawned.
        assert core.cur_tetrimino is not None
        assert core.cur_tetrimino.shape in TetriminoShape.normal_tetriminos()

    def test_lock_in_buffer_zone_triggers_game_over(self) -> None:
        """A piece that locks entirely in the buffer zone (rows < 20) tops out."""
        over: list[str] = []
        core = make_core(over=lambda title, msg: over.append(title))
        block(core, [(20, c) for c in range(W)])  # floor the buffer
        set_current(core, TetriminoShape.O, [(18, 4), (18, 5), (19, 4), (19, 5)])
        core.do_hard_drop()
        assert over == ["game over!"]

    def test_spawn_blocked_triggers_game_over(self) -> None:
        """A piece whose spawn cells are occupied tops out immediately."""
        over: list[str] = []
        core = make_core(over=lambda title, msg: over.append(title))
        # T spawn cells at GENERATE_POSITION[T] = (19, 3).
        block(core, [(19, 3), (19, 4), (18, 4), (19, 5)])
        force_next(core, TetriminoShape.T)
        core._generate_new_tetrimino()
        assert over == ["game over!"]

    def test_line_clear_single(self) -> None:
        core = make_core()
        for c in range(W):
            core.board[39][c] = TetriminoShape.Z
        assert core._line_clear() == 1
        assert all(core.board[39][c] == TetriminoShape.EMPTY for c in range(W))

    def test_line_clear_tetris(self) -> None:
        core = make_core()
        for r in (36, 37, 38, 39):
            for c in range(W):
                core.board[r][c] = TetriminoShape.Z
        assert core._line_clear() == 4

    def test_line_clear_nonadjacent_rows(self) -> None:
        core = make_core()
        for c in range(W):
            core.board[39][c] = TetriminoShape.Z
            core.board[30][c] = TetriminoShape.Z
        assert core._line_clear() == 2

    def test_forced_game_over(self) -> None:
        """``forced_game_over`` immediately invokes the game-over callback."""
        over: list[str] = []
        core = make_core(over=lambda title, msg: over.append(title))
        core.forced_game_over("YOU WIN!")
        assert over == ["YOU WIN!"]

    def test_line_clear_animation_completes_via_process(self) -> None:
        """A lock-down that completes a row starts an animation that
        ``process()`` advances until the rows are actually cleared."""
        core = make_core(seed=1)
        for c in range(8):  # pre-fill row 39 cols 0-7
            core.board[39][c] = TetriminoShape.Z
        # O above cols 8-9 falls to fill row 39 cols 8-9 → row completes.
        set_current(core, TetriminoShape.O, [(25, 8), (25, 9), (26, 8), (26, 9)])
        core.do_hard_drop()
        assert core._animating is True
        assert core.lines == 0  # not yet cleared (animation pending)

        anim = core._config.timing.clear_anim_duration
        while core._animating:
            core.process(anim + 0.01)

        assert core._animating is False
        assert core.lines == 1
        # No CLEAR markers left on the board.
        assert not any(
            cell == TetriminoShape.CLEAR for row in core.board for cell in row
        )


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------

# (is_t_spin, cleared_lines) → (score_added, counter_attr, b2b_after,
#                               lines_for_level_added).  Level = 1, b2b start
# = False, so no B2B multiplier applies.
SCORE_CASES = [
    (0, 0, 0, None, False, 0),
    (0, 1, 100, "_single", False, 1),
    (0, 2, 300, "_double", False, 3),
    (0, 3, 500, "_triple", False, 5),
    (0, 4, 800, "_tetris", True, 8),
    (1, 0, 100, "_t_spin", True, 4),
    (1, 1, 400, "_t_spin_single", True, 8),
    (1, 2, 1200, "_t_spin_double", True, 12),
    (1, 3, 1600, "_t_spin_triple", True, 16),
    (2, 0, 100, "_mini_t_spin", True, 1),
    (2, 1, 200, "_mini_t_spin_single", True, 3),
]


class TestScoring:
    """Tests for the ``_calc_score`` scoring table and B2B multiplier."""

    @pytest.mark.parametrize(
        "is_t_spin,cleared,exp_score,counter_attr,exp_b2b,exp_lfl",
        SCORE_CASES,
    )
    def test_calc_score_table(
        self,
        is_t_spin: int,
        cleared: int,
        exp_score: int,
        counter_attr,
        exp_b2b: bool,
        exp_lfl: int,
    ) -> None:
        core = make_core()
        core.level = 1
        core._b2b_bonus = False
        core._calc_score(is_t_spin, cleared)
        assert core.score == exp_score
        assert core.lines == cleared
        assert core._b2b_bonus is exp_b2b
        assert core._lines_for_level == exp_lfl
        if counter_attr is not None:
            assert getattr(core, counter_attr) == 1

    def test_score_scales_with_level(self) -> None:
        core = make_core()
        core.level = 3
        core._calc_score(0, 1)  # single = 100 × level
        assert core.score == 300

    def test_b2b_tetris_chain_multiplies_score(self) -> None:
        """Consecutive tetrises keep B2B alive; the second scores ×1.5.

        ``level`` and ``_lines_for_level`` are reset between calls so the
        B2B multiplier is isolated from the level-up that a tetris would
        otherwise trigger.
        """
        core = make_core()
        core._b2b_bonus = False
        core.level = 1
        core._lines_for_level = 0
        core._calc_score(0, 4)  # first tetris: 800, b2b → True
        assert core.score == 800
        core.level = 1
        core._lines_for_level = 0
        core._calc_score(0, 4)  # second tetris: B2B bonus active
        assert core.score == 800 + int(1.5 * 800)

    def test_single_breaks_b2b_chain(self) -> None:
        """A single clear after a tetris resets B2B and scores flat."""
        core = make_core()
        core._b2b_bonus = False
        core.level = 1
        core._lines_for_level = 0
        core._calc_score(0, 4)  # tetris, b2b True
        core.level = 1
        core._lines_for_level = 0
        core._calc_score(0, 1)  # single: b2b reset, no multiplier
        assert core.score == 800 + 100
        assert core._b2b_bonus is False


# ---------------------------------------------------------------------------
# garbage system
# ---------------------------------------------------------------------------

# (is_t_spin, cleared, was_b2b) → outgoing garbage lines.
GARBAGE_CASES = [
    (0, 1, False, 0),
    (0, 2, False, 1),
    (0, 3, False, 2),
    (0, 4, False, 4),
    (0, 0, False, 0),
    (1, 0, False, 0),
    (1, 1, False, 2),
    (1, 2, False, 4),
    (1, 3, False, 6),
    (2, 0, False, 0),
    (2, 1, False, 0),
    (0, 4, True, 5),  # 4 + 1 B2B
    (0, 2, True, 2),  # 1 + 1 B2B
    (1, 2, True, 5),  # 4 + 1 B2B
    (0, 1, True, 0),  # single sends 0; B2B only adds when lines > 0
]


class TestGarbage:
    """Tests for garbage-line calculation, offset/cancel, and injection."""

    @pytest.mark.parametrize("is_t_spin,cleared,was_b2b,expected", GARBAGE_CASES)
    def test_calc_garbage_lines(
        self, is_t_spin: int, cleared: int, was_b2b: bool, expected: int
    ) -> None:
        core = make_core()
        assert core._calc_garbage_lines(is_t_spin, cleared, was_b2b) == expected

    def test_outgoing_cancels_incoming(self, monkeypatch) -> None:
        """Outgoing garbage offsets pending incoming garbage 1:1."""
        received: list[int] = []
        core = make_core(lock=lambda n: received.append(n))
        core.garbage_queue = 2
        core._pending_t_spin = 0
        # Stub the messy parts of _finish_lock_down to isolate the offset logic.
        monkeypatch.setattr(core, "_line_clear", lambda: 0)
        monkeypatch.setattr(core, "_calc_score", lambda ts, cl: False)
        monkeypatch.setattr(core, "_calc_garbage_lines", lambda ts, cl, b2b: 4)
        monkeypatch.setattr(core, "_apply_incoming_garbage", lambda: None)
        monkeypatch.setattr(core, "_generate_new_tetrimino", lambda: None)
        monkeypatch.setattr(core, "_build_notice", lambda ts, cl, b2b: None)
        core._finish_lock_down()
        # outgoing 4 cancels min(4, 2) = 2; queue 2 → 0; callback gets 4 - 2.
        assert core.garbage_queue == 0
        assert received == [2]

    def test_no_outgoing_applies_all_incoming(self, monkeypatch) -> None:
        """With no outgoing garbage, the full incoming queue is applied."""
        applied: list[int] = []
        core = make_core()
        core.garbage_queue = 2
        core._pending_t_spin = 0
        monkeypatch.setattr(core, "_line_clear", lambda: 0)
        monkeypatch.setattr(core, "_calc_score", lambda ts, cl: False)
        monkeypatch.setattr(core, "_calc_garbage_lines", lambda ts, cl, b2b: 0)
        monkeypatch.setattr(
            core, "_apply_incoming_garbage", lambda: applied.append(core.garbage_queue)
        )
        monkeypatch.setattr(core, "_generate_new_tetrimino", lambda: None)
        monkeypatch.setattr(core, "_build_notice", lambda ts, cl, b2b: None)
        core._finish_lock_down()
        assert applied == [2]  # queue untouched (2) when apply runs

    def test_garbage_pushes_board_up(self) -> None:
        core = make_core()
        for c in range(W):
            core.board[39][c] = TetriminoShape.Z
        core.garbage_queue = 3
        core._apply_incoming_garbage()
        assert core.garbage_queue == 0
        # Original bottom row shifted up by 3 to row 36.
        assert all(core.board[36][c] == TetriminoShape.Z for c in range(W))
        # Bottom 3 rows are garbage, each with exactly one hole.
        for r in (37, 38, 39):
            garbage = sum(
                1 for c in range(W) if core.board[r][c] == TetriminoShape.GARBAGE
            )
            assert garbage == W - 1

    def test_garbage_hole_shared_per_eight_lines(self) -> None:
        """Every group of 8 garbage rows shares one hole column."""
        core = make_core()
        core.garbage_queue = 10
        core._apply_incoming_garbage()
        # Bottom 10 rows (30..39) are garbage. The first 8 (i=0..7, rows
        # 30..37) share a hole; the last 2 (i=8..9, rows 38..39) share another.
        holes = {}
        for r in range(30, 40):
            for c in range(W):
                if core.board[r][c] == TetriminoShape.EMPTY:
                    holes[r] = c
                    break
        assert len({holes[r] for r in range(30, 38)}) == 1
        assert len({holes[r] for r in range(38, 40)}) == 1

    def test_add_garbage_notices(self) -> None:
        core = make_core()
        core.add_garbage_lines(3)
        assert core.garbage_queue == 3
        assert core.get_notice() == "Garbage +3!"


# ---------------------------------------------------------------------------
# T-Spin detection
# ---------------------------------------------------------------------------


class TestTSpin:
    """Tests for ``_is_t_spin`` corner logic and the offset-4 TST shortcut.

    Uses a NORTH-facing T at junction ``(25, 5)`` — the same layout as the
    rotation tests. Its four corner cells around the junction:

        front-left  (24,4)   front-right (24,6)   ← "front" (stem side, up)
                ┌───┐
                │ T │  (24,5)  stem
        ┌───┬───┴───┴───┬───┐
        …   │ T │ T │ T │   …      (25,4)(25,5)(25,6) bar
        ┌───┴───┴───┴───┬───┐
        back-left  (26,4)   back-right (26,6)  ← "back"
    """

    def _north_t(self, core: TetrisCore) -> None:
        set_current(
            core,
            TetriminoShape.T,
            [(25, 4), (25, 5), (24, 5), (25, 6)],
            Direction.NORTH,
        )
        core._last_move = TetrisCore.Movement.ROTATE

    def test_tspin_full_three_corners(self) -> None:
        """Three corners filled with both front corners blocked ⇒ full (1)."""
        core = make_core()
        self._north_t(core)
        block(core, [(24, 4), (24, 6), (26, 4)])  # front-L, front-R, back-L
        assert core._is_t_spin() == 1

    def test_tspin_mini_front_corner_open(self) -> None:
        """Three corners filled but one front corner open ⇒ mini (2)."""
        core = make_core()
        self._north_t(core)
        # front-L, back-L, back-R filled; front-R (24,6) open.
        block(core, [(24, 4), (26, 4), (26, 6)])
        assert core._is_t_spin() == 2

    def test_tspin_requires_rotate_as_last_move(self) -> None:
        """No T-Spin when the last move was a translation."""
        core = make_core()
        self._north_t(core)
        block(core, [(24, 4), (24, 6), (26, 4)])
        core._last_move = TetrisCore.Movement.MOVE
        assert core._is_t_spin() == 0

    def test_tspin_requires_t_shape(self) -> None:
        """Non-T pieces never register a T-Spin."""
        core = make_core()
        set_current(
            core,
            TetriminoShape.O,
            [(25, 4), (25, 5), (26, 4), (26, 5)],
            Direction.NORTH,
        )
        core._last_move = TetrisCore.Movement.ROTATE
        assert core._is_t_spin() == 0

    def test_no_tspin_with_fewer_than_three_corners(self) -> None:
        core = make_core()
        self._north_t(core)
        block(core, [(24, 4), (26, 4)])  # only two corners
        assert core._is_t_spin() == 0

    def test_offset4_shortcut_forces_full_tspin(self) -> None:
        """A rotation that used the 5th wall-kick is a full T-Spin.

        Regression for the ``_rotate`` shadowing bug: ``_rotate_offset`` was
        stuck at 3, so this ``== 4`` shortcut was unreachable dead code. With
        the fix, a 5th-kick (TST-style) rotation yields a full T-Spin even
        when the corner logic alone would classify it as mini.
        """
        core = make_core()
        self._north_t(core)
        block(core, [(24, 4), (26, 4), (26, 6)])  # mini-like, front-R open
        core._rotate_offset = 4
        assert core._is_t_spin() == 1  # shortcut overrides mini

    def test_offset4_shortcut_contrast(self) -> None:
        """The same mini-like config without offset 4 stays mini (2)."""
        core = make_core()
        self._north_t(core)
        block(core, [(24, 4), (26, 4), (26, 6)])
        core._rotate_offset = 0
        assert core._is_t_spin() == 2

    @pytest.mark.parametrize(
        "direction,bodies,front_corners,back_corner",
        [
            (
                Direction.EAST,
                [(24, 5), (25, 5), (25, 6), (26, 5)],
                [(24, 6), (26, 6)],
                (24, 4),
            ),
            (
                Direction.SOUTH,
                [(25, 4), (25, 5), (26, 5), (25, 6)],
                [(26, 4), (26, 6)],
                (24, 4),
            ),
            (
                Direction.WEST,
                [(24, 5), (25, 5), (25, 4), (26, 5)],
                [(24, 4), (26, 4)],
                (24, 6),
            ),
        ],
    )
    def test_tspin_full_each_orientation(
        self, direction, bodies, front_corners, back_corner
    ) -> None:
        """Full T-Spin (front corners both blocked) in EAST/SOUTH/WEST."""
        core = make_core()
        set_current(core, TetriminoShape.T, bodies, direction)
        core._last_move = TetrisCore.Movement.ROTATE
        core._rotate_offset = 0
        block(core, front_corners + [back_corner])
        assert core._is_t_spin() == 1


# ---------------------------------------------------------------------------
# hold, shadow, serialise, pause
# ---------------------------------------------------------------------------


class TestHold:
    """Tests for the hold mechanic."""

    def test_hold_once_per_lockdown(self) -> None:
        core = make_core()
        first = core.cur_tetrimino
        core.do_hold()  # first hold succeeds
        assert core.hold is first
        after_first = core.cur_tetrimino
        core.do_hold()  # second hold is a silent no-op
        assert core.cur_tetrimino is after_first  # piece did not change

    def test_hold_first_stores_current(self) -> None:
        core = make_core()
        first = core.cur_tetrimino
        core.do_hold()
        assert core.hold is first
        assert core.cur_tetrimino is not first

    def test_hold_swap_returns_previous(self) -> None:
        """Holding again puts the previously-held piece back into play."""
        core = make_core()
        assert core.cur_tetrimino, "cur_tetrimino is None"
        first = core.cur_tetrimino
        core.do_hold()  # hold = first
        # Force the spawned replacement so we can identify it, then hold again.
        core.do_hard_drop()  # lock the second; resets _hold_once via _lock_down
        third = core.cur_tetrimino
        core.do_hold()  # swap: third → hold, first → back into play
        assert core.hold is third
        assert core.cur_tetrimino.shape == first.shape


class TestShadow:
    """Tests for ghost-piece projection."""

    def test_shadow_projects_to_lowest_valid(self) -> None:
        core = make_core()
        set_current(core, TetriminoShape.O, [(25, 4), (25, 5), (26, 4), (26, 5)])
        core._handle_shadow()
        assert set(map(tuple, core.shadow)) == {
            (38, 4),
            (38, 5),
            (39, 4),
            (39, 5),
        }

    def test_shadow_rests_on_floor(self) -> None:
        core = make_core()
        set_current(core, TetriminoShape.O, [(37, 4), (37, 5), (38, 4), (38, 5)])
        core._handle_shadow()
        assert set(map(tuple, core.shadow)) == {
            (38, 4),
            (38, 5),
            (39, 4),
            (39, 5),
        }

    def test_shadow_rests_on_block(self) -> None:
        core = make_core()
        block(core, [(33, 4), (33, 5)])  # floor under cols 4-5 at row 33
        set_current(core, TetriminoShape.O, [(25, 4), (25, 5), (26, 4), (26, 5)])
        core._handle_shadow()
        assert set(map(tuple, core.shadow)) == {
            (31, 4),
            (31, 5),
            (32, 4),
            (32, 5),
        }


class TestSerialise:
    """Tests for board serialisation."""

    def test_returns_int_grid(self) -> None:
        core = make_core()
        grid = core.serialize_board()
        assert len(grid) == H
        assert all(len(row) == W for row in grid)
        # Empty board → all EMPTY (0).
        assert all(v == TetriminoShape.EMPTY.value for row in grid for v in row)

    def test_values_match_shape_enums(self) -> None:
        core = make_core()
        block(core, [(39, 0)], TetriminoShape.I)
        assert core.serialize_board()[39][0] == TetriminoShape.I.value


class TestPause:
    """Tests for pause / controllability / notice behaviour."""

    def test_toggle_pause_switches_state(self) -> None:
        core = make_core()
        assert core.paused is False
        core.toggle_pause()
        assert core.paused is True
        core.toggle_pause()
        assert core.paused is False

    def test_toggle_pause_ignored_in_versus(self) -> None:
        core = make_core(mode=GameMode.VERSUS)
        core.toggle_pause()
        assert core.paused is False

    def test_controllable_false_when_paused(self) -> None:
        core = make_core()
        core.toggle_pause()
        assert core.controllable() is False

    def test_controllable_false_when_animating(self) -> None:
        core = make_core()
        core._animating = True
        assert core.controllable() is False

    def test_get_notice_paused(self) -> None:
        core = make_core()
        core.toggle_pause()
        assert core.get_notice() == "PAUSED"

    def test_get_notice_expires_after_one_second(self, monkeypatch) -> None:
        """Notices vanish after the 1-second display window."""
        core = make_core()
        t = [0.0]
        monkeypatch.setattr(tetris.core.time, "time", lambda: t[0])
        core._set_notice("Single!")
        assert core.get_notice() == "Single!"
        t[0] = 1.0
        assert core.get_notice() == ""


class TestPauseTime:
    """Tests for elapsed-time preservation across pause/unpause cycles.

    Regression guard: ``toggle_pause`` previously dropped ``_running_since``
    without accumulating into ``_elapsed``, so ``game_time`` reset to 0 the
    instant the game was paused (and never recovered after unpause).
    """

    def test_game_time_progresses_while_running(self, monkeypatch) -> None:
        advance = frozen_clock(monkeypatch)
        core = make_core()
        advance(10)
        assert core.game_time == pytest.approx(10.0)

    def test_pause_preserves_elapsed_time(self, monkeypatch) -> None:
        """Pausing must NOT zero out the elapsed time."""
        advance = frozen_clock(monkeypatch)
        core = make_core()
        advance(10)
        core.toggle_pause()
        assert core.paused is True
        assert core.game_time == pytest.approx(10.0)  # not 0 (the regression)

    def test_game_time_frozen_while_paused(self, monkeypatch) -> None:
        """While paused, the clock must not advance."""
        advance = frozen_clock(monkeypatch)
        core = make_core()
        advance(10)
        core.toggle_pause()
        advance(30)  # paused for 30s — must not count
        assert core.game_time == pytest.approx(10.0)

    def test_unpause_resumes_from_preserved_time(self, monkeypatch) -> None:
        """After unpause, time continues from where it left off, not from 0."""
        advance = frozen_clock(monkeypatch)
        core = make_core()
        advance(10)
        core.toggle_pause()
        advance(30)  # paused
        core.toggle_pause()  # unpause
        assert core.game_time == pytest.approx(10.0)
        advance(5)
        assert core.game_time == pytest.approx(15.0)

    def test_multiple_pause_cycles_accumulate(self, monkeypatch) -> None:
        """Only running intervals count; paused intervals are excluded."""
        advance = frozen_clock(monkeypatch)
        core = make_core()
        advance(5)  # run 5s
        core.toggle_pause()
        advance(20)  # paused 20s (excluded)
        core.toggle_pause()
        advance(5)  # run 5s → 10s total
        core.toggle_pause()
        advance(10)  # paused 10s (excluded)
        core.toggle_pause()
        advance(5)  # run 5s → 15s total
        assert core.game_time == pytest.approx(15.0)

    def test_pause_excluded_from_time_remaining(self, monkeypatch) -> None:
        """In Time Attack, pause time must not eat into the countdown."""
        advance = frozen_clock(monkeypatch)
        core = make_core(mode=GameMode.TIME_ATTACK)
        advance(10)
        core.toggle_pause()
        advance(60)  # paused 60s — should NOT consume the countdown
        core.toggle_pause()
        # Only 10s of game time elapsed → 110s of 120s remaining.
        assert core.game_time == pytest.approx(10.0)
        assert core.time_remaining == "01:50:00"


# ---------------------------------------------------------------------------
# levelling & mode end conditions
# ---------------------------------------------------------------------------


class TestLeveling:
    """Tests for level progression, caps, and mode-end triggers."""

    def test_level_up_threshold(self) -> None:
        """Level 1 → 2 needs ``_lines_for_level >= 5`` (5 singles)."""
        core = make_core()
        core._b2b_bonus = False
        for _ in range(5):
            core._calc_score(0, 1)  # +1 to _lines_for_level each
        assert core.level == 2

    def test_level_up_once_per_lockdown(self) -> None:
        """A single lock-down levels up at most once (``if``, not ``while``)."""
        core = make_core()
        core._b2b_bonus = False
        core._calc_score(0, 4)  # tetris: +8 to _lines_for_level (≥5 → level 2)
        assert core.level == 2  # not 3 (8 < 15, the level-2→3 threshold)

    def test_max_level_15_in_endless(self) -> None:
        core = make_core(mode=GameMode.ENDLESS)
        core.level = 15
        core._b2b_bonus = False
        core._calc_score(0, 4)
        assert core.level == 15

    def test_casual_caps_at_level_5(self) -> None:
        core = make_core(mode=GameMode.CASUAL)
        core.level = 5
        core._lines_for_level = 100  # past the level-5→6 threshold (75)
        core._b2b_bonus = False
        core._calc_score(0, 4)
        assert core.level == 5

    def test_150_lines_mode_ends_at_150(self) -> None:
        over: list[str] = []
        core = make_core(
            mode=GameMode._150_LINES, over=lambda title, msg: over.append(title)
        )
        core.lines = 149
        core._b2b_bonus = False
        core._calc_score(0, 1)  # lines → 150
        assert over == ["game over!"]

    def test_time_attack_ends_in_calc_score(self, monkeypatch) -> None:
        over: list[str] = []
        core = make_core(
            mode=GameMode.TIME_ATTACK, over=lambda title, msg: over.append(title)
        )
        duration = core._config.game_rules.time_attack_duration
        fixed = datetime(2026, 1, 1)
        freeze_now(monkeypatch, fixed)
        core._running_since = fixed
        core._elapsed = timedelta(seconds=duration)
        core._calc_score(0, 0)
        assert over == ["game over!"]

    def test_time_attack_ends_in_process(self, monkeypatch) -> None:
        over: list[str] = []
        core = make_core(
            mode=GameMode.TIME_ATTACK, over=lambda title, msg: over.append(title)
        )
        duration = core._config.game_rules.time_attack_duration
        fixed = datetime(2026, 1, 1)
        freeze_now(monkeypatch, fixed)
        core._running_since = fixed
        core._elapsed = timedelta(seconds=duration)
        core.process(0.01)
        assert over == ["game over!"]


# ---------------------------------------------------------------------------
# process() timing
# ---------------------------------------------------------------------------


class TestProcess:
    """Tests for the per-tick update loop's timing semantics."""

    def test_process_falls_one_row_per_interval(self) -> None:
        core = make_core(seed=1)
        start_lowest = core._get_current_lowest()
        core.process(core._fall_speed)  # exactly one fall interval
        assert core._get_current_lowest() == start_lowest + 1

    def test_process_large_delta_does_not_catch_up(self) -> None:
        """A delta far exceeding fall speed still moves the piece only once."""
        core = make_core(seed=1)
        start_lowest = core._get_current_lowest()
        core.process(10.0)
        assert core._get_current_lowest() == start_lowest + 1

    def test_digging_mode_auto_adds_garbage(self) -> None:
        core = make_core(mode=GameMode.DIGGING, seed=1)
        increment = core._digging_mode_line_increment_time
        core.process(increment + 0.01)
        assert core.garbage_queue >= 1


# ---------------------------------------------------------------------------
# headless integration
# ---------------------------------------------------------------------------


def _play_hard_drops(seed: int, limit: int = 2000):
    """Drive a game with hard-drop-only input until game over or *limit*.

    Returns ``(score, lines, level, ticks)``. The line-clear animation is
    flushed between drops so the board state stays consistent.
    """
    over: list[str] = []
    core = make_core(seed=seed, over=lambda title, msg: over.append(title))
    anim = core._config.timing.clear_anim_duration
    ticks = 0
    while not over and ticks < limit:
        core.do_hard_drop()
        while core._animating:
            core.process(anim + 0.01)
        ticks += 1
    return core.score, core.lines, core.level, ticks, bool(over)


class TestIntegration:
    """End-to-end tests driving the public API without curses."""

    def test_full_game_no_exception(self) -> None:
        """A hard-drop-only game runs to game-over without raising."""
        *_, over = _play_hard_drops(seed=7)
        assert over, "game should top out within the drop limit"

    def test_deterministic_replay(self) -> None:
        """Same seed + same input ⇒ identical final score/lines/level."""
        a = _play_hard_drops(seed=7)
        b = _play_hard_drops(seed=7)
        assert a == b


# ---------------------------------------------------------------------------
# lock-down notice strings
# ---------------------------------------------------------------------------

NOTICE_CASES = [
    (0, 1, "Single!"),
    (0, 2, "Double!"),
    (0, 3, "Triple!"),
    (0, 4, "Tetris!"),
    (1, 0, "T-Spin!"),
    (1, 1, "T-Spin Single!"),
    (1, 2, "T-Spin Double!"),
    (1, 3, "T-Spin Triple!"),
    (2, 0, "T-Spin Mini!"),
    (2, 1, "T-Spin Mini Single!"),
    (0, 0, ""),  # no clear, no t-spin → no notice
]


class TestNotice:
    """Tests for ``_build_notice`` action strings and the B2B suffix."""

    @pytest.mark.parametrize("is_t_spin,cleared,expected", NOTICE_CASES)
    def test_notice_strings(
        self, monkeypatch, is_t_spin: int, cleared: int, expected: str
    ) -> None:
        t = [0.0]
        monkeypatch.setattr(tetris.core.time, "time", lambda: t[0])
        core = make_core()
        core._b2b_bonus = False
        core._build_notice(is_t_spin, cleared, False)
        assert core.get_notice() == expected

    def test_b2b_suffix_when_active(self, monkeypatch) -> None:
        t = [0.0]
        monkeypatch.setattr(tetris.core.time, "time", lambda: t[0])
        core = make_core()
        core._b2b_bonus = True
        core._build_notice(0, 4, True)  # tetris, B2B active
        assert core.get_notice() == "Tetris! B2B!"

    def test_no_b2b_suffix_when_inactive(self, monkeypatch) -> None:
        t = [0.0]
        monkeypatch.setattr(tetris.core.time, "time", lambda: t[0])
        core = make_core()
        core._b2b_bonus = False  # chain already broken
        core._build_notice(0, 4, True)
        assert core.get_notice() == "Tetris!"
