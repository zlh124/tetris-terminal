"""End-to-end test for versus-mode seed synchronisation.

Verifies the full chain: server → ``MATCH_FOUND`` → ``NetworkClient.seed``
→ ``TetrisCore(seed=...)``. Two clients that match on the same server must
receive the same seed and therefore produce identical bag sequences.

The synchronous ``NetworkClient`` cannot share an event loop with the async
``server`` fixture (it would deadlock), so a real ``serve()`` is run in a
background thread with its own loop.
"""

from __future__ import annotations

import asyncio
import contextlib
import socket
import threading
import time

from tetris.config import Config
from tetris.core import TetrisCore
from tetris.enums import GameMode
from tetris.multiplay.network import NetworkClient
from tetris.multiplay.server import serve
from tetris.utils import get_version


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _wait_for_port(port: int, timeout: float = 5.0) -> None:
    """Poll *port* with a raw TCP connect until the server is reachable."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with contextlib.suppress(OSError):
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                return
        time.sleep(0.05)
    raise RuntimeError(f"server did not start on port {port} within {timeout}s")


@contextlib.contextmanager
def running_server(max_rooms: int = 0):
    """Run ``tetris-server`` in a background thread; yield its port."""
    port = _free_port()
    loop = asyncio.new_event_loop()
    task_holder: dict = {}

    def _run() -> None:
        asyncio.set_event_loop(loop)
        task = loop.create_task(
            serve("127.0.0.1", port, get_version(), max_rooms=max_rooms)
        )
        task_holder["task"] = task
        try:
            loop.run_until_complete(task)
        except asyncio.CancelledError:
            pass
        finally:
            loop.close()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    _wait_for_port(port)
    try:
        yield port
    finally:
        task = task_holder.get("task")
        if task is not None:
            loop.call_soon_threadsafe(task.cancel)
        thread.join(timeout=5)


def _draw_sequence(seed: int, n: int = 20) -> list:
    """Build a VERSUS core with *seed* and draw n+1 pieces (current + n).

    The second core must be created *after* the first's sequence is drawn so
    its ``__init__`` re-seeds the shared global RNG (TetrisCore uses the
    module-level ``random``, not an instance RNG).
    """
    core = TetrisCore(
        GameMode.VERSUS,
        Config(),
        lambda n: None,
        lambda title, msg: None,
        seed=seed,
    )
    assert core.cur_tetrimino, "cur_tetrimino is None"
    return [core.cur_tetrimino.shape] + [core._get_tetrimino().shape for _ in range(n)]


def test_matched_clients_share_seed_and_bag_sequence() -> None:
    """Two clients matched on one server get the same seed → same bag."""
    with running_server() as port:
        c1 = NetworkClient()
        c2 = NetworkClient()
        try:
            # Handshake both BEFORE waiting: otherwise c1's blocking
            # wait_for_match would prevent c2 from connecting.
            c1.handshake("127.0.0.1", port, get_version())
            c2.handshake("127.0.0.1", port, get_version())
            c1.wait_for_match()
            c2.wait_for_match()
        finally:
            c1.close()
            c2.close()

    # The bug being guarded against: the seed was previously dropped, leaving
    # both clients with seed=None and thus unsynchronised piece sequences.
    assert c1.seed is not None, "client did not capture the match seed"
    assert c2.seed is not None, "client did not capture the match seed"
    assert c1.seed == c2.seed, "server sent different seeds to the two clients"

    # Same seed ⇒ identical bag sequence (drawn past a replenish boundary so
    # the seeded shuffle is exercised, not just the initial 14-piece bag).
    seq1 = _draw_sequence(c1.seed, n=20)
    seq2 = _draw_sequence(c2.seed, n=20)
    assert seq1 == seq2
