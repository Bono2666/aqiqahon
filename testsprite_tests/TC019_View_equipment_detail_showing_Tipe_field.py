import asyncio
import re
from playwright import async_api
from playwright.async_api import expect

async def run_test():
    pw = None
    browser = None
    context = None

    try:
        # Start a Playwright session in asynchronous mode
        pw = await async_api.async_playwright().start()

        # Launch a Chromium browser in headless mode with custom arguments
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--window-size=1280,720",
                "--disable-dev-shm-usage",
                "--ipc=host",
                "--single-process"
            ],
        )

        # Create a new browser context (like an incognito window)
        context = await browser.new_context()
        # Wider default timeout to match the agent's DOM-stability budget;
        # auto-waiting Playwright APIs (expect, locator.wait_for) inherit this.
        context.set_default_timeout(15000)

        # Open a new page in the browser context
        page = await context.new_page()

        # Interact with the page elements to simulate user flow
        # -> navigate
        await page.goto("http://localhost:8000")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        
        # -> Fill 'bono2666' into the User ID field and 'Tr1-B0n0' into the Password field, then click the 'Sign in' button.
        # User ID text field
        elem = page.locator('[id="id_user_id"]')
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("bono2666")
        
        # -> Fill 'bono2666' into the User ID field and 'Tr1-B0n0' into the Password field, then click the 'Sign in' button.
        # Password password field
        elem = page.locator('[id="id_password"]')
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("Tr1-B0n0")
        
        # -> Fill 'bono2666' into the User ID field and 'Tr1-B0n0' into the Password field, then click the 'Sign in' button.
        # Sign in button
        elem = page.get_by_role('button', name='Sign in', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'Data Master' menu item to open its submenu so the Pelengkap link can be selected.
        # Data Master link in sidebar
        elem = page.locator("span.nav-link-text", has_text="Data Master").first
        await elem.scroll_into_view_if_needed()
        await elem.click(timeout=10000)
        
        # -> Wait for submenu to expand
        await asyncio.sleep(1)
        
        # -> Click the 'Pelengkap' link in the Data Master submenu to open the Equipment list.
        # Pelengkap link
        elem = page.locator("span.nav-link-text", has_text="Pelengkap").first
        await elem.click(timeout=10000)
        
        # -> Click on the first equipment row in the table to open its detail view.
        # First equipment row
        elem = page.locator("table tbody tr").first
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify the equipment detail page shows the Tipe Pelengkap field
        # Assert: The 'ID Pelengkap:' page header is visible on the detail page.
        await expect(page.get_by_text("ID Pelengkap:", exact=False).first).to_be_visible(timeout=15000), "The 'ID Pelengkap:' page header is visible on the detail page."
        # Assert: The 'Tipe Pelengkap' label is visible on the detail page.
        await expect(page.get_by_text("Tipe Pelengkap", exact=True).first).to_be_visible(timeout=15000), "The 'Tipe Pelengkap' label is visible on the detail page."
        # Assert: The tipe dropdown select field is visible and disabled (read-only mode).
        await expect(page.locator('[id="id_tipe"]')).to_be_disabled(timeout=15000), "The tipe dropdown select field is visible and disabled (read-only mode)."
        # Assert: The 'Nama Pelengkap' label is visible on the detail page.
        await expect(page.get_by_text("Nama Pelengkap", exact=True).first).to_be_visible(timeout=15000), "The 'Nama Pelengkap' label is visible on the detail page."
        
        current_url = await page.evaluate("() => window.location.href")
        # Assert: page loaded with a URL (final outcome verified by the AI judge during the run)
        assert current_url, 'Page should have loaded with a URL'
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
