## Configuración

Con `tetris --generate-config`, se crea un archivo de configuración en:

| Plataforma | Ruta                                                        |
| ---------- | ----------------------------------------------------------- |
| Linux      | `~/.config/tetris-terminal/config.json`                     |
| macOS      | `~/Library/Application Support/tetris-terminal/config.json` |
| Windows    | `%APPDATA%/tetris-terminal/config.json`                     |

El archivo de configuración hace referencia a un [JSON Schema](../config-schema.json), que los editores pueden usar para ofrecer autocompletado y validación. Todos los campos son opcionales; las claves que falten usarán sus valores predeterminados.

#### display

Apariencia visual de la interfaz del juego.

| Clave         | Predeterminado | Descripción                 |
| ------------- | -------------- | --------------------------- |
| `empty_cell`  | `"  "`         | Carácter de celda vacía     |
| `solid_cell`  | `"██"`         | Carácter de celda sólida    |
| `shadow_cell` | `"░░"`         | Carácter de la pieza sombra |
| `bd_v`        | `"│"`          | Borde vertical              |
| `bd_h`        | `"─"`          | Borde horizontal            |
| `bd_tl`       | `"╭"`          | Borde superior-izquierdo    |
| `bd_tr`       | `"╮"`          | Borde superior-derecho      |
| `bd_bl`       | `"╰"`          | Borde inferior-izquierdo    |
| `bd_br`       | `"╯"`          | Borde inferior-derecho      |
| `bd_vr`       | `"├"`          | Borde T-derecha             |
| `bd_vl`       | `"┤"`          | Borde T-izquierda           |
| `bd_hb`       | `"┬"`          | Borde T-inferior            |
| `bd_ht`       | `"┴"`          | Borde T-superior            |

#### timing

Configuración de velocidad de fotogramas y animaciones.

| Clave                       | Predeterminado | Descripción                                                                                |
| --------------------------- | -------------- | ------------------------------------------------------------------------------------------ |
| `fps`                       | `30`           | Fotogramas por segundo                                                                     |
| `clear_anim_flash_interval` | `0.05`         | Intervalo de parpadeo de la animación de limpieza de líneas (segundos); no disponible en el modo versus |
| `clear_anim_duration`       | `0.3`          | Duración de la animación de limpieza de líneas (segundos); no disponible en el modo versus |

#### game_rules

Parámetros de jugabilidad.

| Clave                      | Predeterminado | Descripción                                                                |
| -------------------------- | -------------- | -------------------------------------------------------------------------- |
| `max_lock_down_move_count` | `15`           | Movimientos máximos antes de que una pieza se fije; no disponible en el modo versus |
| `time_attack_duration`     | `120`          | Duración del modo Ataque al tiempo (segundos)                              |

##### `multi_play`

Configuración de conexión para el modo multijugador.

| Clave  | Predeterminado | Descripción            |
| ------ | -------------- | ---------------------- |
| `host` | `"localhost"`  | Dirección del servidor |
| `port` | `8765`         | Puerto del servidor    |
