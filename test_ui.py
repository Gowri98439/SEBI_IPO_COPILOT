import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        errors = []
        page.on("pageerror", lambda err: errors.append(f"Page Error: {err}"))
        page.on("console", lambda msg: errors.append(f"Console {msg.type}: {msg.text}") if msg.type in ["error", "warning"] else None)

        print("1. Testing Login...")
        await page.goto("http://localhost:3000/login")
        await page.fill('input[type="email"]', "demo@ipocolpilot.ai")
        await page.fill('input[type="password"]', "Demo@1234")
        await page.click('button[type="submit"]')
        
        await page.wait_for_timeout(3000)
        
        print("Finding workspace links...")
        locators = await page.locator("a").all()
        workspace_url = None
        for loc in locators:
            href = await loc.get_attribute("href")
            if href and "/app/workspace/" in href:
                workspace_url = "http://localhost:3000" + href
                break
                
        if workspace_url:
            print(f"Going to workspace: {workspace_url}")
            await page.goto(workspace_url)
            await page.wait_for_timeout(3000)
            
            print("Going to compliance page")
            await page.goto(workspace_url.replace("/workspace/", "/compliance/"))
            await page.wait_for_timeout(3000)

            print("Going to copilot page")
            await page.goto(workspace_url.replace("/workspace/", "/copilot/"))
            await page.wait_for_timeout(3000)
            
            print("Going to export page")
            await page.goto(workspace_url.replace("/workspace/", "/export/"))
            await page.wait_for_timeout(3000)
            
        else:
            print("No workspace found, or on onboarding.")
            print("Current URL:", page.url)

        print("Errors so far:")
        for e in errors:
            print("  ", e)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
