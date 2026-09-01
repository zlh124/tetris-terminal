## Modo versus

#### Inicio rápido

```bash
# Iniciar el servidor
tetris-server

# El jugador 1 se conecta al servidor
tetris --server localhost:8765

# El jugador 2 se conecta al servidor
tetris --server localhost:8765
```

Una vez que ambos clientes se han conectado, el servidor los empareja automáticamente y comienza la batalla.

#### Comandos de CLI

| Comando                     | Descripción                                                    |
| --------------------------- | -------------------------------------------------------------- |
| `tetris-server`             | Iniciar el servidor                                            |
| `tetris`                    | En el modo multijugador se usan el puerto y la IP predeterminados |
| `tetris --server HOST:PORT` | Establecer el puerto y la IP para la conexión multijugador     |

#### Opciones de `tetris-server`

| Opción      | Predeterminado | Descripción                     |
| ----------- | -------------- | ------------------------------- |
| `--host`    | `0.0.0.0`      | Dirección del host para enlazar |
| `--port`    | `8765`         | Puerto para escuchar            |
| `--version` |                | Mostrar versión y salir         |
