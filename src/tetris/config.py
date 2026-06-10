"""configuration for tetris-terminal"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import MISSING, dataclass, field, fields
from pathlib import Path


@dataclass
class DisplayConfig:
    """visual display settings"""

    # internal (not loaded from config file)
    window_rows: int = 26
    window_cols: int = 44
    window_cols_versus_mode = 65

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

    _internal = frozenset({"window_rows", "window_cols", "window_cols_versus_mode"})


@dataclass
class TimingConfig:
    """frame rate and animation timing"""

    fps: int = 30
    clear_anim_flash_interval: float = 0.05
    clear_anim_duration: float = 0.3

    _internal = frozenset()


@dataclass
class MultiPlayConfig:
    host: str = "localhost"
    port: int = 8765


@dataclass
class GameRulesConfig:
    """gameplay rule parameters"""

    # internal (not loaded from config file)
    board_width: int = 10
    board_height: int = 40

    # customizable
    max_lock_down_move_count: int = 15
    time_attack_duration: int = 120

    _internal = frozenset({"board_width", "board_height"})


def _default_log_dir() -> str:
    """Return platform-appropriate log directory default."""
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
    """logging settings"""

    enabled: bool = False
    level: str = "DEBUG"
    log_dir: str = field(default_factory=_default_log_dir)

    _internal = frozenset()


@dataclass
class Config:
    """root configuration, loaded from JSON with defaults for missing keys"""

    display: DisplayConfig = field(default_factory=DisplayConfig)
    timing: TimingConfig = field(default_factory=TimingConfig)
    game_rules: GameRulesConfig = field(default_factory=GameRulesConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    multi_play: MultiPlayConfig = field(default_factory=MultiPlayConfig)

    @staticmethod
    def config_path() -> Path:
        """Return platform-appropriate config file path."""
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
        """Load config from JSON file, falling back to defaults for missing keys."""
        if path is None:
            path = cls.config_path()
        elif isinstance(path, str):
            path = Path(path)

        if not path.exists():
            return cls()

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return cls()

        return cls._merge(data)

    @classmethod
    def generate_config(cls, path: Path | None = None) -> Path:
        """Write default config file and return its path. Creates parent directories.

        :raises FileExistsError: if the config file already exists
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
    def _merge(cls, data: dict) -> Config:
        """Merge a dict (from JSON) into a Config, preserving defaults for missing keys."""
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
    def get_config_data(cls) -> dict:
        return {
            "display": _dataclass_defaults(DisplayConfig),
            "timing": _dataclass_defaults(TimingConfig),
            "game_rules": _dataclass_defaults(GameRulesConfig),
            "logging": _dataclass_defaults(LoggingConfig),
            "multi_play": _dataclass_defaults(MultiPlayConfig),
        }


def _merge_dataclass(cls_type, data: dict):
    """Create a dataclass instance from a dict, skipping internal fields."""
    internal = getattr(cls_type, "_internal", frozenset())
    kwargs = {}
    for f in fields(cls_type):
        if f.name in data and f.name not in internal:
            kwargs[f.name] = data[f.name]
    return cls_type(**kwargs)


def _dataclass_defaults(cls_type) -> dict:
    """Return a dict of configurable (non-internal) defaults for a dataclass."""
    internal = getattr(cls_type, "_internal", frozenset())
    result = {}
    for f in fields(cls_type):
        if f.name in internal or f.name.startswith("_"):
            continue
        value = f.default_factory() if f.default is MISSING else f.default  # type: ignore
        result[f.name] = value
    return result
