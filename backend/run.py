"""Custom Uvicorn entry point.

Patches Uvicorn's event loop selection for Windows + Python 3.14 compatibility.
Uvicorn 0.46.0 incorrectly selects SelectorEventLoop when running with --reload on Windows,
which breaks Playwright's subprocess execution (NotImplementedError in _make_subprocess_transport).

This script must be used INSTEAD of ``uvicorn app.main:app`` directly.
"""
from __future__ import annotations

import asyncio
import sys

# ---------------------------------------------------------------------------
# Patch: always use ProactorEventLoop on Windows
# ---------------------------------------------------------------------------

if sys.platform == "win32":
    # WORKAROUND: Uvicorn 0.46.0 incorrectly selects SelectorEventLoop
    # when --reload is used on Windows. ProactorEventLoop is required
    # for Playwright's subprocess execution.
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    import uvicorn.loops.asyncio as _uvicorn_loop

    _original_factory = _uvicorn_loop.asyncio_loop_factory  # noqa: F841

    def _patched_factory(use_subprocess: bool = False) -> type[asyncio.AbstractEventLoop]:
        return asyncio.ProactorEventLoop

    _uvicorn_loop.asyncio_loop_factory = _patched_factory


# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
