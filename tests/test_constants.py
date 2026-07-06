"""Unit tests for constants and lookup tables (``tetris/constants.py``).

Validates the SRS rotation table's completeness, wall-kick offset counts,
and the rotation-involution invariant (a CW diff and its inverse CCW diff
sum to zero — i.e. rotating back is a no-op).
"""

from __future__ import annotations

import pytest

from tetris.constants import (
    GENERATE_POSITION,
    ROTATE_TABLE,
    SHAPE_TABLE,
    I_WALL_KICK_OFFSET,
    JLSTZ_WALL_KICK_OFFSET,
    O_WALL_KICK_OFFSET,
)
from tetris.enums import Direction, TetriminoShape

# The 8 (start, end) transitions populated per shape: 4 CW + 4 CCW.
EXPECTED_TRANSITIONS = {
    (Direction.NORTH, Direction.EAST),
    (Direction.EAST, Direction.SOUTH),
    (Direction.SOUTH, Direction.WEST),
    (Direction.WEST, Direction.NORTH),
    (Direction.NORTH, Direction.WEST),
    (Direction.WEST, Direction.SOUTH),
    (Direction.SOUTH, Direction.EAST),
    (Direction.EAST, Direction.NORTH),
}


class TestShapeTable:
    """Tests for ``SHAPE_TABLE`` and ``GENERATE_POSITION``."""

    def test_all_shapes_have_four_cells(self) -> None:
        for shape in TetriminoShape.normal_tetriminos():
            assert len(SHAPE_TABLE[shape]) == 4

    def test_all_shapes_have_spawn_position(self) -> None:
        for shape in TetriminoShape.normal_tetriminos():
            assert shape in GENERATE_POSITION


class TestRotateTable:
    """Tests for the built ``ROTATE_TABLE``."""

    def test_covers_all_shapes_and_transitions(self) -> None:
        for shape in TetriminoShape.normal_tetriminos():
            keys = set(ROTATE_TABLE[shape].keys())
            assert keys == EXPECTED_TRANSITIONS, f"missing transitions for {shape}"

    def test_each_entry_has_diff_and_offsets(self) -> None:
        for shape in TetriminoShape.normal_tetriminos():
            for trans in EXPECTED_TRANSITIONS:
                entry = ROTATE_TABLE[shape][trans]
                assert "standard_rotate_diff" in entry
                assert "offsets" in entry
                assert len(entry["standard_rotate_diff"]) == 4

    @pytest.mark.parametrize("shape", TetriminoShape.normal_tetriminos())
    def test_offset_counts_by_shape(self, shape: TetriminoShape) -> None:
        """JLSTZ and I use 5 wall-kick offsets; O uses only (0,0)."""
        for trans in EXPECTED_TRANSITIONS:
            offsets = ROTATE_TABLE[shape][trans]["offsets"]
            if shape == TetriminoShape.O:
                assert offsets == [(0, 0)]
            else:
                assert len(offsets) == 5

    @pytest.mark.parametrize("shape", TetriminoShape.normal_tetriminos())
    def test_rotation_is_involution(self, shape: TetriminoShape) -> None:
        """For each CW (A→B), diff(A,B) + diff(B,A) == (0,0) per cell.

        Rotating CW then CCW returns every cell to its origin, so the two
        diffs must be exact negatives.
        """
        cw_pairs = [
            (Direction.NORTH, Direction.EAST),
            (Direction.EAST, Direction.SOUTH),
            (Direction.SOUTH, Direction.WEST),
            (Direction.WEST, Direction.NORTH),
        ]
        for a, b in cw_pairs:
            fwd = ROTATE_TABLE[shape][(a, b)]["standard_rotate_diff"]
            rev = ROTATE_TABLE[shape][(b, a)]["standard_rotate_diff"]
            for (fr, fc), (rr, rc) in zip(fwd, rev):
                assert (fr + rr, fc + rc) == (0, 0)


class TestWallKickTables:
    """Sanity checks on the raw wall-kick offset constants."""

    def test_jlstz_has_five_offsets_each(self) -> None:
        assert len(JLSTZ_WALL_KICK_OFFSET) == 8
        for offsets in JLSTZ_WALL_KICK_OFFSET.values():
            assert len(offsets) == 5

    def test_i_has_five_offsets_each(self) -> None:
        assert len(I_WALL_KICK_OFFSET) == 8
        for offsets in I_WALL_KICK_OFFSET.values():
            assert len(offsets) == 5

    def test_o_has_single_zero_offset(self) -> None:
        assert len(O_WALL_KICK_OFFSET) == 8
        for offsets in O_WALL_KICK_OFFSET.values():
            assert offsets == [(0, 0)]
