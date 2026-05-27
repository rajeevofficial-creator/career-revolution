"""Dump LinkedIn login page structure to find correct selectors."""
import asyncio

async def main():
    from playwright.async_api import async_playwright

    STEALTH_ARGS = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--lang=en-US,en",
    ]
    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=STEALTH_ARGS)
        ctx = await browser.new_context(user_agent=UA, viewport={"width":1280,"height":900},
                                         locale="en-US", timezone_id="Europe/Zurich")
        await ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
        page = await ctx.new_page()

        print("Loading login page...")
        await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(3)

        print(f"URL: {page.url}")
        print(f"Title: {await page.title()}")

        # Find all input elements
        inputs = await page.query_selector_all("input")
        print(f"\nFound {len(inputs)} input elements:")
        for inp in inputs:
            name = await inp.get_attribute("name") or ""
            id_ = await inp.get_attribute("id") or ""
            type_ = await inp.get_attribute("type") or ""
            placeholder = await inp.get_attribute("placeholder") or ""
            visible = await inp.is_visible()
            print(f"  name={name!r:30} id={id_!r:30} type={type_!r:12} visible={visible} placeholder={placeholder!r}")

        # Find all buttons
        buttons = await page.query_selector_all("button")
        print(f"\nFound {len(buttons)} buttons:")
        for btn in buttons:
            type_ = await btn.get_attribute("type") or ""
            text = (await btn.inner_text()).strip()[:50]
            visible = await btn.is_visible()
            print(f"  type={type_!r:10} visible={visible} text={text!r}")

        # Screenshot for visual inspection
        await page.screenshot(path="li_login_page.png", full_page=True)
        print("\nScreenshot saved: li_login_page.png")

        await browser.close()

asyncio.run(main())
