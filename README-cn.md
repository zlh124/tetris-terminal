![gameplay](./gameplay.gif)  
[English](README.md) | [中文](README-cn.md) | [Spanish](README.es-ES.md)

# Tetris Terminal

一款基于终端的俄罗斯方块游戏

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)]()

### 特性

- 遵循 [Tetris 设计指南](https://dn720004.ca.archive.org/0/items/2009-tetris-variant-concepts_202201/2009%20Tetris%20Design%20Guideline.pdf) 的现代俄罗斯方块设计
  - 扩展放置（Extended Placement）
  - 下一个方块预览（Next Piece Preview）
  - 超级旋转系统（SRS）
  - 方块暂存（Piece Holding）
  - 阴影方块（Shadow Piece）
  - 现代计分系统（Modern Scoring System）
  - 现代等级系统（Modern Level System）

### 平台支持

基本可以运行在任何终端模拟器上, 甚至可以在 linux tty 上运行。

### 安装与使用

```bash
pip install tetris-terminal
tetris
```

### 控制方式

| 按键          | 功能       |
| ------------- | ---------- |
| `a`, `←`      | 向左移动   |
| `d`, `→`      | 向右移动   |
| `w`, `↑`, `x` | 顺时针旋转 |
| `z`           | 逆时针旋转 |
| `s`, `↓`      | 软降       |
| `space`       | 硬降       |
| `c`           | 暂存方块   |
| `p`           | 暂停游戏   |
| `q`           | 退出游戏   |

### CLI 选项

| 选项                 | 说明                                                   |
| -------------------- | ------------------------------------------------------ |
| `--generate-config`  | 生成默认配置文件并退出                                 |
| `--disable-config`   | 忽略配置文件，使用内置默认值                           |
| `--server HOST:PORT` | 连接多人游戏（见下文）服务器（默认：`localhost:8765`） |
| `--version`          | 显示版本并退出                                         |

### 联机对战（Versus 模式）

见 [VERSUS_MODE-cn.md](docs/VERSUS_MODE-cn.md)

### 配置

见 [CONFIG-cn.md](docs/CONFIG-cn.md)

### 许可证

MIT 许可证 - 详情见 [LICENSE](LICENSE)。

### 致谢

灵感来源于 [tinytetris](https://github.com/taylorconor/tinytetris)（一个 C 语言实现版本）。

### 计划填坑（可能）

1. 音效支持
1. ...
