"""Configuration management for tetris-terminal.

Configuration is loaded from a platform-appropriate JSON file and merged
with built-in defaults so that missing keys never cause errors.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import MISSING, dataclass, field, fields
from pathlib import Path
from typing import Any


@dataclass
class DisplayConfig:
    """Visual display settings.

    Attributes:
        window_rows: Minimum terminal rows required for single-player mode.
        window_cols: Minimum terminal columns required for single-player mode.
        window_cols_versus_mode: Minimum terminal columns for versus mode.
        empty_cell: Character(s) rendered for an empty board cell.
        solid_cell: Character(s) rendered for an occupied board cell.
        shadow_cell: Character(s) rendered for the shadow (ghost) piece.
    """

    # internal (not loaded from config file)
    window_rows: int = 26
    window_cols: int = 44
    window_cols_versus_mode: int = 65

    # customizable
    empty_cell: str = "  "
    solid_cell: str = "██"
    shadow_cell: str = "░░"

    bd_v: str = "│"
    bd_h: str = "─"
    bd_tl: str = "╭"
    bd_tr: str = "╮"
    bd_bl: str = "╰"
    bd_br: str = "╯"
    bd_vr: str = "├"
    bd_vl: str = "┤"
    bd_hb: str = "┬"
    bd_ht: str = "┴"

    _internal: frozenset[str] = frozenset(
        {"window_rows", "window_cols", "window_cols_versus_mode"}
    )


@dataclass
class TimingConfig:
    """Frame rate and animation timing settings.

    Attributes:
        fps: Target frames per second for rendering.
        clear_anim_flash_interval: Seconds between line-clear flash toggles.
        clear_anim_duration: Total duration of the line-clear animation.
    """

    fps: int = 30
    clear_anim_flash_interval: float = 0.05
    clear_anim_duration: float = 0.3

    _internal: frozenset[str] = frozenset()


@dataclass
class MultiPlayConfig:
    """Multiplayer connection settings.

    Attributes:
        host: Server hostname or IP address.
        port: Server TCP port.
    """

    host: str = "localhost"
    port: int = 8765


@dataclass
class GameRulesConfig:
    """Gameplay rule parameters.

    Attributes:
        board_width: Number of columns in the playfield.
        board_height: Total rows (including 20-row buffer zone).
        max_lock_down_move_count: Max moves/rotates before forced lock-down.
        time_attack_duration: Duration in seconds for Time Attack mode.
    """

    # internal (not loaded from config file)
    board_width: int = 10
    board_height: int = 40

    # customizable
    max_lock_down_move_count: int = 15
    time_attack_duration: int = 120

    _internal: frozenset[str] = frozenset({"board_width", "board_height"})


def _default_log_dir() -> str:
    """Return the platform-appropriate default log directory.

    Returns:
        Absolute path to the log directory (e.g. ``~/.cache/tetris-terminal``).
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        xdg = os.environ.get("XDG_CACHE_HOME", "")
        base = Path(xdg) if xdg else Path.home() / ".cache"
    return str(base / "tetris-terminal")


@dataclass
class LoggingConfig:
    """Logging settings.

    Attributes:
        enabled: Whether file logging is active.
        level: Python logging level name (e.g. ``"DEBUG"``, ``"INFO"``).
        log_dir: Directory where log files are written.
    """

    enabled: bool = False
    level: str = "DEBUG"
    log_dir: str = field(default_factory=_default_log_dir)

    _internal: frozenset[str] = frozenset()


