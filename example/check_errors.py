"""Browser check for the errors example: run `solara run example/errors_app.py`, then this script."""

import typer
from playwright.sync_api import expect, sync_playwright


def main(url: str = "http://localhost:8765", screenshot: str = "solara-html-errors.png"):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(url)

        # An error while rendering, and an error while mounting, show in the component itself.
        expect(page.locator("pre", has_text="error in the template or script")).to_contain_text("reading 'here'")
        expect(page.locator("pre", has_text="cannot mount the component")).to_contain_text('"name" is a Python prop')

        # The component next to them still works.
        page.locator(".card input").fill("Ada")
        expect(page.locator(".card h2")).to_contain_text("Ada")

        page.screenshot(path=screenshot, full_page=True)
        browser.close()
    print("all checks passed")


if __name__ == "__main__":
    typer.run(main)
