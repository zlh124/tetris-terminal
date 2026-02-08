![gameplay](./gameplay.gif)  
[English](README.md) | [中文](README-cn.md)

# Tetris Terminal🎮
一款基于终端的俄罗斯方块游戏，使用 Python 和 `curses` 库编写。

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)]()  

### 特性
- 遵循 [Tetris 设计指南](https://dn720004.ca.archive.org/0/items/2009-tetris-variant-concepts_202201/2009%20Tetris%20Design%20Guideline.pdf) 的现代俄罗斯方块设计
    - [x] 扩展放置（Extended Placement）
    - [x] 下一个方块预览（Next Piece Preview）
    - [x] SRS 旋转系统（SRS System）
    - [x] 方块暂存（Piece Holding）
    - [x] 阴影方块（Shadow Piece）
    - [x] 现代计分系统（Modern Scoring System）
    - [x] 现代等级系统（Modern Level System）

### 平台支持
基于 Python 的 [`curses`](https://docs.python.org/3/library/curses.html) 模块：
- ✅ **Linux/macOS**：开箱即用
- ✅️ **Windows**：需安装 [`windows-curses`](https://github.com/zephyrproject-rtos/windows-curses)

### 安装与使用
```bash
pip install tetris-terminal
tetris
```

### 控制方式
| 按键        | 功能         |
|------------|--------------|
| `a`, `←`   | 向左移动     |
| `d`, `→`   | 向右移动     |
| `w`, `↑`, `x` | 顺时针旋转 |
|    `z`     | 逆时针旋转   |
| `s`, `↓`   | 软降         |
|  `space`   | 硬降         |
|    `c`     | 暂存方块     |
|    `q`     | 退出游戏     |

### 许可证
MIT 许可证 - 详情见 [LICENSE](LICENSE)。

### 致谢
灵感来源于 [tinytetris](https://github.com/taylorconor/tinytetris)（一个 C 语言实现版本）。

### 计划填坑（可能）
1. 暂停与继续功能
2. 开始界面与游戏结束界面
3. 更佳的显示效果与音效支持
4. ...