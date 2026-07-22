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
        
        # -> Wait for fetchReminders() to execute and update badge visibility.
        await asyncio.sleep(3)
        
        # --> Assertions to verify final state
        
        # --> Verify hamburger badge (desktop) exists in the DOM
        # Assert: The desktop hamburger notification badge element (hamburger-badge) exists in the DOM.
        await expect(page.locator('[id="hamburger-badge"]')).to_be_attached(timeout=15000), "The desktop hamburger notification badge element (hamburger-badge) exists in the DOM."
        
        # --> Verify hamburger mobile badge exists in the DOM
        # Assert: The mobile hamburger notification badge element (hamburger-mobile-badge) exists in the DOM.
        await expect(page.locator('[id="hamburger-mobile-badge"]')).to_be_attached(timeout=15000), "The mobile hamburger notification badge element (hamburger-mobile-badge) exists in the DOM."
        
        # --> Verify Transaksi sidebar badge exists in the DOM
        # Assert: The Transaksi sidebar notification badge element (transaksi-badge) exists in the DOM.
        await expect(page.locator('[id="transaksi-badge"]')).to_be_attached(timeout=15000), "The Transaksi sidebar notification badge element (transaksi-badge) exists in the DOM."
        
        # --> Verify bell reminder badge exists in the DOM
        # Assert: The bell icon reminder badge element (reminder-badge) exists in the DOM.
        await expect(page.locator('[id="reminder-badge"]')).to_be_attached(timeout=15000), "The bell icon reminder badge element (reminder-badge) exists in the DOM."
        
        # --> Verify badge visibility logic is consistent
        # Get the reminder count from the bell badge
        reminder_count_text = await page.locator('[id="reminder-count"]').text_content()
        reminder_count = int(reminder_count_text) if reminder_count_text and reminder_count_text.isdigit() else 0
        
        # If reminders exist, badges should be visible (not have d-none class)
        if reminder_count > 0:
            # Assert: When reminders exist, the hamburger badge should be visible.
            await expect(page.locator('[id="hamburger-badge"]')).to_be_visible(timeout=5000), "When reminders exist, the hamburger badge should be visible."
            # Assert: When reminders exist, the Transaksi sidebar badge should be visible.
            await expect(page.locator('[id="transaksi-badge"]')).to_be_visible(timeout=5000), "When reminders exist, the Transaksi sidebar badge should be visible."
        else:
            # Assert: When no reminders exist, the hamburger badge should be hidden.
            await expect(page.locator('[id="hamburger-badge"]')).to_have_class(re.compile(r"d-none"), timeout=5000), "When no reminders exist, the hamburger badge should be hidden."
            # Assert: When no reminders exist, the Transaksi sidebar badge should be hidden.
            await expect(page.locator('[id="transaksi-badge"]')).to_have_class(re.compile(r"d-none"), timeout=5000), "When no reminders exist, the Transaksi sidebar badge should be hidden."
        
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
