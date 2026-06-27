"""Shared stealth module for Playwright browser automation.

Provides:
- get_stealth_script(): Returns the Playwright stealth JavaScript payload
- apply_stealth(context): Injects stealth script into a browser context
- calculate_backoff(attempt): Exponential backoff with jitter for retries
"""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext

logger = logging.getLogger(__name__)

# Lazy import to avoid heavy imports at module load time
_stealth_script: str | None = None


def get_stealth_script() -> str:
    """Return the Playwright stealth JavaScript payload.

    The payload is an IIFE that evades bot detection by patching
    navigator.webdriver, Chrome runtime, WebGL vendor, etc.
    """
    global _stealth_script
    if _stealth_script is None:
        from playwright_stealth import Stealth

        _stealth_script = Stealth(
            # Disable navigator_user_agent to keep our custom UA
            navigator_user_agent=False,
            navigator_user_agent_data=False,
        ).script_payload
    return _stealth_script


async def apply_stealth(context: BrowserContext) -> None:
    """Inject stealth scripts into a browser context before navigation.

    Args:
        context: A Playwright BrowserContext to inject stealth into.
    """
    script = get_stealth_script()
    await context.add_init_script(script)
    logger.debug("Stealth script injected into browser context")


def calculate_backoff(attempt: int) -> float:
    """Calculate exponential backoff with jitter in milliseconds.

    Formula: min(16000, 1000 * 2**attempt + random.uniform(0, 500))

    Args:
        attempt: Zero-based retry attempt number.

    Returns:
        Sleep duration in milliseconds (float).
    """
    base = 1000 * (2**attempt)
    jitter = random.uniform(0, 500)
    return min(16000.0, base + jitter)
