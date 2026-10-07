"""Browser check for the security example: run `solara run example/security_app.py`, then this script."""

import typer
from playwright.sync_api import expect, sync_playwright


def main(url: str = "http://localhost:8765", screenshot: str = "solara-html-security.png"):
    errors, warnings = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        page.on(
            "console",
            lambda message: warnings.append(message.text)
            if message.type == "warning" and message.text.startswith("solara-html:")
            else None,
        )
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url)
        expect(page.locator(".fine")).to_be_visible()

        # Attributes that can run code are removed, however the template set them.
        for name in ("static-js", "bound-js"):
            assert page.locator(f".{name}").get_attribute("href") is None, name
        for name in ("static-on", "dynamic-on"):
            assert page.locator(f".{name}").get_attribute("onclick") is None, name
        assert page.locator(".srcdoc").get_attribute("srcdoc") is None
        # A safe link stays.
        assert page.locator(".fine").get_attribute("href") == "https://example.com/"

        # v-safe-html keeps formatting and drops scripts, handlers, frames and unsafe URLs.
        safe = page.locator(".safe")
        expect(safe.locator("b.x")).to_have_text("bold")
        assert safe.locator("script, iframe").count() == 0
        assert safe.locator("img").get_attribute("onerror") is None
        assert safe.locator("img").get_attribute("src") is None
        links = safe.locator("a")
        expect(links).to_have_count(2)
        assert links.nth(0).get_attribute("href") is None
        assert links.nth(1).get_attribute("href") == "https://example.com/"
        assert links.nth(1).get_attribute("rel") == "noopener noreferrer"

        # Clicking everything does not run any code.
        for name in ("static-js", "bound-js", "static-on", "dynamic-on"):
            page.locator(f".{name}").click()
        safe.locator("a").first.click()
        assert page.evaluate("window.pwned") is None

        page.screenshot(path=screenshot, full_page=True)
        browser.close()
    if errors:
        raise AssertionError("browser console errors:\n" + "\n".join(errors))
    if not any("removed" in warning for warning in warnings):
        raise AssertionError("the guard did not report what it removed")
    print("all checks passed")


if __name__ == "__main__":
    typer.run(main)
