"""Unit tests for utility helpers (``tetris/utils.py``).

Focuses on ``rotate_points`` (the rotation math underpinning the SRS
table) and ``get_version``. The curses drawing helpers are exercised
lightly with a fake window since they are thin wrappers.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError

import pytest

import tetris.utils as utils
from tetris.utils import get_version, rotate_points


# ---------------------------------------------------------------------------
# rotate_points
# ---------------------------------------------------------------------------

# CW rotation around the origin maps (r, c) → (c, -r); CCW maps to (-c, r).


class TestRotatePoints:
    """Tests for ``rotate_points``."""

    def test_cw_around_origin(self) -> None:
        assert rotate_points([(1, 0), (0, 1)], [0, 0], ccw=False) == [
            (0, -1),
            (1, 0),
        ]

    def test_ccw_around_origin(self) -> None:
        assert rotate_points([(1, 0), (0, 1)], [0, 0], ccw=True) == [
            (0, 1),
            (-1, 0),
        ]

    def test_cw_then_ccw_round_trip(self) -> None:
        """CCW is the exact inverse of CW."""
        pts = [(2, 3), (5, 1), (0, 7), (4, 4)]
        cw = rotate_points(pts, [2, 3], ccw=False)
        back = rotate_points(cw, [2, 3], ccw=True)
        assert back == pts

    def test_center_is_invariant_under_rotation(self) -> None:
        """A point at the center is unmoved by rotation."""
        assert rotate_points([(3, 4)], [3, 4], ccw=False) == [(3, 4)]
        assert rotate_points([(3, 4)], [3, 4], ccw=True) == [(3, 4)]

    def test_averaged_double_axis_i_piece_center(self) -> None:
        """The I-piece uses an averaged double-axis center [(r0,r1),(c0,c1)].

        cr = mean(r0, r1), cc = mean(c0, c1). Verify the averaging is applied
        by checking CW→CCW round-trip (rounding must be lossless here).
        """
        pts = [(0, 0), (0, 1), (0, 2), (0, 3)]
        center = [(0, 1), (1, 2)]  # cr = 0.5, cc = 1.5
        cw = rotate_points(pts, center, ccw=False)
        back = rotate_points(cw, center, ccw=True)
        assert back == pts

    def test_four_rotations_cw_return_to_start(self) -> None:
        """Four CW turns = identity."""
        pts = [(2, 3), (5, 1)]
        once = rotate_points(pts, [2, 2], ccw=False)
        twice = rotate_points(once, [2, 2], ccw=False)
        thrice = rotate_points(twice, [2, 2], ccw=False)
        fourth = rotate_points(thrice, [2, 2], ccw=False)
        assert fourth == pts

    def test_results_are_int_tuples(self) -> None:
        out = rotate_points([(1, 0)], [0, 0], ccw=False)
        assert out == [(0, -1)]
        assert all(isinstance(r, int) and isinstance(c, int) for r, c in out)


# ---------------------------------------------------------------------------
# get_version
# ---------------------------------------------------------------------------


class TestGetVersion:
    """Tests for ``get_version``."""

    def test_returns_string_when_installed(self) -> None:
        """The package is installed under ``uv run``, so a version is returned."""
        v = get_version()
        assert isinstance(v, str)
        assert v  # non-empty

    def test_returns_dev_when_not_installed(self, monkeypatch) -> None:
        def _raise(name: str):
            raise PackageNotFoundError(name)

        monkeypatch.setattr("tetris.utils.version", _raise)
        assert get_version() == "0.0.0-dev"


# ---------------------------------------------------------------------------
# timed decorator
# ---------------------------------------------------------------------------


class TestTimed:
    """Tests for the ``timed`` decorator."""

    def test_preserves_return_value(self) -> None:
        @utils.timed
        def add(a, b):
            return a + b

        assert add(2, 3) == 5

    def test_preserves_name_and_docstring(self) -> None:
        @utils.timed
        def fn():
            """docstring."""

        assert fn.__name__ == "fn"
        assert fn.__doc__ == "docstring."

    def test_propagates_exceptions(self) -> None:
        @utils.timed
        def boom():
            raise ValueError("nope")

        with pytest.raises(ValueError, match="nope"):
            boom()


# ---------------------------------------------------------------------------
# safe_addstr (light fake-window test)
# ---------------------------------------------------------------------------


class TestSafeAddstr:
    """Tests for ``safe_addstr`` swallowing ``curses.error``."""

    def test_swallows_curses_error(self, monkeypatch) -> None:
        import curses

        raised: list[bool] = []

        class FakeWin:
            def addstr(self, *args):
                raised.append(True)
                raise curses.error

        # Should not raise.
        utils.safe_addstr(FakeWin(), 0, 0, "x")  # type: ignore[arg-type]
        assert raised == [True]

    def test_passes_through_on_success(self) -> None:
        calls: list[tuple] = []

        class FakeWin:
            def addstr(self, *args):
                calls.append(args)

        utils.safe_addstr(FakeWin(), 1, 2, "hi")  # type: ignore[arg-type]
        assert calls == [(1, 2, "hi")]
