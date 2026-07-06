"""Unit tests for enumerations (``tetris/enums.py``)."""

from __future__ import annotations

from tetris.enums import (
    Direction,
    GameMode,
    Sections,
    TetriminoShape,
    WebClientMsgType,
)


class TestTetriminoShape:
    """Tests for ``TetriminoShape``."""

    def test_normal_tetriminos_are_seven(self) -> None:
        seven = TetriminoShape.normal_tetriminos()
        assert len(seven) == 7
        assert set(seven) == {
            TetriminoShape.Z,
            TetriminoShape.S,
            TetriminoShape.O,
            TetriminoShape.J,
            TetriminoShape.T,
            TetriminoShape.I,
            TetriminoShape.L,
        }

    def test_normal_tetriminos_exclude_specials(self) -> None:
        seven = TetriminoShape.normal_tetriminos()
        assert TetriminoShape.EMPTY not in seven
        assert TetriminoShape.GARBAGE not in seven
        assert TetriminoShape.CLEAR not in seven

    def test_values_are_contiguous(self) -> None:
        values = [s.value for s in TetriminoShape]
        assert values == list(range(10))

    def test_repr_is_friendly(self) -> None:
        assert repr(TetriminoShape.T) == "TetriminoShape.T"


class TestDirection:
    def test_order_clockwise(self) -> None:
        assert list(Direction) == [
            Direction.NORTH,
            Direction.EAST,
            Direction.SOUTH,
            Direction.WEST,
        ]


class TestGameMode:
    def test_str_strips_underscores(self) -> None:
        assert str(GameMode._150_LINES) == "150 LINES"
        assert str(GameMode.TIME_ATTACK) == "TIME ATTACK"
        assert str(GameMode.ENDLESS) == "ENDLESS"

    def test_values_unique(self) -> None:
        values = [m.value for m in GameMode]
        assert len(values) == len(set(values))


class TestSections:
    def test_str_strips_underscores(self) -> None:
        assert str(Sections._150_LINES) == "150 LINES"
        assert str(Sections.QUIT) == "QUIT"

    def test_quit_is_last(self) -> None:
        assert Sections.QUIT.value == 6


class TestWebClientMsgType:
    def test_string_values(self) -> None:
        assert WebClientMsgType.HELLO == "hello"
        assert WebClientMsgType.HELLO_OK == "hello_ok"
        assert WebClientMsgType.MATCH_FOUND == "match_found"
        assert WebClientMsgType.GARBAGE == "garbage"
        assert WebClientMsgType.ERROR == "error"
        assert WebClientMsgType.SERVER_FULL == "server_full"
        assert WebClientMsgType.OPPONENT_DISCONNECTED == "opponent_disconnected"

    def test_all_values_unique(self) -> None:
        values = [m.value for m in WebClientMsgType]
        assert len(values) == len(set(values))
