## Versus Mode

#### Quick Start

```bash
# Start the server
tetris-server

# Player 1 connects to the server
tetris --server localhost:8765

# Player 2 connects to the server
tetris --server localhost:8765
```

Once both clients have connected, the server matches them automatically and the battle begins.

#### CLI Commands

| Command                     | Description                                           |
| --------------------------- | ----------------------------------------------------- |
| `tetris-server`             | Start the server                                      |
| `tetris`                    | In multiplayer mode, the default port and IP are used |
| `tetris --server HOST:PORT` | Set the port and IP for the multiplayer connection    |

#### `tetris-server` Options

| Option      | Default   | Description           |
| ----------- | --------- | --------------------- |
| `--host`    | `0.0.0.0` | Host address to bind  |
| `--port`    | `8765`    | Port to listen on     |
| `--version` |           | Show version and exit |
