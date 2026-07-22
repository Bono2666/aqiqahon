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
        
        # --> Verify Dashboard Produksi section with Total Box
        # Assert: 'Dashboard Produksi' section header is visible.
        await expect(page.get_by_text("Dashboard Produksi", exact=False).first).to_be_visible(timeout=15000), "Dashboard Produksi section header is visible."
        # Assert: 'Total Box' counter label is visible in the production dashboard.
        await expect(page.get_by_text("Total Box", exact=True).first).to_be_visible(timeout=15000), "Total Box counter label is visible in the production dashboard."
        # Assert: 'Total Kambing' counter label is visible in the production dashboard.
        await expect(page.get_by_text("Total Kambing", exact=True).first).to_be_visible(timeout=15000), "Total Kambing counter label is visible in the production dashboard."
        
        # --> Verify Kemasan Dan Souvenir card
        await page.get_by_text("Kemasan Dan Souvenir", exact=True).first.scroll_into_view_if_needed()
        # Assert: 'Kemasan Dan Souvenir' card header is visible.
        await expect(page.get_by_text("Kemasan Dan Souvenir", exact=True).first).to_be_visible(timeout=15000), "'Kemasan Dan Souvenir' card header is visible."
        
        # --> Verify Rekap Masakan card
        # Assert: 'Rekap Masakan' card header is visible.
        await expect(page.get_by_text("Rekap Masakan", exact=True).first).to_be_visible(timeout=15000), "'Rekap Masakan' card header is visible."
        
        # --> Verify Rekap Menu Olahan + Pendamping card
        # Assert: 'Rekap Menu Olahan + Pendamping' card header is visible.
        await expect(page.get_by_text("Rekap Menu Olahan + Pendamping", exact=True).first).to_be_visible(timeout=15000), "'Rekap Menu Olahan + Pendamping' card header is visible."
        
        # --> Verify Rekap Dekorasi card
        # Assert: 'Rekap Dekorasi' card header is visible.
        await expect(page.get_by_text("Rekap Dekorasi", exact=True).first).to_be_visible(timeout=15000), "'Rekap Dekorasi' card header is visible."
        
        # --> Verify Rekap Paket Nasi Box card
        # Assert: 'Rekap Paket Nasi Box' card header is visible.
        await expect(page.get_by_text("Rekap Paket Nasi Box", exact=True).first).to_be_visible(timeout=15000), "'Rekap Paket Nasi Box' card header is visible."
        
        # --> Verify Rekap Paket Kambing card
        # Assert: 'Rekap Paket Kambing' card header is visible.
        await expect(page.get_by_text("Rekap Paket Kambing", exact=True).first).to_be_visible(timeout=15000), "'Rekap Paket Kambing' card header is visible."
        
        # --> Verify Rekap Kambing Guling card
        # Assert: 'Rekap Kambing Guling' card header is visible.
        await expect(page.get_by_text("Rekap Kambing Guling", exact=True).first).to_be_visible(timeout=15000), "'Rekap Kambing Guling' card header is visible."
        
        # --> Verify Rekap Nampan + Prasmanan card
        # Assert: 'Rekap Nampan + Prasmanan' card header is visible.
        await expect(page.get_by_text("Rekap Nampan + Prasmanan", exact=True).first).to_be_visible(timeout=15000), "'Rekap Nampan + Prasmanan' card header is visible."
        
        # --> Verify Rekap Qurban card
        # Assert: 'Rekap Qurban' card header is visible.
        await expect(page.get_by_text("Rekap Qurban", exact=True).first).to_be_visible(timeout=15000), "'Rekap Qurban' card header is visible."
        
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
