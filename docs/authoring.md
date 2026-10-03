# Writing a solara-html component

A guide for people and for LLM agents that write components. The [README](../README.md) is the reference.
This page is the short version: the contract, the rules, the traps, and a recipe for each common case.
The files in [example/](../example) are tested, so copy from them.

## The shape of every component

Two files: the Python signature, and the HTML file.

```python
# page.py
import solara
import solara_html

@solara_html.component_html("counter.html")          # path is relative to this .py file
def Counter(count: int = 0, on_count=None, step: int = 1, event_saved=None, children=[]):
    pass                                              # the body is never used

count = solara.reactive(0)

@solara.component
def Page():
    Counter(count=count.value, on_count=count.set, event_saved=lambda data: print("saved", data))
```

```html
<!-- counter.html -->
<template>
  <button @click="count = count + step">{{ count }}</button>
  <button @click="saved(count)">Save</button>
  <slot></slot>
</template>

<style>
  button { padding: 0.5rem 1rem; }
</style>

<script type="module">
  export const component = {
    // Vue options API. Python props and events are available as `this.count`, `this.saved(...)`.
    computed: { double() { return this.count * 2; } },
  };
</script>
```

## The contract (the only part that is specific to solara-html)

| Python signature | In the template and script |
| --- | --- |
| `name: str = "x"` | `name` (read it, assign it, `v-model="name"`). Syncs both ways. |
| `on_name=callback` | Nothing in the template. Python calls `callback(new_value)` when the browser changes `name`. |
| `event_save=callback` | `save(data)` (or `this.save(data)`). Python gets `callback(data)`; `data` is `None` if you pass nothing. |
| `children=[widgets]` | The widgets show where `<slot></slot>` is. |

How to remember it: **Python props are assigned, events are called.** Like Solara itself. Never `$emit` to Python.

## Rules

Do:

- Keep one component per file.
- Give every prop a default value and a type hint in the signature.
- Give `on_<prop>` for every prop the browser can change, and make Python store it (`on_count=count.set`).
- Use the Vue **options API** in `export const component = {...}`: `data`, `computed`, `watch`, `methods`, `mounted`, `beforeUnmount`, `components`.
- Put logic in the script, not in long template expressions.
- Use CSS variables (`var(--x)`) for anything that must follow the page theme. Put spacing on an element inside the template, not on `:host`.
- Clean up in `beforeUnmount`: timers, and listeners added to `document` or `window`.
- Change a list or dict prop by assigning a new value (`this.items = [...this.items, x]`). An in-place change (`this.items.push(x)`, `item.done = true`) is also sent to Python, but an assignment is the clearer form.
- Keep data that crosses the line to JSON types: `str`, `int`, `float`, `bool`, `None`, `list`, `dict`. Convert dates and arrays in Python first.
  A whole number that the browser writes to a `float` prop reaches Python as an `int`.
- Treat a call to an event as asynchronous. The new props come back from Python a moment later.

Do not:

- Do not use `v-html` or bind `innerHTML`. Use `v-safe-html="text"` for markup that comes from Python or users.
- Do not use `onclick="..."` or other `on*` attributes, `srcdoc`, `javascript:` or `data:` URLs. They are removed. Use `@click`.
- Do not use named slots, `<script setup>` or `setup()`. The first two cannot work, and `setup()` is not tested.
- Do not give a `computed` or `methods` entry the same name as a prop or event. The component then shows an error.
- Do not `@import` a remote URL or an absolute path in `<style>`. Use `<link rel="stylesheet" href="...">` in the template. Only `@import "./file.css"` works.
- Do not use Vuetify or Solara components or classes in the template. Write plain HTML.
- Do not rely on page CSS classes (Vuetify, Solara). The component has its own shadow root.
- Do not name an argument like an `ipyreact.Widget` attribute (`layout`, `open`, `props`, `events`, ...), or start it with `_`. The decorator raises `ValueError`.
- Do not use `window` or `document` inside `{{ }}` or directive expressions. Vue does not allow them there; call a method.

## Recipes

