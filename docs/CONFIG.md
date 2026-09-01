## Configuration

With `tetris --generate-config`, a configuration file is created at:

| Platform | Path                                                        |
| -------- | ----------------------------------------------------------- |
| Linux    | `~/.config/tetris-terminal/config.json`                     |
| macOS    | `~/Library/Application Support/tetris-terminal/config.json` |
| Windows  | `%APPDATA%/tetris-terminal/config.json`                     |

The config file references a [JSON Schema](../config-schema.json), which editors can use to provide autocompletion and validation. All fields are optional — missing keys fall back to their defaults.

#### display

Visual appearance of the game interface.

| Key           | Default | Description            |
| ------------- | ------- | ---------------------- |
| `empty_cell`  | `"  "`  | Empty cell character   |
| `solid_cell`  | `"██"`  | Filled cell character  |
| `shadow_cell` | `"░░"`  | Shadow piece character |
| `bd_v`        | `"│"`   | Border vertical        |
| `bd_h`        | `"─"`   | Border horizontal      |
| `bd_tl`       | `"╭"`   | Border top-left        |
| `bd_tr`       | `"╮"`   | Border top-right       |
| `bd_bl`       | `"╰"`   | Border bottom-left     |
| `bd_br`       | `"╯"`   | Border bottom-right    |
| `bd_vr`       | `"├"`   | Border T-right         |
| `bd_vl`       | `"┤"`   | Border T-left          |
| `bd_hb`       | `"┬"`   | Border T-bottom        |
| `bd_ht`       | `"┴"`   | Border T-top           |

#### timing

Frame rate and animation settings.

| Key                         | Default | Description                                                                 |
| --------------------------- | ------- | --------------------------------------------------------------------------- |
| `fps`                       | `30`    | Frames per second                                                           |
| `clear_anim_flash_interval` | `0.05`  | Line clear animation flash interval (seconds); not available in versus mode |
| `clear_anim_duration`       | `0.3`   | Line clear animation duration (seconds); not available in versus mode       |

#### game_rules

Gameplay parameters.

| Key                        | Default | Description                                                       |
| -------------------------- | ------- | ----------------------------------------------------------------- |
| `max_lock_down_move_count` | `15`    | Max moves before a piece locks down; not available in versus mode |
| `time_attack_duration`     | `120`   | Time Attack mode duration (seconds)                               |

##### `multi_play`

Connection settings for multiplayer mode.

| Key    | Default       | Description     |
| ------ | ------------- | --------------- |
| `host` | `"localhost"` | Server address  |
| `port` | `8765`        | Server port     |
