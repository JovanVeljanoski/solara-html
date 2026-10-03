# AGENTS.md

Guidance for AI coding agents working in this repository. Read [HANDOVER.md](HANDOVER.md) first for the current state and open tasks.

## What this is

`solara-html` is a small standalone package that adds single-file HTML components to [Solara](https://github.com/widgetti/solara):
`@solara_html.component_html("file.html")`. One `.html` file holds a `<template>`, optional scoped `<style>` and an optional `<script type="module">`.
It runs on stock Solara (>= 1.64.0) through ipyreact ES modules. It is not a fork of Solara.

## Ground rules

- **Never edit Solara or ipyreact.** If something needs a change there, work around it in this package, or write down the request for the maintainers (widgetti/solara). Do not vendor or monkey-patch Solara internals.
- Use only public Solara API. The one core hook we rely on is `solara.server.reload.watch_file`.
- No frontend build step. `solara_html/runtime.js` is plain ES module JavaScript, shipped as is.
- Security matters in the runtime: keep the attribute and property allowlists, the URL scheme checks, and the refusal of `on*` and `srcdoc` bindings. A new binding needs a test and a README entry.
- The license is MIT. Keep the credit to Maarten A. Breddels (the package started from widgetti/solara#1233) in `LICENSE` and the README.

## Layout

- `solara_html/component.py` - the `component_html` decorator, builds an ipyreact widget class from the function signature.
- `solara_html/parse.py` - splits the `.html` file into template, style and script (stdlib `html.parser`).
- `solara_html/imports.py` - rewrites relative `import` statements in the script so each imported file becomes its own ES module.
- `solara_html/runtime.js` - the browser runtime: shadow root, `data-solara-*` bindings, `mount({root, get, set, subscribe, emit})`.
- `tests/` - unit tests (no browser).
- `example/` - example apps, each with a Playwright check (`check*.py`).
- `scripts/run_browser_checks.sh` - runs all browser checks; CI uses it.

## Commands

```bash
uv venv --python 3.11 && uv pip install -e ".[dev]"
uv run playwright install chromium      # once, for the browser checks

uv run pytest                           # unit tests
source .venv/bin/activate && scripts/run_browser_checks.sh   # all browser checks (the script needs `python` and `solara` on PATH)
uv run solara run example/greeting_app.py    # try the examples by hand
```

Run both the unit tests and the browser checks before you call a change done. A change to `runtime.js` is only covered by the browser checks.
Do not claim something works in a browser unless you ran the check.

## Conventions

- Conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `ci:`, `refactor:`.
- Default branch is `master`. Prefer small commits; squash fixups before pushing.
- Type hints on Python code. Keep `from __future__ import annotations`; the package supports Python >= 3.8.
- Comments say why, not what. Keep the README the source of truth for the user-facing API and its limits; update it with the code.
- Do not commit screenshots (`*.png`), logs, or `.venv/`.
