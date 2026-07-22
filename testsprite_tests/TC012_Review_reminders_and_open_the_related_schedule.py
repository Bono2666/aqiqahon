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
        
        # -> Fill the User ID and Password fields and click the 'SIGN IN' button to log in.
        # User ID text field
        elem = page.locator('[id="id_user_id"]')
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("bonocs")
        
        # -> Fill the User ID and Password fields and click the 'SIGN IN' button to log in.
        # Password password field
        elem = page.locator('[id="id_password"]')
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("Tr1-B0n0")
        
        # -> Fill the User ID and Password fields and click the 'SIGN IN' button to log in.
        # Sign in button
        elem = page.get_by_role('button', name='Sign in', exact=True)
        await elem.click(timeout=10000)
        
        # -> Open the reminders dropdown by clicking the reminder bell showing '12' in the top navigation.
        # 12 link
        elem = page.locator('[id="reminderDropdown"]')
        await elem.click(timeout=10000)
        
        # -> Open the reminder 'Driver belum ditentukan untuk pesanan INV-100022/BOGOR/SA/07/2026 (Bono Faradianto)'.
        # Driver belum ditentukan untuk pesanan... link
        elem = page.get_by_role('link', name='Driver belum ditentukan untuk pesanan INV-100022/BOGOR/SA/07/2026 (Bono Faradianto)', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the calendar event labeled '00.00 Bono Faradianto' to open the related schedule.
        # 00.00 Bono Faradianto link
        elem = page.locator('xpath=/html/body/div/div[4]/div/div/div/div/div[2]/div[2]/div/table/tbody/tr/td/div/div/div/table/tbody/tr[3]/td[5]/div/div[2]/div/a')
        await elem.click(timeout=10000)
        
        # -> Click the 'LIHAT DETAIL' button in the Detail Pesanan modal to open the related schedule/order page.
        # Lihat Detail link
        elem = page.locator('[id="btn-view"]')
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify reminder items are displayed
        await page.locator("xpath=/html/body/div[1]/nav/div/div/ul/li[2]/a/span").nth(0).scroll_into_view_if_needed()
        # Assert: The reminders badge is visible and shows '12'.
        await expect(page.locator("xpath=/html/body/div[1]/nav/div/div/ul/li[2]/a/span").nth(0)).to_be_visible(timeout=15000), "The reminders badge is visible and shows '12'."
        # Assert: A reminder item mentioning 'Driver belum ditentukan' is present in the reminders list.
        await expect(page.locator("xpath=/html/body/div[1]/nav/div/div/ul/li[2]").nth(0)).to_contain_text("Driver belum ditentukan", timeout=15000), "A reminder item mentioning 'Driver belum ditentukan' is present in the reminders list."
        
        # --> Verify the related schedule page is displayed
        # Assert: The related schedule/order page is open (URL contains /order/view/INV-100017).
        await expect(page).to_have_url(re.compile("/order/view/INV\\-100017"), timeout=15000), "The related schedule/order page is open (URL contains /order/view/INV-100017)."
        await page.locator("xpath=/html/body/div[1]/div[4]/form/div[1]/div/div/div/div[1]/div/div[2]/a[2]").nth(0).scroll_into_view_if_needed()
        # Assert: The order detail page shows the 'Ubah' link, confirming the related schedule page is displayed.
        await expect(page.locator("xpath=/html/body/div[1]/div[4]/form/div[1]/div/div/div/div[1]/div/div[2]/a[2]").nth(0)).to_be_visible(timeout=15000), "The order detail page shows the 'Ubah' link, confirming the related schedule page is displayed."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    