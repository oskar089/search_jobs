"""E2E tests for the profile import flow.

Tests the frontend UI by verifying that the import section renders correctly
with provider tabs, URL input, and import button.

Requires:
  - Frontend dev server running on FRONTEND_URL (default: http://localhost:5173)
  - Backend server running on API_URL (default: http://localhost:8000/api)
  - Playwright browsers installed (run ``playwright install chromium``)

Usage:
  pytest backend/tests/test_import_e2e.py -v --headed
"""

from __future__ import annotations

import pytest
from playwright.async_api import Page, expect


@pytest.mark.e2e
class TestProfileImportSection:
    """Verify the "Importar perfil" section renders and behaves correctly."""

    @pytest.mark.profile
    async def test_import_section_renders(self, authed_page: Page) -> None:
        """The import section, provider tabs, and URL input should be visible."""
        page = authed_page

        # Wait for the page to fully load
        await page.wait_for_load_state("networkidle")

        # Verify the main section heading
        await expect(
            page.get_by_text("Importar perfil"),
        ).to_be_visible()

        # Verify provider tabs
        await expect(
            page.get_by_role("button", name="LinkedIn"),
        ).to_be_visible()
        await expect(
            page.get_by_role("button", name="Infojobs"),
        ).to_be_visible()

        # Verify URL input and import button
        await expect(
            page.get_by_placeholder("https://linkedin.com/in/tu-perfil"),
        ).to_be_visible()
        await expect(
            page.get_by_role("button", name="Importar"),
        ).to_be_visible()

    @pytest.mark.profile
    async def test_provider_tabs_switch(self, authed_page: Page) -> None:
        """Clicking a provider tab should highlight it and update the placeholder."""
        page = authed_page

        # Click Infojobs tab
        await page.get_by_role("button", name="Infojobs").click()

        # The placeholder should update to show the Infojobs hint
        await expect(
            page.get_by_placeholder("https://infojobs.net/tu-perfil"),
        ).to_be_visible()

        # Click back to LinkedIn
        await page.get_by_role("button", name="LinkedIn").click()

        # The placeholder should switch back
        await expect(
            page.get_by_placeholder("https://linkedin.com/in/tu-perfil"),
        ).to_be_visible()

    @pytest.mark.profile
    async def test_url_input_accepts_text(self, authed_page: Page) -> None:
        """Typing a URL into the input should work."""
        page = authed_page

        test_url = "https://linkedin.com/in/testuser"
        url_input = page.get_by_placeholder("https://linkedin.com/in/tu-perfil")
        await url_input.fill(test_url)

        # Verify the value was accepted
        await expect(url_input).to_have_value(test_url)

    @pytest.mark.profile
    async def test_cv_section_renders(self, authed_page: Page) -> None:
        """The "Subir CV" section should be visible above the import section."""
        page = authed_page

        # The CV section heading
        await expect(page.get_by_text("Subir CV")).to_be_visible()

        # The drop zone text
        await expect(
            page.get_by_text("Arrastra un PDF aquí o haz clic para seleccionar"),
        ).to_be_visible()

    @pytest.mark.profile
    async def test_import_and_cv_sections_screenshot(
        self,
        authed_page: Page,
    ) -> None:
        """Take a screenshot of the profile page showing both sections."""
        page = authed_page

        # Wait for full render
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1000)  # Extra time for React rendering

        # Scroll the import section into view and take a screenshot
        import_section = page.get_by_text("Importar perfil")
        await import_section.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)

        await page.screenshot(
            path="test_results/profile_import_section.png",
            full_page=True,
        )
