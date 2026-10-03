"""Browser check for the todo example: run `solara run example/todo_app.py`, then this script."""

import typer
from playwright.sync_api import expect, sync_playwright


def main(url: str = "http://localhost:8765", screenshot: str = "solara-html-todo.png"):
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
        expect(page.locator("h2")).to_have_text("2 of 2 left")

        # An assignment (`this.items = [...]`) reaches Python.
        page.locator("input.new").fill("Test it")
        page.get_by_role("button", name="Add").click()
        expect(python_sees).to_contain_text("{'text': 'Test it', 'done': False}")
        expect(page.locator("h2")).to_have_text("3 of 3 left")

        # A change deep inside one item (`v-model` on `item.done`) reaches Python.
        page.get_by_role("checkbox", name="Ship it").check()
        expect(python_sees).to_contain_text("{'text': 'Ship it', 'done': True}")
        expect(page.locator("h2")).to_have_text("2 of 3 left")

        # An in-place `splice` reaches Python.
        page.get_by_role("button", name="Remove Write the docs").click()
        expect(python_sees).not_to_contain_text("Write the docs")
        expect(page.locator("h2")).to_have_text("1 of 2 left")

        # An assignment from a template expression.
        page.get_by_role("button", name="Clear finished").click()
        expect(python_sees).not_to_contain_text("Ship it")
        expect(page.locator("li")).to_have_count(1)
        expect(python_sees).to_have_text("Python sees: [{'text': 'Test it', 'done': False}]")

        page.screenshot(path=screenshot, full_page=True)
        browser.close()
    if errors:
        raise AssertionError("browser console errors or warnings:\n" + "\n".join(errors))
    print("all checks passed")


if __name__ == "__main__":
    typer.run(main)
