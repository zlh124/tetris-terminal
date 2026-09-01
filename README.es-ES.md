![gameplay](./gameplay.gif)  
[English](README.md) | [中文](README-cn.md) | [Spanish](README.es-ES.md)

# Tetris Terminal

Un juego de Tetris basado en terminal.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)]()

### Funcionalidades

- Diseño moderno de Tetris siguiendo la [Guía de Diseño de Tetris](https://dn720004.ca.archive.org/0/items/2009-tetris-variant-concepts_202201/2009%20Tetris%20Design%20Guideline.pdf)
  - Colocación extendida
  - Vista previa de la siguiente pieza
  - Sistema SRS
  - Almacenamiento de piezas
  - Pieza sombra
  - Sistema de puntuación moderno
  - Sistema de niveles moderno

### Compatibilidad con plataformas

Puede ejecutarse en prácticamente cualquier emulador de terminal, incluso en una TTY de Linux.

### Instalación y uso

```bash
pip install tetris-terminal
tetris
```

### Controles

| Tecla          | Acción                       |
| -------------- | ---------------------------- |
| `a`, `←`       | Mover a la izquierda         |
| `d`, `→`       | Mover a la derecha           |
| `w`, `↑`, `x`  | Rotar en sentido horario     |
| `z`            | Rotar en sentido antihorario |
| `s`, `↓`       | Caída suave                  |
| `space`        | Caída instantánea            |
| `c`            | Guardar pieza                |
| `p`            | Pausar                       |
| `q`            | Salir del juego              |

### Opciones de CLI

| Opción               | Descripción                                                              |
| -------------------- | ------------------------------------------------------------------------ |
| `--generate-config`  | Generar un archivo de configuración predeterminado y salir               |
| `--disable-config`   | Ignorar el archivo de configuración y ejecutar con valores predeterminados |
| `--server HOST:PORT` | Conectar a un servidor multijugador (ver más abajo) (predeterminado: `localhost:8765`) |
| `--version`          | Mostrar versión y salir                                                  |

### Multijugador (Modo versus)

Ver [VERSUS_MODE.es-ES.md](docs/VERSUS_MODE.es-ES.md)

### Configuración

Ver [CONFIG.es-ES.md](docs/CONFIG.es-ES.md)

### Licencia

Licencia MIT - ver [LICENSE](LICENSE) para más detalles.

### Agradecimientos

Inspirado en [tinytetris](https://github.com/taylorconor/tinytetris) (una implementación en C).

### Por implementar (posiblemente)

1. sonido
1. ...
