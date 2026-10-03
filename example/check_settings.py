"""Browser check for the settings example: run `solara run example/settings_app.py`, then this script."""

import typer
from playwright.sync_api import expect, sync_playwright


def main(url: str = "http://localhost:8765", screenshot: str = "solara-html-settings.png"):
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        # Solara itself logs Vue warnings in development mode; only errors and our own warnings count.
        page.on(
            "console",
            lambda message: errors.append(message.text)
            if message.type == "error" or (message.type == "warning" and message.text.startswith("solara-html:"))
            else None,
        )
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url)
        python_sees = page.locator(".python-sees")

        # Props, a v-if / v-else-if chain, and values computed from props.
        expect(page.locator(".user")).to_have_text("Ada")
        expect(page.locator(".plan")).to_have_text("Free")
        expect(page.locator(".plan-text")).to_have_text("Pro unlocks unlimited sessions.")
        expect(page.locator("select.level")).to_have_value("A2")  # the shown level is gated by the plan
        expect(page.locator("select.level")).to_be_disabled()
        expect(page.locator("input.audio")).to_be_disabled()
        # A stylesheet shared with `@import "./buttons.css"`.
        expect(page.get_by_role("button", name="Upgrade to Pro")).to_have_css("background-color", "rgb(35, 90, 151)")

        # An event reaches Python, and the props it changes come back.
        page.get_by_role("button", name="Upgrade to Pro").click()
        expect(page.locator(".plan")).to_have_text("Pro")
        expect(page.locator("select.level")).to_have_value("B1")
        expect(page.locator("select.level")).to_be_enabled()
        expect(page.get_by_role("button", name="Manage plan")).to_be_visible()

        # select and checkbox models write to Python.
        page.locator("select.level").select_option("C1")
        expect(python_sees).to_contain_text("level=C1")
        page.locator("input.audio").check()
        expect(python_sees).to_contain_text("audio=True")
        page.locator("input.audio").uncheck()
        expect(python_sees).to_contain_text("audio=False")

        # A number input that validates on change, and puts the old value back when the new one is wrong.
        number = page.locator("input.num")
        number.fill("7")
        number.press("Enter")
        expect(python_sees).to_contain_text("num=7")
        number.fill("99")
        number.press("Enter")
        expect(page.locator(".error")).to_have_text("Must be an integer from 3 to 50")
        expect(number).to_have_value("7")

        # Fast typing into a prop whose server echo is slow: no character is lost.
        nickname = page.locator("input.nick")
        nickname.click()
        nickname.press_sequentially("abcdefghij", delay=40)
        page.wait_for_timeout(4500)
        expect(nickname).to_have_value("abcdefghij")
        expect(python_sees).to_contain_text("nick='abcdefghij'")

        # A modal dialog: Escape closes it, and the state follows, so it opens again.
        page.get_by_role("button", name="Delete account").first.click()
        expect(page.locator("dialog")).to_have_attribute("open", "")
        page.keyboard.press("Escape")
        expect(page.locator("dialog")).not_to_have_attribute("open", "")
        page.get_by_role("button", name="Delete account").first.click()
        expect(page.locator("dialog")).to_have_attribute("open", "")
        page.locator("dialog .confirm").click()
        expect(python_sees).to_contain_text("events=['subscribe', 'delete']")

        page.screenshot(path=screenshot, full_page=True)
        browser.close()
    if errors:
        raise AssertionError("browser console errors or warnings:\n" + "\n".join(errors))
    print("all checks passed")


if __name__ == "__main__":
    typer.run(main)
