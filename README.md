![gameplay](./gameplay.gif)  
[English](README.md) | [中文](README-cn.md) | [Spanish](README.es-ES.md)

# Tetris Terminal

A terminal-based Tetris game.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)]()

### Features

- Modern Tetris design following the [Tetris Design Guideline](https://dn720004.ca.archive.org/0/items/2009-tetris-variant-concepts_202201/2009%20Tetris%20Design%20Guideline.pdf)
  - Extended Placement
  - Next Piece Preview
  - Super Rotation System (SRS)
  - Piece Holding
  - Shadow Piece
  - Modern Scoring System
  - Modern Level System

### Platform Support

Can basically run on any terminal emulator, even on a Linux tty.

### Installation & Usage

```bash
pip install tetris-terminal
tetris
```

### Controls

| Key            | Action                  |
| -------------- | ----------------------- |
| `a`, `←`       | Move left               |
| `d`, `→`       | Move right              |
| `w`, `↑`, `x`  | Rotate clockwise        |
| `z`            | Rotate counterclockwise |
| `s`, `↓`       | Soft drop               |
| `space`        | Hard drop               |
| `c`            | Hold piece              |
| `p`            | Pause                   |
| `q`            | Quit game               |

### CLI Options

| Option               | Description                                                             |
| -------------------- | ---------------------------------------------------------------------- |
| `--generate-config`  | Generate a default config file and exit                                |
| `--disable-config`   | Ignore the config file and use built-in defaults                       |
| `--server HOST:PORT` | Connect to a multiplayer (see below) server (default: `localhost:8765`) |
| `--version`          | Show version and exit                                                  |

### Multiplayer (Versus Mode)

See [VERSUS_MODE.md](docs/VERSUS_MODE.md)

### Configuration

See [CONFIG.md](docs/CONFIG.md)

### License

MIT License - see [LICENSE](LICENSE) for details.

### Acknowledgements

Inspired by [tinytetris](https://github.com/taylorconor/tinytetris) (a C implementation).

### To be implemented (Maybe)

1. Sound support
1. ...