@dataclass
class Config:
    """Root configuration container, loaded from JSON with defaults for missing keys.

    Attributes:
        display: Visual display settings.
        timing: Frame rate and animation timing.
        game_rules: Gameplay parameters.
        logging: Logging behaviour.
        multi_play: Multiplayer server address.
    """

    display: DisplayConfig = field(default_factory=DisplayConfig)
    timing: TimingConfig = field(default_factory=TimingConfig)
    game_rules: GameRulesConfig = field(default_factory=GameRulesConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    multi_play: MultiPlayConfig = field(default_factory=MultiPlayConfig)

    @staticmethod
    def config_path() -> Path:
        """Return the platform-appropriate config file path.

        Returns:
            Path to ``config.json`` (e.g. ``~/.config/tetris-terminal/config.json``).
        """
        if sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            xdg = os.environ.get("XDG_CONFIG_HOME", "")
            base = Path(xdg) if xdg else Path.home() / ".config"
        return base / "tetris-terminal" / "config.json"

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        """Load config from a JSON file, falling back to built-in defaults.

        Args:
            path: Path to ``config.json``. Uses :meth:`config_path` when ``None``.

        Returns:
            A :class:`Config` instance with user values merged over defaults.
        """
        if path is None:
            path = cls.config_path()
        elif isinstance(path, str):
            path = Path(path)

        if not path.exists():
            return cls()

        try:
            with open(path, encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
        except (json.JSONDecodeError, OSError):
            return cls()

        return cls._merge(data)

    @classmethod
    def generate_config(cls, path: Path | None = None) -> Path:
        """Write a default config file and return its path.

        Creates parent directories as needed.

        Args:
            path: Target path. Uses :meth:`config_path` when ``None``.

        Returns:
            Path of the newly created config file.

        Raises:
            FileExistsError: If the config file already exists.
        """
        if path is None:
            path = cls.config_path()
        elif isinstance(path, str):
            path = Path(path)

        if path.exists():
            raise FileExistsError(f"config file already exists: {path}")

        data = cls.get_config_data()
        data["$schema"] = (
            "https://raw.githubusercontent.com/zlh124/tetris-terminal/refs/heads/master/config-schema.json"
        )

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.write("\n")
        return path

    @classmethod
    def _merge(cls, data: dict[str, Any]) -> Config:
        """Merge a dict (from JSON) into a Config, preserving defaults for missing keys.

        Args:
            data: Parsed JSON object.

        Returns:
            A new :class:`Config` with overrides applied.
        """
        display = _merge_dataclass(DisplayConfig, data.get("display", {}))
        timing = _merge_dataclass(TimingConfig, data.get("timing", {}))
        game_rules = _merge_dataclass(GameRulesConfig, data.get("game_rules", {}))
        logging_cfg = _merge_dataclass(LoggingConfig, data.get("logging", {}))
        multi_play = _merge_dataclass(MultiPlayConfig, data.get("multi_play", {}))
        return cls(
            display=display,
            timing=timing,
            game_rules=game_rules,
            logging=logging_cfg,
            multi_play=multi_play,
        )

    @classmethod
    def get_config_data(cls) -> dict[str, Any]:
        """Return a dict of configurable defaults for serialization.

        Returns:
            Dict with top-level keys ``"display"``, ``"timing"``, ``"game_rules"``,
            ``"logging"``, and ``"multi_play"``.
        """
        return {
            "display": _dataclass_defaults(DisplayConfig),
            "timing": _dataclass_defaults(TimingConfig),
            "game_rules": _dataclass_defaults(GameRulesConfig),
            "logging": _dataclass_defaults(LoggingConfig),
            "multi_play": _dataclass_defaults(MultiPlayConfig),
        }


def _merge_dataclass(cls_type: type, data: dict[str, Any]) -> Any:
    """Create a dataclass instance from a dict, skipping internal fields.

    Args:
        cls_type: The dataclass to instantiate.
        data: Key-value overrides (from JSON).

    Returns:
        An instance of *cls_type* with the provided values merged in.
    """
    internal: frozenset[str] = getattr(cls_type, "_internal", frozenset())
    kwargs: dict[str, Any] = {}
    for f in fields(cls_type):
        if f.name in data and f.name not in internal:
            kwargs[f.name] = data[f.name]
    return cls_type(**kwargs)


def _dataclass_defaults(cls_type: type) -> dict[str, Any]:
    """Return a dict of configurable (non-internal) defaults for a dataclass.

    Args:
        cls_type: The dataclass whose defaults are wanted.

    Returns:
        Mapping from field name to default value (excluding internal fields).
    """
    internal: frozenset[str] = getattr(cls_type, "_internal", frozenset())
    result: dict[str, Any] = {}
    for f in fields(cls_type):
        if f.name in internal or f.name.startswith("_"):
            continue
        value = f.default_factory() if f.default is MISSING else f.default  # type: ignore[union-attr]
        result[f.name] = value
    return result