| You need | Look at |
| --- | --- |
| Text input, computed value, one event, a relative JS import | [greeting.html](../example/greeting.html), `format.js` |
| `select`, checkbox, number input with validation, `v-if` / `v-else-if`, a modal `<dialog>`, a slow server | [settings.html](../example/settings.html) |
| A list of dicts that the browser edits | [todo.html](../example/todo.html) |
| A child component with its own file (`$emit` / `v-model` between Vue components) | [quiz.html](../example/quiz.html), [topic_picker.js](../example/topic_picker.js) |
| An event that carries data, a keyboard shortcut, timers, `ref` and `$nextTick`, state that changes later | [quiz.html](../example/quiz.html) |
| Several instances on one page, watchers, Solara widgets in the slot | [beacon.html](../example/beacon.html) |
| Shared CSS between components | `@import "./buttons.css";` in `<style>` ([buttons.css](../example/buttons.css)) |
| Markup from Python or users | `v-safe-html`, see [security.html](../example/security.html) |

### A watcher that sends a value to Python

```js
watch: { draft(value) { this.query = value; } }     // `query` is a prop: the assignment calls on_query
```

### Python tells the browser to do something

Python cannot call a method in the browser. Send a value and react to it. A counter works for "do it again":

```python
@solara_html.component_html("field.html")
def Field(text: str = "", on_text=None, focus_count: int = 0):   # Python: focus_count=n + 1 to focus
    pass
```
```js
watch: { focus_count() { this.$refs.input.focus(); } }
```

### Images, fonts and other files

Files in the `public` folder next to your app are served at `/static/public/...`. Use that absolute path in `src`, in `<link rel="stylesheet" href>` and in CSS `url(...)`.
A `data:` URL in `src` is removed by the guard.

### A modal dialog

A native `<dialog>` is opened by a method call, so use a watcher and handle the `close` event (Escape closes it):

```html
<dialog ref="dialog" @close="open = false">...</dialog>
```
```js
watch: { open(value) { const d = this.$refs.dialog; if (value && !d.open) d.showModal(); if (!value && d.open) d.close(); } }
```

### Typing that should reach Python only when it is finished

Use a local `data()` field for the draft, and assign the prop only on `@change`, `@blur` or Enter (see `beacon.html`).

## When something does not work

| You see | Cause |
| --- | --- |
| A part of the page is empty, or a value is missing | Run in development mode (`solara run app.py`, not `--production`) and read the browser console. Vue warns there, for example `Property "nme" was accessed during render but is not defined`. |
| A red message `some.js: SyntaxError: ...` (or `page.html (script): ...`) | A JavaScript error in that file: a syntax error, an import of a name the file does not export, or an error thrown while it runs. The message names the file. There is no line number for a syntax error, so open that file. |
| The template shows but the script seems not to run, and the console has `does not export "component"` | The script needs `export const component = {...}`. |
| A red message in place of the component | A template or script error. The message says what failed. The browser console has the stack. |
| `ValueError` when Python starts | The decorator refused something: a name clash, `v-html`, a missing `<template>`, a missing imported file, an import cycle. The message names the file. |
| A prop does not update in the browser | Python did not assign a new value. In Solara, `items.value.append(x)` does not notify; use `items.set([...items.value, x])`. |
| `ValueError: cannot import ...` from `<style>` | An `@import` that is not a relative file. See above. |
| A link, image, or iframe has no URL | The guard removed an unsafe URL. The browser console has a `solara-html:` warning that names it. |
| A child component renders as an unknown element | Register it in `components` (see `quiz.html`). Its tag can be kebab-case: `<topic-picker>`. |

In development mode (`solara run app.py`) a change to the HTML file, to a JavaScript file it imports, or to a CSS file it `@import`s reloads the app.

## Before you call it done

1. The signature has a default and a type hint for every prop.
2. Every `$emit` is between two Vue components, never to Python.
3. No `v-html`, no `on*` attributes.
4. Timers and `document` listeners are removed in `beforeUnmount`.
5. You ran the app and used every control once. Read the browser console: there must be no `solara-html:` warning or error.
6. For a change to this package: add or extend a check in `example/` and run `scripts/run_browser_checks.sh`.
