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
        
        # -> Fill the 'User ID' and 'Password' fields and click the 'SIGN IN' button to submit the login form.
        # User ID text field
        elem = page.locator('[id="id_user_id"]')
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("bonocs")
        
        # -> Fill the 'User ID' and 'Password' fields and click the 'SIGN IN' button to submit the login form.
        # Password password field
        elem = page.locator('[id="id_password"]')
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("Tr1-B0n0")
        
        # -> Fill the 'User ID' and 'Password' fields and click the 'SIGN IN' button to submit the login form.
        # Sign in button
        elem = page.get_by_role('button', name='Sign in', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the reminders button showing '12' (the bell/alerts) to open the reminders list.
        # 12 link
        elem = page.locator('[id="reminderDropdown"]')
        await elem.click(timeout=10000)
        
        # -> Click the reminder 'Pengiriman pesanan INV-100022/BOGOR/SA/07/2026 (Bono Faradianto) terlambat' to open its related schedule.
        # Pengiriman pesanan INV-100022/BOGOR/SA/07/2026... link
        elem = page.get_by_role('link', name='Pengiriman pesanan INV-100022/BOGOR/SA/07/2026 (Bono Faradianto) terlambat', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the '10.30 Bono Faradianto' calendar event to open its schedule details and verify the schedule entry opens.
        # 10.30 Bono Faradianto link
        elem = page.get_by_text('10.30 Bono Faradianto', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify overdue schedule reminders are displayed
        # Assert: Reminders badge shows '12', indicating reminders are present.
        await expect(page.locator("xpath=/html/body/div[1]/nav/div/div/ul/li[2]/a").nth(0)).to_contain_text("12", timeout=15000), "Reminders badge shows '12', indicating reminders are present."
        # Assert: The reminders area displays the 'Pengingat Hari Ini' header, confirming reminders are shown.
        await expect(page.locator("xpath=/html/body/div[1]/nav/div/div/ul/li[2]").nth(0)).to_contain_text("Pengingat Hari Ini", timeout=15000), "The reminders area displays the 'Pengingat Hari Ini' header, confirming reminders are shown."
        
        # --> Verify a related schedule opens from a reminder
        # Assert: URL contains '/jadwal/' confirming navigation to the schedule page.
        await expect(page).to_have_url(re.compile("/jadwal/"), timeout=15000), "URL contains '/jadwal/' confirming navigation to the schedule page."
        await page.locator("xpath=/html/body/div[1]/div[4]/div/div[1]/div/div/div[2]/div[2]/div/table/tbody/tr/td/div/div/div/table/tbody/tr[3]/td[6]/div/div[2]/div[1]/a").nth(0).scroll_into_view_if_needed()
        # Assert: The calendar event '10.30 Bono Faradianto' is visible, indicating the related schedule is present.
        await expect(page.locator("xpath=/html/body/div[1]/div[4]/div/div[1]/div/div/div[2]/div[2]/div/table/tbody/tr/td/div/div/div/table/tbody/tr[3]/td[6]/div/div[2]/div[1]/a").nth(0)).to_be_visible(timeout=15000), "The calendar event '10.30 Bono Faradianto' is visible, indicating the related schedule is present."
        await page.locator("xpath=/html/body/div[1]/div[4]/div/div[2]/div/div/div[2]/div[1]/div/div[6]/div[1]/div/label").nth(0).scroll_into_view_if_needed()
        # Assert: The 'Driver' label is visible in the order detail modal, confirming the schedule details opened.
        await expect(page.locator("xpath=/html/body/div[1]/div[4]/div/div[2]/div/div/div[2]/div[1]/div/div[6]/div[1]/div/label").nth(0)).to_be_visible(timeout=15000), "The 'Driver' label is visible in the order detail modal, confirming the schedule details opened."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    