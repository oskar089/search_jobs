"""Rate limiting middleware using slowapi.

Provides a shared ``Limiter`` instance and an ``init_rate_limiting()``
function to wire it into the FastAPI app.

Uses slowapi's in-memory storage (single-instance deployment). If the app
scales to multiple workers, swap to Redis storage.
"""

from __future__ import annotations

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from fastapi import FastAPI

limiter = Limiter(key_func=get_remote_address, default_limits=[])


def init_rate_limiting(app: FastAPI) -> None:
    """Wire slowapi rate limiting into the FastAPI application.

    Must be called after the app is created but before running.
    Registers the limiter in ``app.state`` and adds the 429 handler.
    """
    app.state.limiter = limiter
    app.add_exception_handler(429, _rate_limit_exceeded_handler)
