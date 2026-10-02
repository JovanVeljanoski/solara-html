"""Browser check for the example app: run `solara run example/greeting_app.py`, then this script."""

import typer
from playwright.sync_api import expect, sync_playwright


def main(url: str = "http://localhost:8765", screenshot: str = "solara-html-demo.png"):
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url)

        # Playwright CSS locators pierce open shadow roots.
        name_input = page.locator(".card input")
        python_sees = page.locator("text=Python sees")

        # data-solara-prop-disabled: Reset is disabled while the name is the default.
        reset_button = page.locator(".card button", has_text="Reset")
        expect(reset_button).to_be_disabled()

        name_input.fill("Ada")
        expect(reset_button).to_be_enabled()
        expect(python_sees).to_have_text("Python sees: Ada")
        expect(page.locator(".card h2")).to_have_text("Hello, Ada")
        expect(page.locator(".card .count")).to_have_text("3 characters")
        # The label comes from format.js, a relative import of greeting.html.
        name_input.fill("A")
        expect(page.locator(".card .count")).to_have_text("1 character")

        reset_button.click()
        expect(python_sees).to_have_text("Python sees: World")
        expect(reset_button).to_be_disabled()

        page.get_by_role("button", name="Shout").click()
        expect(python_sees).to_have_text("Python sees: WORLD")

        # Typing in the middle survives the round trip through Python.
        name_input.fill("World")
        name_input.press("Home")
        name_input.press_sequentially("Hi ")
        expect(python_sees).to_have_text("Python sees: Hi World")

        name_input.fill("Grace")
        name_input.press("Escape")
        expect(python_sees).to_have_text("Python sees: World")

        # Page CSS must not reach into the component.
        page.add_style_tag(content="h2 { color: rgb(255, 0, 0) !important; }")
        expect(page.locator(".card h2")).not_to_have_css("color", "rgb(255, 0, 0)")

        page.screenshot(path=screenshot, full_page=True)
        browser.close()
    if errors:
        raise AssertionError("browser console errors:\n" + "\n".join(errors))
    print("all checks passed")


if __name__ == "__main__":
    typer.run(main)
