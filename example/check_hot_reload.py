"""Browser check for hot reload in development mode (needs Solara >= 1.64).

It copies the greeting example to a temporary directory, starts `solara run` there without `--production`,
edits greeting.html and then format.js (a relative import), and expects the open page to show each edit.
Run it with `python example/check_hot_reload.py`.
"""

import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import typer
from playwright.sync_api import expect, sync_playwright

EXAMPLE = Path(__file__).parent


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


def main():
    with tempfile.TemporaryDirectory() as tmp:
        app_dir = Path(tmp)
        for name in ["greeting_app.py", "greeting.html", "format.js"]:
            shutil.copy(EXAMPLE / name, app_dir / name)
        port = free_port()
        url = f"http://localhost:{port}"
        server = subprocess.Popen(
            [sys.executable, "-m", "solara", "run", str(app_dir / "greeting_app.py"), "--port", str(port), "--no-open"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        errors = []
        try:
            wait_for_server(url, server)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page()
                page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(url)
                heading = page.locator(".card h2")
                count = page.locator(".card .count")
                expect(heading).to_have_text("Hello, World")
                expect(count).to_have_text("5 characters")

                html = app_dir / "greeting.html"
                html.write_text(html.read_text().replace("Hello, ", "Howdy, "))
                expect(heading).to_have_text("Howdy, World", timeout=15_000)

                js = app_dir / "format.js"
                # Only the displayed text: the function name `characters` is imported by greeting.html.
                js.write_text(js.read_text().replace("} characters", "} letters"))
                expect(count).to_have_text("5 letters", timeout=15_000)

                browser.close()
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
        if errors:
            raise AssertionError("browser console errors:\n" + "\n".join(errors))
    print("all checks passed")


if __name__ == "__main__":
    typer.run(main)
