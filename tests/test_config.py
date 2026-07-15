"""Unit tests for configuration management (``tetris/config.py``).

Covers JSON loading with defaults merging, internal-field protection,
config generation, and platform path resolution — all using ``tmp_path``
and ``monkeypatch`` so no real config files are touched.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from tetris.config import (
    Config,
    DisplayConfig,
    GameRulesConfig,
    _dataclass_defaults,
    _merge_dataclass,
)

# ---------------------------------------------------------------------------
# load / merge
# ---------------------------------------------------------------------------


class TestLoad:
    """Tests for ``Config.load`` and the merge logic."""

    def test_load_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        cfg = Config.load(tmp_path / "nope.json")
        assert cfg == Config()

    def test_load_partial_json_merges_over_defaults(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"display": {"empty_cell": "··"}}))
        cfg = Config.load(path)
        # Override applied…
        assert cfg.display.empty_cell == "··"
        # …while untouched fields keep their defaults.
        assert cfg.display.solid_cell == DisplayConfig().solid_cell
        assert cfg.game_rules.board_width == 10

    def test_internal_fields_not_overridable(self, tmp_path: Path) -> None:
        """Internal fields (board_width/height, window_*) ignore JSON values."""
        path = tmp_path / "config.json"
        path.write_text(
            json.dumps(
                {
                    "game_rules": {"board_width": 999, "board_height": 1},
                    "display": {"window_rows": 1, "window_cols": 1},
                }
            )
        )
        cfg = Config.load(path)
        assert cfg.game_rules.board_width == 10
        assert cfg.game_rules.board_height == 40
        assert cfg.display.window_rows == 26
        assert cfg.display.window_cols == 44

    def test_load_invalid_json_returns_defaults(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        path.write_text("{ not valid json")
        assert Config.load(path) == Config()

    def test_load_accepts_str_path(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"timing": {"fps": 60}}))
        cfg = Config.load(path)
        assert cfg.timing.fps == 60

    def test_merge_dataclass_skips_internal_and_unknown(self) -> None:
        gr = _merge_dataclass(GameRulesConfig, {"board_width": 99, "junk": 1})
        assert gr.board_width == 10  # internal, ignored
        assert not hasattr(gr, "junk")  # unknown, ignored

    def test_merge_applies_customizable_fields(self) -> None:
        gr = _merge_dataclass(GameRulesConfig, {"max_lock_down_move_count": 30})
        assert gr.max_lock_down_move_count == 30


# ---------------------------------------------------------------------------
# generate_config
# ---------------------------------------------------------------------------


class TestGenerate:
    """Tests for ``Config.generate_config``."""

    def test_writes_default_config(self, tmp_path: Path) -> None:
        path = tmp_path / "sub" / "config.json"
        result = Config.generate_config(path)
        assert result == path
        assert path.exists()
        # Round-trips back to defaults.
        assert Config.load(path) == Config()

    def test_adds_schema_url(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        Config.generate_config(path)
        data = json.loads(path.read_text())
        assert "$schema" in data
        assert "tetris-terminal" in data["$schema"]

    def test_refuses_existing_file(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        path.write_text("{}")
        with pytest.raises(FileExistsError):
            Config.generate_config(path)

    def test_uses_default_path_when_none(self, monkeypatch, tmp_path: Path) -> None:
        """When *path* is None, ``config_path()`` is used."""
        fake_path = tmp_path / "cfg.json"
        monkeypatch.setattr(Config, "config_path", staticmethod(lambda: fake_path))
        assert Config.generate_config() == fake_path
        assert fake_path.exists()


# ---------------------------------------------------------------------------
# get_config_data / _dataclass_defaults
# ---------------------------------------------------------------------------


class TestConfigData:
    """Tests for serialization helpers."""

    def test_get_config_data_excludes_internal_fields(self) -> None:
        data = Config.get_config_data()
        assert "board_width" not in data["game_rules"]
        assert "board_height" not in data["game_rules"]
        assert "window_rows" not in data["display"]
        # Customizable fields present.
        assert "max_lock_down_move_count" in data["game_rules"]
        assert "empty_cell" in data["display"]

    def test_dataclass_defaults_excludes_internal_and_underscore(self) -> None:
        defaults = _dataclass_defaults(DisplayConfig)
        assert "_internal" not in defaults
        assert "window_rows" not in defaults  # internal
        assert "empty_cell" in defaults

    def test_get_config_data_has_all_sections(self) -> None:
        data = Config.get_config_data()
        assert set(data) == {
            "display",
            "timing",
            "game_rules",
            "logging",
            "multi_play",
        }


# ---------------------------------------------------------------------------
# config_path platform resolution
# ---------------------------------------------------------------------------


class TestConfigPath:
    """Tests for ``Config.config_path`` platform logic."""

    def test_linux_uses_xdg_config_home(self, monkeypatch, tmp_path: Path) -> None:
        monkeypatch.setattr(sys, "platform", "linux")
        xdg = tmp_path / "xdgconfig"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
        assert Config.config_path() == xdg / "tetris-terminal" / "config.json"

    @pytest.mark.skipif(
        sys.platform != "linux", reason="Requires Unix Path.home() $HOME semantics"
    )
    def test_linux_falls_back_to_home_config(self, monkeypatch, tmp_path: Path) -> None:
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        assert Config.config_path() == (
            tmp_path / ".config" / "tetris-terminal" / "config.json"
        )

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific test")
    def test_macos_uses_application_support(self, monkeypatch, tmp_path: Path) -> None:
        monkeypatch.setattr(sys, "platform", "darwin")
        monkeypatch.setenv("HOME", str(tmp_path))
        assert Config.config_path() == (
            tmp_path
            / "Library"
            / "Application Support"
            / "tetris-terminal"
            / "config.json"
        )

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_windows_uses_appdata(self, monkeypatch, tmp_path: Path) -> None:
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setenv("APPDATA", str(tmp_path))
        assert Config.config_path() == (tmp_path / "tetris-terminal" / "config.json")
