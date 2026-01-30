![gameplay](./gameplay.gif)  
# Tetris game in python
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)]()  
This is a simple tetris game written in python, that can be played in the terminal.

### Features
- Classic Tetris gameplay with 7 standard tetrominoes
- Real-time score
- Next piece preview

### Platform Support
Based on Python's [`curses`](https://docs.python.org/3/library/curses.html) module:
- ✅ **Linux/macOS**: Works out of the box
- ⚠️ **Windows**: Requires [`windows-curses`](https://pypi.org/project/windows-curses/) (auto-installed via dependencies)

### Installation & Usage
- Using [uv](https://github.com/astral-sh/uv) (recommended):
```bash
uv pip install -e .
pytris
```
- Using pip (alternative):
```bash
pip install -e .
tetris
```

### Controls
| Key       | Action          |
|-----------|-----------------|
|    `a`    | Move left       |
|    `d`    | Move right      |
|    `w`    | Rotate piece    |
|    `s`    | Hard drop       |
|    `q`    | Quit game       |

### License
MIT License - see [LICENSE](LICENSE) for details.

### Acknowledgements
Game logic adapted from [tinytetris](https://github.com/taylorconor/tinytetris) (a C implementation).
