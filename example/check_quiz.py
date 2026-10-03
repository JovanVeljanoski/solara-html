"""Browser check for the quiz example: run `solara run example/quiz_app.py`, then this script."""

import re

import typer
from playwright.sync_api import expect, sync_playwright


def main(url: str = "http://localhost:8765", screenshot: str = "solara-html-quiz.png"):
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

        # The start screen, a shared stylesheet, and a child component.
        expect(page.locator(".setup h1")).to_have_text("Quiz")
        expect(page.locator(".stats")).to_have_text("1 of 4 topics complete")
        start = page.get_by_role("button", name="Start quiz")
        expect(start).to_be_disabled()
        expect(page.get_by_role("button", name="Surprise me")).to_have_css("background-color", "rgb(227, 236, 246)")

        # The child component writes the model through $emit; Python gets the new value.
        page.get_by_placeholder("Choose topics").click()
        page.get_by_role("option", name="Food").click()
        expect(python_sees).to_contain_text("topic=['Food']")
        expect(start).to_be_enabled()
        # Clicking outside closes the list (the child listens on the document).
        page.locator(".setup h1").click()
        expect(page.get_by_role("listbox")).to_have_count(0)
        # Filtering, and removing a chip.
        page.locator(".combo-field input").fill("gre")
        expect(page.get_by_role("option")).to_have_count(1)
        page.get_by_role("option", name="Greetings").click()
        page.locator(".chip", has_text="Food").get_by_role("button").click()
        expect(python_sees).to_contain_text("topic=['Greetings']")
        page.locator(".setup h1").click()

        # An event with data: the topics go to Python as a list.
        start.click()
        expect(page.locator(".term")).to_have_text("hello")
        expect(python_sees).to_contain_text("('start', ['Greetings'])")

        # Typing, then Enter as a keyboard shortcut, send the answer.
        answer = page.get_by_placeholder("Type your answer")
        expect(answer).to_be_focused()
        answer.fill("hola")
        page.keyboard.press("Enter")
        expect(page.locator(".note")).to_contain_text("That works.")
        expect(python_sees).to_contain_text("('check', 'hola')")
        expect(answer).to_be_disabled()
        expect(page.locator("progress")).to_have_attribute("value", re.compile(r"^33\.3"))

        # Enter again goes to the next question. State written from timers (simulated dictation) works too.
        page.keyboard.press("Enter")
        expect(page.locator(".term")).to_have_text("goodbye")
        expect(answer).to_have_value("")
        page.locator(".dictate").click()
        expect(answer).to_have_value("hola")
        expect(page.locator(".dictate")).not_to_have_class("listening")

        # A modal dialog guards Cancel; Escape closes it, and Cancel quiz leaves the screen.
        page.get_by_role("button", name="Cancel quiz").click()
        expect(page.locator("dialog")).to_have_attribute("open", "")
        page.keyboard.press("Escape")
        expect(page.locator("dialog")).not_to_have_attribute("open", "")
        page.get_by_role("button", name="Cancel quiz").click()
        page.locator("dialog").get_by_role("button", name="Cancel quiz").click()
        expect(page.locator(".setup h1")).to_have_text("Quiz")
        expect(python_sees).to_contain_text("('cancel',)")

        # The document-level Enter shortcut also works on the start screen, because the topics are still chosen.
        page.keyboard.press("Enter")
        expect(page.locator(".term")).to_have_text("hello")

        page.screenshot(path=screenshot, full_page=True)
        browser.close()
    if errors:
        raise AssertionError("browser console errors or warnings:\n" + "\n".join(errors))
    print("all checks passed")


if __name__ == "__main__":
    typer.run(main)
