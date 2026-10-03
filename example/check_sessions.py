"""Browser check for sessions: run `solara run example/greeting_app.py`, then this script.

Several browsers on one server each get their own state, and a reload starts over.
"""

import typer
from playwright.sync_api import expect, sync_playwright


def main(url: str = "http://localhost:8765", screenshot: str = "solara-html-sessions.png"):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        pages = [browser.new_context().new_page() for _ in range(3)]
        for page in pages:
            page.goto(url)
            expect(page.locator(".card h2")).to_have_text("Hello, World")
        for number, page in enumerate(pages):
            page.locator(".card input").fill(f"User{number}")
        for number, page in enumerate(pages):
            expect(page.locator(".card h2")).to_have_text(f"Hello, User{number}")

        pages[0].reload()
        expect(pages[0].locator(".card h2")).to_have_text("Hello, World")
        pages[0].locator(".card input").fill("Again")
        expect(pages[0].locator(".card h2")).to_have_text("Hello, Again")
        expect(pages[1].locator(".card h2")).to_have_text("Hello, User1")
        pages[0].screenshot(path=screenshot)
        browser.close()
    print("all checks passed")


if __name__ == "__main__":
    typer.run(main)
