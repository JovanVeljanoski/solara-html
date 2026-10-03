"""Browser check for the errors example: run `solara run example/errors_app.py`, then this script.

Every broken component shows its own message and names the file. The components next to them keep working.
"""

import re

import typer
from playwright.sync_api import expect, sync_playwright


def main(url: str = "http://localhost:8765", screenshot: str = "solara-html-errors.png"):
    warnings = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        failures = []
        page.on("console", lambda message: warnings.append(message.text) if message.type == "warning" else None)
        page.on("pageerror", lambda error: failures.append(str(error)))
        page.goto(url)

        # A working component with a script that imports "react" shows that scripts load.
        expect(page.locator(".react")).to_have_text(re.compile(r"^React \d+$"))
        # The component next to them works.
        page.locator(".card input").fill("Ada")
        expect(page.locator(".card h2")).to_contain_text("Ada")

        def message(text: str):
            return page.locator("pre", has_text=text)

        # Template errors.
        expect(message("error in the template or script")).to_contain_text("reading 'here'")
        expect(message("cannot mount the component")).to_contain_text('"name" is a Python prop')
        # Script errors: each says which file failed.
        expect(message("errors_syntax.html (script)")).to_contain_text("SyntaxError")
        expect(message("errors_lib.js")).to_contain_text("SyntaxError")
        expect(message("errors_export.html (script)")).to_contain_text("does not provide an export named 'nope'")
        expect(message("errors_export.html (script)")).to_contain_text("format.js")  # not a blob: URL
        expect(message("errors_throw.html (script)")).to_contain_text("boom")
        # A broken component shows no template.
        for name in ("syntax", "import", "export", "throw"):
            expect(page.locator(f".{name}")).to_have_count(0)
        # A script without a `component` export still shows its template, and warns.
        expect(page.locator(".nocomponent")).to_be_visible()
        assert any('errors_nocomponent.html (script) does not export "component"' in text for text in warnings), warnings

        # A component that is added and removed again quickly, while its script loads, leaves nothing behind.
        toggle = page.locator(".toggle")
        for _ in range(8):
            toggle.click()
        expect(page.locator(".react")).to_have_text(re.compile(r"^React \d+$"))  # an even number of clicks: shown again
        toggle.click()
        expect(page.locator(".react")).to_have_count(0)
        toggle.click()
        expect(page.locator(".react")).to_have_text(re.compile(r"^React \d+$"))
        assert not failures, failures
        page.screenshot(path=screenshot, full_page=True)
        browser.close()
    print("all checks passed")


if __name__ == "__main__":
    typer.run(main)
