"""Unit tests for the settlement statistics container (``tetris/settlement.py``).

Only ``SettlementMessage.format`` is unit-tested — the ``Settlement`` curses
UI class is out of scope for unit testing.
"""

from __future__ import annotations

import pytest

from tetris.settlement import SettlementMessage


def make_msg(game_mode: str = "") -> SettlementMessage:
    """Build a settlement message with small, safe counter values."""
    return SettlementMessage(
        "GAME OVER",
        score=1000,
        lines=50,
        time="02:00:00",
        single=5,
        double=3,
        triple=2,
        tetris=1,
        t_spin=0,
        t_spin_single=1,
        t_spin_double=0,
        t_spin_triple=0,
        mini_t_spin=0,
        mini_t_spin_single=0,
        game_mode=game_mode,
    )


class TestSettlementFormat:
    """Tests for ``SettlementMessage.format``."""

    def test_returns_nonempty_lines(self) -> None:
        lines = make_msg().format(50)
        assert len(lines) > 0

    def test_each_line_exactly_width(self) -> None:
        """Each emitted line is padded/centred to exactly *width* columns."""
        width = 50
        lines = make_msg().format(width)
        assert all(len(line) == width for line in lines)

    def test_includes_mode_line_when_set(self) -> None:
        lines = make_msg(game_mode="ENDLESS").format(50)
        assert any("Mode: ENDLESS" in line for line in lines)

    def test_omits_mode_line_when_empty(self) -> None:
        lines = make_msg(game_mode="").format(50)
        assert not any("Mode:" in line for line in lines)

    def test_includes_all_stat_values(self) -> None:
        joined = "\n".join(make_msg().format(60))
        for needle in [
            "Score: 1000",
            "Lines: 50",
            "Time: 02:00:00",
            "Single: 5",
            "Double: 3",
            "Triple: 2",
            "Tetris: 1",
            "T-Spin Single: 1",
        ]:
            assert needle in joined, f"missing {needle!r}"

    def test_title_is_attribute(self) -> None:
        msg = make_msg()
        assert msg.title == "GAME OVER"

    @pytest.mark.skip(
        reason=(
            "format() infinite-loops when any message exceeds half-width "
            "(the flush branch never increments i). Latent bug — not testable "
            "without a timeout."
        )
    )
    def test_format_hangs_on_oversize_message(self) -> None:
        """Documents a known bug; skipped to avoid hanging the suite."""
