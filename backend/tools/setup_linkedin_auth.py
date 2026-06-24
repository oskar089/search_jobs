"""One-time LinkedIn auth setup tool.

Opens a headed (visible) Chromium window so you can log into LinkedIn
manually. After a successful login, it saves the browser session
(cookies, storage) to ``backend/linkedin_auth.json``.

Future Playwright-based scraping will reuse this session, bypassing the
need to log in headlessly (which LinkedIn often blocks).

Usage::

    cd backend/
    python tools/setup_linkedin_auth.py

Then:

1. A Chromium window will open pointing at linkedin.com/login.
2. Log in with your credentials (2FA if needed — it will work in headed).
3. Once you reach your LinkedIn feed, press **Enter** in the terminal.
4. The session is saved and the browser closes.

"""

from __future__ import annotations

import json
from pathlib import Path

AUTH_FILE = Path(__file__).parents[1] / "linkedin_auth.json"

# Same stealth script used by the scraper — we load it early so LinkedIn
# doesn't detect automation even during the headed setup.
STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
});
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});
Object.defineProperty(navigator, 'languages', {
    get: () => ['es-AR', 'en-US', 'en'],
});
if (typeof chrome !== 'undefined') {
    Object.defineProperty(chrome, 'runtime', {
        get: () => ({
            connect: () => ({}),
            sendMessage: () => ({}),
        }),
    });
}
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(param) {
    if (param === 37445) return 'Intel Inc.';
    if (param === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter(param);
};
"""


def main() -> None:
    from playwright.sync_api import sync_playwright

    if AUTH_FILE.exists():
        ans = input(
            f"linkedin_auth.json already exists ({AUTH_FILE}). "
            "Overwrite? [y/N] "
        )
        if ans.lower() != "y":
            print("Aborted.")
            return

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
        )
        context.add_init_script(STEALTH_SCRIPT)

        page = context.new_page()
        page.goto("https://www.linkedin.com/login", timeout=30000)
        page.wait_for_timeout(1000)

        print("\n=== LinkedIn Auth Setup ===")
        print("A Chromium window is open at linkedin.com/login.")
        print("Log in with your credentials (2FA will work in this headed mode).")
        print("Once you see your LinkedIn feed, come back here and press Enter.\n")

        input("Press Enter after successful login... ")

        # Save the session
        state = context.storage_state()
        AUTH_FILE.write_text(json.dumps(state, indent=2))
        print(f"\n✓ Auth state saved to {AUTH_FILE}")
        print("The LinkedIn scraper will now reuse this session.")

        context.close()
        browser.close()


if __name__ == "__main__":
    main()
