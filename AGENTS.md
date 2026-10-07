# AGENTS.md

Guidance for AI coding agents working in this repository.

## What this is

`solara-html` is a small standalone package that adds single-file HTML components to [Solara](https://github.com/widgetti/solara):
`@solara_html.component_html("file.html")`. One `.html` file holds a Vue 3 `<template>`, optional scoped `<style>` and an optional `<script type="module">`
that exports a Vue options object named `component`. Vue 3 is the only engine. It runs on stock Solara (>= 1.64.0) through ipyreact ES modules. It is not a fork of Solara.

## Ground rules

- **Never edit Solara or ipyreact.** If something needs a change there, work around it in this package, or write down the request for the maintainers (widgetti/solara). Do not vendor or monkey-patch Solara internals.
- Use only public Solara API. Two core hooks are used: `solara.server.reload.watch_file` (hot reload) and `solara.server.settings.main.mode` (development mode loads the Vue build that warns). Do not add a third without a reason.
- User JavaScript is never an ipyreact module: ipyreact stops every widget on the page if one module fails. Python sends the script and its imports as text and `runtime.js` loads them, so an error stays in its component. Keep it that way.
- No frontend build step. `solara_html/runtime.js` is plain ES module JavaScript, shipped as is. Vue is a vendored copy of the official browser build (`solara_html/vendor`, see its README for how to update it).
- Python talks to the template like Solara talks to widgets: props are assigned, events are called as methods. Do not add `$emit` to Python.
- Security matters in the runtime: keep the DOM guard (`on*`, `srcdoc`, URL schemes), the `v-safe-html` sanitizer and its allowlists, and the refusal of `v-html` and `innerHTML` bindings in `component.py`. A change there needs a test in `example/check_security.py` or `tests/` and a README entry.
- The license is MIT. Keep the credit to Maarten A. Breddels (the package started from widgetti/solara#1233) in `LICENSE` and the README.

## Layout

- `solara_html/component.py` - the `component_html` decorator, builds an ipyreact widget class from the function signature.
- `solara_html/parse.py` - splits the `.html` file into template, style and script (stdlib `html.parser`).
- `solara_html/imports.py` - collects the script and the files it imports (relative `import`s rewritten to module ids) as data for the runtime, and inlines relative CSS `@import`s.
- `solara_html/runtime.js` - the browser runtime: shadow root, the Vue app (props as reactive state, events as methods), the DOM guard, `v-safe-html`.
- `solara_html/vendor/` - the Vue 3 browser builds with the template compiler (production, and development with warnings; chosen by the Solara mode), and the license.
- `docs/index.html` - the docs page that GitHub Pages serves (the `deploy-docs` job of `.github/workflows/test.yaml`, after all checks pass; it installs nothing). Plain HTML, no build step. Every `data-file` code block is an example that `tests/test_docs.py` loads and `tests/browser/check_docs.py` runs; every `data-sync` text is compared with the code (versions, reserved names, guard lists). The pictures in `docs/img/` are made by `check_docs.py --screenshots` in the browser job of CI and passed to the deploy job as an artifact (`*.png` is not committed). Change the page and the code together; keep it short and factual.
- `docs/authoring.md` - the guide for writing components (for people and agents that use the package). Keep it in step with the README. The wheel includes it as `solara_html/authoring.md`.
- `tests/` - unit tests (no browser). `tests/browser/` holds the app that is broken on purpose (one component per kind of error) and its Playwright check; it is not an example.
- `example/` - example apps, each with a Playwright check (`check*.py`). Add a check for each new feature.
- `scripts/run_browser_checks.sh` - runs all browser checks; CI uses it.

## Commands

```bash
uv venv --python 3.12 && uv pip install -e ".[dev]"
uv run playwright install chromium      # once, for the browser checks

uv run pytest                           # unit tests
uv run ruff check . && uv run mypy      # lint and types; CI runs both
source .venv/bin/activate && scripts/run_browser_checks.sh   # all browser checks (the script needs `python` and `solara` on PATH)
uv run solara run example/greeting_app.py    # try the examples by hand (development mode; add --production for the other Vue build)
```

Run the unit tests, ruff, mypy and the browser checks before you call a change done. A change to `runtime.js` is only covered by the browser checks.
Do not claim something works in a browser unless you ran the check.

## Conventions

- Conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `ci:`, `refactor:`.
- Default branch is `master`. Prefer small commits; squash fixups before pushing.
- Type hints on Python code, in the Python 3.12 style (`list[str]`, `str | None`). The package needs Python >= 3.12 and does not support older versions.
- Comments say why, not what. Keep the README the source of truth for the user-facing API and its limits; update it with the code.
- Do not commit screenshots (`*.png`), logs, or `.venv/`.
