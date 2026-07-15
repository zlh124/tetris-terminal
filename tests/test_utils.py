"""Unit tests for utility helpers (``tetris/utils.py``).

Focuses on ``rotate_points`` (the rotation math underpinning the SRS
table) and ``get_version``. The curses drawing helpers are exercised
lightly with a fake window since they are thin wrappers.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError

import pytest

import tetris.utils as utils
from tetris.utils import get_version


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
