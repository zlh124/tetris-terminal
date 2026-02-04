![gameplay](./gameplay.gif)  
# Tetris Terminal🎮
A terminal-based Tetris game written in Python using the `curses` library.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)]()  

### Features
- Modern Tetris design following the [Tetris Design Guideline](https://dn720004.ca.archive.org/0/items/2009-tetris-variant-concepts_202201/2009%20Tetris%20Design%20Guideline.pdf)
    - [x] Extended Placement
    - [x] Next Piece Preview
    - [x] SRS System
    - [x] Piece Holding
    - [ ] Scoring System
    - [ ] Level System

### Platform Support
Based on Python's [`curses`](https://docs.python.org/3/library/curses.html) module:
- ✅ **Linux/macOS**: Works out of the box
- ✅️ **Windows**: With [`windows-curses`](https://github.com/zephyrproject-rtos/windows-curses)

### Installation & Usage
```bash
pip install tetris-terminal
tetris
```

### Controls
| Key        | Action     |
|------------|------------|
| `a`, `←`   | Move left  |
| `d`, `→`   | Move right |
|`w`, `↑`,`x`| Rotate cw  |
|    `z`     | Rotate ccw |
| `s`, `↓`   | Soft drop  |
|  `space`   | Hard drop  |
|    `c`     | Hold       |
|    `q`     | Quit game  |

### License
MIT License - see [LICENSE](LICENSE) for details.

### Acknowledgements
Idea from [tinytetris](https://github.com/taylorconor/tinytetris) (a C implementation).