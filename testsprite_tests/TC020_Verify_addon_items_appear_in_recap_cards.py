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
        
        # --> Assertions to verify final state
        
        # --> Verify Kemasan Dan Souvenir card structure
        # Assert: 'Kemasan Dan Souvenir' card header is visible.
        await expect(page.get_by_text("Kemasan Dan Souvenir", exact=True).first).to_be_visible(timeout=15000), "'Kemasan Dan Souvenir' card header is visible."
        # Assert: The Kemasan Dan Souvenir card contains a table with an 'Item' header.
        kemasan_card = page.locator("text=Kemasan Dan Souvenir").first.locator("xpath=ancestor::div[contains(@class,'card')]")
        await expect(kemasan_card.locator("th", has_text="Item").first).to_be_visible(timeout=15000), "The Kemasan Dan Souvenir card contains a table with an 'Item' header."
        # Assert: The Kemasan Dan Souvenir card contains a 'Jumlah' column header.
        await expect(kemasan_card.locator("th", has_text="Jumlah").first).to_be_visible(timeout=15000), "The Kemasan Dan Souvenir card contains a 'Jumlah' column header."
        
        # --> Verify Rekap Masakan card structure
        # Assert: 'Rekap Masakan' card header is visible.
        await expect(page.get_by_text("Rekap Masakan", exact=True).first).to_be_visible(timeout=15000), "'Rekap Masakan' card header is visible."
        # Assert: The Rekap Masakan card contains a table with a 'Masakan' header.
        masakan_card = page.locator("text=Rekap Masakan").first.locator("xpath=ancestor::div[contains(@class,'card')]")
        await expect(masakan_card.locator("th", has_text="Masakan").first).to_be_visible(timeout=15000), "The Rekap Masakan card contains a table with a 'Masakan' header."
        # Assert: The Rekap Masakan card contains a 'Box' column header.
        await expect(masakan_card.locator("th", has_text="Box").first).to_be_visible(timeout=15000), "The Rekap Masakan card contains a 'Box' column header."
        
        # --> Verify Rekap Menu Olahan + Pendamping card structure
        # Assert: 'Rekap Menu Olahan + Pendamping' card header is visible.
        await expect(page.get_by_text("Rekap Menu Olahan + Pendamping", exact=True).first).to_be_visible(timeout=15000), "'Rekap Menu Olahan + Pendamping' card header is visible."
        # Assert: The Rekap Menu Olahan card contains a table with a 'Menu' header.
        olahan_card = page.locator("text=Rekap Menu Olahan + Pendamping").first.locator("xpath=ancestor::div[contains(@class,'card')]")
        await expect(olahan_card.locator("th", has_text="Menu").first).to_be_visible(timeout=15000), "The Rekap Menu Olahan card contains a table with a 'Menu' header."
        # Assert: The Rekap Menu Olahan card contains a 'Box' column header.
        await expect(olahan_card.locator("th", has_text="Box").first).to_be_visible(timeout=15000), "The Rekap Menu Olahan card contains a 'Box' column header."
        
        # --> Verify that recap cards show either data rows or empty state
        # Assert: Each recap card (Kemasan, Masakan, Olahan) shows either data rows or a "Belum ada data" placeholder.
        kemasan_rows = await kemasan_card.locator("tbody tr").count()
        masakan_rows = await masakan_card.locator("tbody tr").count()
        olahan_rows = await olahan_card.locator("tbody tr").count()
        # Each card should have at least 1 row (either data or "Belum ada data")
        assert kemasan_rows >= 1, "Kemasan Dan Souvenir card has at least one row."
        assert masakan_rows >= 1, "Rekap Masakan card has at least one row."
        assert olahan_rows >= 1, "Rekap Menu Olahan card has at least one row."
        
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
