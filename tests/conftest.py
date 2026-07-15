"""Pytest fixtures for tetris-terminal server tests."""

import asyncio
import contextlib
import socket
from typing import AsyncGenerator

import pytest_asyncio

from tetris.multiplay.server import serve
from tetris.utils import get_version


def _free_port() -> int:
    """Find a free TCP port on localhost.

    Returns:
        An available port number.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


async def _wait_for_server(port: int, timeout: float = 5.0) -> None:
    """Poll *port* with a raw TCP connect until the server is reachable.

    Args:
        port: TCP port to poll.
        timeout: Maximum time to wait in seconds.

    Raises:
        RuntimeError: If the server does not become reachable within
            *timeout* seconds.
    """
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", port),
                timeout=0.3,
            )
            writer.close()
            await writer.wait_closed()
            return
        except (OSError, asyncio.TimeoutError):
            if asyncio.get_event_loop().time() > deadline:
                raise RuntimeError(
                    f"Server did not start on port {port} within {timeout}s"
                )
            await asyncio.sleep(0.05)


@pytest_asyncio.fixture
async def server() -> AsyncGenerator[int, None]:
    """Start an unlimited tetris-server on a free port.

    Yields:
        The port number the server is listening on.
    """
    port = _free_port()
    task = asyncio.create_task(serve("127.0.0.1", port, get_version()))
    await _wait_for_server(port)
    yield port
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


@pytest_asyncio.fixture
async def server_full() -> AsyncGenerator[int, None]:
    """Start a tetris-server with ``max_rooms=1`` on a free port.

    Yields:
        The port number the server is listening on.
    """
    port = _free_port()
    task = asyncio.create_task(serve("127.0.0.1", port, get_version(), max_rooms=1))
    await _wait_for_server(port)
    yield port
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
