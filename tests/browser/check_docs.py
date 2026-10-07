"""Browser check for the code in docs/index.html.

It writes every example of the page to a temporary folder, runs each as a Solara app (development mode, so Vue warns about
template mistakes) and does what the page says the example does. Run it with `python tests/browser/check_docs.py`.

With `--screenshots docs/img` it also saves the result of each example as `<example>.png`, for the docs page.
The browser job of CI does that and hands the images to the job that publishes the page, so they are never committed.
"""

import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from collections.abc import Callable
from html.parser import HTMLParser
from pathlib import Path

import typer
from playwright.sync_api import Page, expect, sync_playwright

PAGE = Path(__file__).parent.parent.parent / "docs" / "index.html"


class _Examples(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.files: dict[str, str] = {}
        self._name: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = dict(attrs).get("data-file")
        if name:
            self._name, self._text = name, []

    def handle_data(self, data: str) -> None:
        if self._name:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._name and tag == "code":
            self.files[self._name] = "".join(self._text)
            self._name = None


def hello(page: Page) -> None:
    expect(page.get_by_text("Hello, World!")).to_be_visible()
    expect(page.get_by_role("button", name="Reset")).to_be_disabled()
    page.get_by_label("Name").fill("Ada")
    expect(page.get_by_text("Hello, Ada!")).to_be_visible()
    expect(page.get_by_text("Python sees: Ada")).to_be_visible()
    page.get_by_role("button", name="Reset").click()
    expect(page.get_by_text("Python sees: World")).to_be_visible()
    expect(page.get_by_text("Hello, World!")).to_be_visible()
    # The picture on the page shows this state.
    page.get_by_label("Name").fill("Ada")
    expect(page.get_by_text("Python sees: Ada")).to_be_visible()


def tasks(page: Page) -> None:
    for text in ("Write docs", "Ship it"):
        page.get_by_placeholder("New task").fill(text)
        page.get_by_role("button", name="Add").click()
    expect(page.get_by_role("listitem")).to_have_count(2)
    expect(page.get_by_text("Python sees: [{'text': 'Write docs', 'done': False}, {'text': 'Ship it', 'done': False}]")).to_be_visible()
    page.get_by_role("checkbox").first.check()
    expect(page.get_by_text("Python sees: [{'text': 'Write docs', 'done': True}, {'text': 'Ship it', 'done': False}]")).to_be_visible()


def card(page: Page) -> None:
    expect(page.get_by_role("heading", name="Starter")).to_be_visible()
    expect(page.get_by_text("For a team.")).to_be_visible()
    page.get_by_role("button", name="Choose").nth(1).click()
    expect(page.get_by_text("Chosen: Pro")).to_be_visible()


CHECKS: dict[str, Callable[[Page], None]] = {"hello": hello, "tasks": tasks, "card": card}


def snapshot(page: Page, path: Path) -> None:
    """A picture of what the example shows: the page content, without the empty page around it."""
    page.add_style_tag(content=".solara-autorouter-content > .v-sheet { padding: 12px; }")
    page.locator(".solara-autorouter-content > .v-sheet").screenshot(path=path)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_server(url: str, process: subprocess.Popen, timeout: float = 60) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError("solara run exited early")
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError(f"{url} did not start in {timeout} seconds")


def main(screenshots: str = typer.Option("", help="A folder for the picture of each example")) -> None:
    examples = _Examples()
    examples.feed(PAGE.read_text(encoding="utf-8"))
    folders = {name.split("/")[0] for name in examples.files}
    assert folders == set(CHECKS), f"the page has the examples {sorted(folders)}, this check covers {sorted(CHECKS)}"

    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for name, text in examples.files.items():
            target = Path(tmp) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        for folder, check in CHECKS.items():
            port = free_port()
            url = f"http://localhost:{port}"
            server = subprocess.Popen(
                [sys.executable, "-m", "solara", "run", str(Path(tmp) / folder / "app.py"), "--port", str(port), "--no-open"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            problems: list[str] = []
            try:
                wait_for_server(url, server)
                page = browser.new_page(viewport={"width": 520, "height": 500}, device_scale_factor=2)
                # Solara itself logs Vue warnings in development mode; only errors and our own warnings count.
                page.on("console", lambda m: problems.append(m.text) if m.type == "error" or "solara-html" in m.text else None)
                page.on("pageerror", lambda error: problems.append(str(error)))
                page.goto(url)
                check(page)
                if screenshots:
                    Path(screenshots).mkdir(parents=True, exist_ok=True)
                    snapshot(page, Path(screenshots) / f"{folder}.png")
                assert not problems, f"{folder}: browser console problems:\n" + "\n".join(problems)
                page.close()
            finally:
                server.terminate()
                server.wait(timeout=10)
            print(f"docs example '{folder}' ok")
        browser.close()
    print("all checks passed")


if __name__ == "__main__":
    typer.run(main)
