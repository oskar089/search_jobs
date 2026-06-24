"""Persistent async event loop for Celery tasks.

Celery workers on Windows run with --pool=solo (no prefork/threads pools
available), which means every task runs in the same thread. Using
asyncio.run() creates and closes a new event loop each time, and SQLAlchemy
async engine connections get orphaned when the loop closes — causing
InterfaceError and "Event loop is closed" failures.

This module creates a SINGLE persistent event loop at import time, so all
tasks reuse the same loop without ever closing it.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)

_LOOP: asyncio.AbstractEventLoop | None = None


def get_loop() -> asyncio.AbstractEventLoop:
    """Return the process-wide persistent event loop."""
    global _LOOP  # noqa: PLW0603
    if _LOOP is None or _LOOP.is_closed():
        _LOOP = asyncio.new_event_loop()
        asyncio.set_event_loop(_LOOP)
        logger.debug("Created persistent event loop %s", _LOOP)
    return _LOOP


def run_async(coro):
    """Run a coroutine in the persistent event loop.

    Replaces asyncio.run() in all Celery task wrappers.
    """
    loop = get_loop()
    return loop.run_until_complete(coro)
