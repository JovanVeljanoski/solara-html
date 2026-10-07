"""Browser check for the beacon demo: run `solara run example/beacon_app.py`, then this script."""

import typer
from playwright.sync_api import expect, sync_playwright


def main(url: str = "http://localhost:8765", screenshot: str = "solara-html-beacon.png"):
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1300, "height": 1000})
        # Solara itself logs Vue warnings in development mode; only errors and our own warnings count.
        page.on(
            "console",
            lambda message: errors.append(message.text)
            if message.type == "error" or (message.type == "warning" and message.text.startswith("solara-html:"))
            else None,
        )
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url)

        # Two independent instances; Playwright CSS locators pierce open shadow roots.
        beacons = page.locator(".beacon")
        expect(beacons).to_have_count(2)
        first, second = beacons.nth(0), beacons.nth(1)
        python_sees = page.locator(".python-sees")

        # Debounced call sign: Enter commits it to Python.
        first.locator(".field input").fill("NOVA-1")
        first.locator(".field input").press("Enter")
        expect(python_sees.nth(0)).to_have_text("Python sees call sign: NOVA-1")
        expect(python_sees.nth(1)).to_have_text("Python sees call sign: EMBER-3")

        # An event from the native button reaches Python, and the count comes back as a prop.
        first.locator(".pulse-button").click()
        first.locator(".pulse-button").click()
        expect(first.locator(".counter strong")).to_have_text("2")
        expect(second.locator(".counter strong")).to_have_text("0")

        # A Vue button in the slot resets the Python state.
        page.get_by_role("button", name="Reset station").first.click()
        expect(first.locator(".counter strong")).to_have_text("0")
        expect(python_sees.nth(0)).to_have_text("Python sees call sign: AURORA-7")

        page.screenshot(path=screenshot, full_page=True)
        browser.close()
    if errors:
        raise AssertionError("browser console errors or warnings:\n" + "\n".join(errors))
    print("all checks passed")


if __name__ == "__main__":
    typer.run(main)
