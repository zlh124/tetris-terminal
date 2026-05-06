![gameplay](./gameplay.gif)  
[English](README.md) | [中文](README-cn.md)

# Tetris Terminal🎮

A terminal-based Tetris game written in Python using the `curses` library.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)]()

### Features

- Modern Tetris design following the [Tetris Design Guideline](https://dn720004.ca.archive.org/0/items/2009-tetris-variant-concepts_202201/2009%20Tetris%20Design%20Guideline.pdf)
  - [x] Extended Placement
  - [x] Next Piece Preview
  - [x] SRS System
  - [x] Piece Holding
  - [x] Shadow Piece
  - [x] Modern Scoring System
  - [x] Modern Level System

### Platform Support

Based on Python's [`curses`](https://docs.python.org/3/library/curses.html) module:

- ✅ **Linux/macOS**: Works out of the box
- ✅️ **Windows**: With [`windows-curses`](https://github.com/zephyrproject-rtos/windows-curses)
- Can run on basically any terminal setup, even a linux tty.

### Installation & Usage

```bash
pip install tetris-terminal
tetris
```

### Controls

| Key          | Action     |
| ------------ | ---------- |
| `a`, `←`     | Move left  |
| `d`, `→`     | Move right |
| `w`, `↑`,`x` | Rotate cw  |
| `z`          | Rotate ccw |
| `s`, `↓`     | Soft drop  |
| `space`      | Hard drop  |
| `c`          | Hold       |
| `p`          | Pause      |
| `q`          | Quit game  |

### CLI Options

| Option              | Description                                          |
| ------------------- | ---------------------------------------------------- |
| `--generate-config` | Generate a default config file and exit              |
| `--disable-config`  | Ignore config file and run with built-in defaults    |
| `--version`         | Show version and exit                                |

### Configuration

On first run, or via `tetris --generate-config`, a configuration file is created at:

| Platform | Path                                                       |
| -------- | ---------------------------------------------------------- |
| Linux    | `~/.config/tetris-terminal/config.json`                    |
| macOS    | `~/Library/Application Support/tetris-terminal/config.json` |
| Windows  | `%APPDATA%/tetris-terminal/config.json`                    |

The config file references a [JSON Schema](config-schema.json) for editor autocompletion and validation. All fields are optional — missing keys fall back to their defaults.

#### display

Visual appearance of the game board.

| Key            | Default | Description         |
| -------------- | ------- | ------------------- |
| `empty_cell`   | `"  "`  | Empty cell character |
| `solid_cell`   | `"██"`  | Filled cell character |
| `shadow_cell`  | `"░░"`  | Shadow piece character |
| `bd_v`         | `"│"`   | Border vertical      |
| `bd_h`         | `"─"`   | Border horizontal    |
| `bd_tl`        | `"╭"`   | Border top-left      |
| `bd_tr`        | `"╮"`   | Border top-right     |
| `bd_bl`        | `"╰"`   | Border bottom-left   |
| `bd_br`        | `"╯"`   | Border bottom-right  |
| `bd_vr`        | `"├"`   | Border T-right       |
| `bd_vl`        | `"┤"`   | Border T-left        |
| `bd_hb`        | `"┬"`   | Border T-bottom      |
| `bd_ht`        | `"┴"`   | Border T-top         |

#### timing

Frame rate and animation settings.

| Key                        | Default | Description              |
| -------------------------- | ------- | ------------------------ |
| `fps`                      | `30`    | Frames per second        |
| `clear_anim_flash_interval`| `0.05`  | Line clear flash interval (seconds) |
| `clear_anim_duration`      | `0.3`   | Line clear animation duration (seconds) |

#### game_rules

Gameplay parameters.

| Key                        | Default | Description                         |
| -------------------------- | ------- | ----------------------------------- |
| `max_lock_down_move_count` | `15`    | Max moves before piece locks down   |
| `time_attack_duration`     | `120`   | Time Attack mode duration (seconds) |

### License

MIT License - see [LICENSE](LICENSE) for details.

### Acknowledgements

Idea from [tinytetris](https://github.com/taylorconor/tinytetris) (a C implementation).

### Going to be implemented(Maybe)

1. sound
1. ...
