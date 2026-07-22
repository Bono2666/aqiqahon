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
        
        # -> Fill 'bonocs' into the User ID field, fill 'Tr1-B0n0' into the Password field, then click the 'SIGN IN' button to submit the login form.
        # User ID text field
        elem = page.locator('[id="id_user_id"]')
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("bonocs")
        
        # -> Fill 'bonocs' into the User ID field, fill 'Tr1-B0n0' into the Password field, then click the 'SIGN IN' button to submit the login form.
        # Password password field
        elem = page.locator('[id="id_password"]')
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("Tr1-B0n0")
        
        # -> Fill 'bonocs' into the User ID field, fill 'Tr1-B0n0' into the Password field, then click the 'SIGN IN' button to submit the login form.
        # Sign in button
        elem = page.get_by_role('button', name='Sign in', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify unscheduled orders are displayed
        # Assert: Unscheduled orders label ('Belum Dijadwalkan') is visible on the dashboard.
        await expect(page.locator("xpath=/html/body/div[1]/div[4]/div/div[2]/div[1]/div/div/div/div[2]").nth(0)).to_contain_text("Belum Dijadwalkan", timeout=15000), "Unscheduled orders label ('Belum Dijadwalkan') is visible on the dashboard."
        
        # --> Verify cooking orders are displayed
        # Assert: The dashboard shows the 'Sedang Produksi' (cooking) widget.
        await expect(page.locator("xpath=/html/body/div[1]/div[4]/div/div[2]/div[2]/div/div/div/div[2]").nth(0)).to_contain_text("Sedang Produksi", timeout=15000), "The dashboard shows the 'Sedang Produksi' (cooking) widget."
        # Assert: The cooking orders count is displayed as 4 on the dashboard.
        await expect(page.locator("xpath=/html/body/div[1]/div[4]/div/div[2]/div[2]/div/div/div/div[2]").nth(0)).to_contain_text("4", timeout=15000), "The cooking orders count is displayed as 4 on the dashboard."
        
        # --> Verify packing orders are displayed
        await page.locator("xpath=/html/body/div[1]/div[4]/div/div[2]/div[4]/div/div/div/div[2]").nth(0).scroll_into_view_if_needed()
        # Assert: Packing orders widget is visible on the dashboard.
        await expect(page.locator("xpath=/html/body/div[1]/div[4]/div/div[2]/div[4]/div/div/div/div[2]").nth(0)).to_be_visible(timeout=15000), "Packing orders widget is visible on the dashboard."
        
        # --> Verify on delivery orders are displayed
        # Assert: The On Delivery widget (labelled 'Dalam Pengiriman') is displayed on the dashboard.
        await expect(page.locator("xpath=/html/body/div[1]/div[4]/div/div[3]/div[2]/div/div/div/div[2]").nth(0)).to_contain_text("Dalam Pengiriman", timeout=15000), "The On Delivery widget (labelled 'Dalam Pengiriman') is displayed on the dashboard."
        
        # --> Verify completed orders are displayed
        # Assert: The Completed orders widget labeled "Selesai" is visible on the dashboard.
        await expect(page.locator("xpath=/html/body/div[1]/div[4]/div/div[3]/div[3]/div/div/div/div[1]").nth(0)).to_contain_text("Selesai", timeout=15000), "The Completed orders widget labeled \"Selesai\" is visible on the dashboard."
        # Assert: The Completed orders count is displayed as 0.
        await expect(page.locator("xpath=/html/body/div[1]/div[4]/div/div[3]/div[3]/div/div/div/div[1]/h5").nth(0)).to_have_text("0", timeout=15000), "The Completed orders count is displayed as 0."
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
    