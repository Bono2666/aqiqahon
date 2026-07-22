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
        
        # -> Click the '+ TAMBAH PELengkap' button to open the Add Equipment form.
        # Tambah Pelengkap link
        elem = page.get_by_role('link', name='Tambah Pelengkap', exact=True)
        await elem.click(timeout=10000)
        
        # -> Generate a unique equipment ID using timestamp
        import time
        unique_suffix = str(int(time.time()))[-6:]
        equipment_id = f"EQ{unique_suffix}"
        equipment_name = f"Test Pelengkap {unique_suffix}"
        
        # -> Fill 'ID Pelengkap' with a unique code, fill 'Nama Pelengkap' with a name, select a Tipe, and click 'Simpan'.
        # equipment_id text field
        elem = page.locator('[id="id_equipment_id"]')
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill(equipment_id)
        
        # -> Fill 'Nama Pelengkap' with a test name.
        # equipment_name text field
        elem = page.locator('[id="id_equipment_name"]')
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill(equipment_name)
        
        # -> Select 'Kemasan Dan Souvenir' from the Tipe Pelengkap dropdown.
        # tipe select
        elem = page.locator('[id="id_tipe"]')
        await elem.wait_for(state="visible", timeout=10000)
        await elem.select_option(label="Kemasan Dan Souvenir")
        
        # -> Click 'Simpan' to save the new equipment.
        # Simpan button
        elem = page.get_by_role('button', name='Simpan', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify the new equipment appears in the list with the correct tipe
        # Assert: New equipment code is present in the list.
        await expect(page.locator(f"text={equipment_id}").first).to_be_visible(timeout=15000), f"New equipment code '{equipment_id}' is present in the list."
        # Assert: New equipment name is present in the list.
        await expect(page.locator(f"text={equipment_name}").first).to_be_visible(timeout=15000), f"New equipment name '{equipment_name}' is present in the list."
        # Assert: Tipe 'Kemasan Dan Souvenir' is displayed for the new equipment in the list.
        await expect(page.locator("text=Kemasan Dan Souvenir").first).to_be_visible(timeout=15000), "Tipe 'Kemasan Dan Souvenir' is displayed for the new equipment in the list."
        
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
