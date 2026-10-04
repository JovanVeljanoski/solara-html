# solara-html

Single-file HTML components for Solara, as a separate package.
One `.html` file holds a component's template, scoped CSS and browser JavaScript, and Solara connects it to Python state.
The template is [Vue 3](https://vuejs.org/) template syntax, so a page is plain HTML with `{{ }}`, `v-model`, `v-if`, `v-for` and `@click`.
It works with a stock Solara: no server routes, no template edits, no monkey patches, no fork.

It started as [widgetti/solara#1207](https://github.com/widgetti/solara/pull/1207) (a Solara core feature) and was reshaped
into a package by Maarten Breddels in [widgetti/solara#1233](https://github.com/widgetti/solara/pull/1233).
This repository continues that package. It is MIT licensed, like Solara.

It needs Python 3.9 or later and Solara 1.64.0 or later (which has the `solara.server.reload.watch_file` hook that makes hot reload work).
It also reads `solara.server.settings.main.mode`: in development mode it loads the Vue build that warns about template mistakes (see Errors).

## Install

Install from GitHub:

```bash
pip install git+https://github.com/JovanVeljanoski/solara-html.git
```

## Hello world

Two files in the same folder.

`hello.html`:

```html
<template>
  <label>Name <input v-model="name" /></label>
  <p>Hello, {{ name }}!</p>
  <button :disabled="name === 'World'" @click="reset()">Reset</button>
</template>
```

`hello_app.py`:

```python
import solara

import solara_html


@solara_html.component_html("hello.html")
def Hello(name="World", on_name=None, event_reset=None):
    pass


name = solara.reactive("World")


@solara.component
def Page():
    Hello(name=name.value, on_name=name.set, event_reset=lambda _data: name.set("World"))
    solara.Text(f"Python sees: {name.value}")
```

Run it:

```bash
solara run hello_app.py
```

Type in the input: the greeting changes in the browser, and Python gets the new value through `on_name`.
The button calls `event_reset` in Python.

## How Python and the template talk

The function signature is the contract, as in `solara.component_vue`. The function body is not used.

| In Python | In the template |
| --- | --- |
| A plain argument `name="World"` | A variable `name` (`{{ name }}`, `v-model="name"`, `:title="name"`). It syncs both ways. |
| `on_name=callback` | Called with the new value when the browser changes `name`. |
| `event_reset=callback` | A method `reset()`. It calls `callback(data)` in Python. |
| `children=[...]` | The Solara widgets that show at the template's `<slot>`. |

Like in Solara, you change a prop by **assigning** it, and you call an event as a **method**. You do not `$emit` to Python:

```html
<input v-model="name" />                    <!-- assigns the prop; on_name runs -->
<button @click="check(answer)">Check</button>  <!-- calls event_check(answer) in Python -->
```

- The data of an event must be JSON (numbers, text, lists, dicts, `null`). The callback gets `None` when there is no data.
- A bare `@click="reset"` is the same as `@click="reset($event)"`. Python cannot take a DOM event, so it receives `None`.
- A write to a prop shows at once in the browser, then goes to Python. A fast typist is not behind a slow server.
- A list or dict prop can be changed in place too (`this.items.push(x)`, or a checkbox bound to `item.done`): the change is sent to Python. An assignment (`this.items = [...this.items, x]`) is the clearer form. In Python, as in Solara, `items.value.append(x)` is not seen: set a new list.
- The names must not collide with names in the template's own script: a prop or event with the same name as a `computed` or `methods` entry raises an error in the browser.

`on_<x>` is a callback only when `<x>` is an argument too. Otherwise `on_<x>` is a prop like any other (so `on_air: bool` works).

Some argument names are reserved, and the decorator raises a `ValueError` for them:

- names on `ipyreact.Widget`: `keys`, `comm`, `open`, `close`, `layout`, `model_id`, `tooltip`, `tabbable`, `children`, `events`, `props` (and more in other ipywidgets versions), and names that start with `_`;
- two arguments that give the same React prop: ipyreact adds a `set<Name>` setter per prop, so `x` collides with `setX` and with `X`;
- a prop and an event with the same name, such as `click` and `event_click`.

`children=None` and `children=[]` both work.
Only the default slot exists, because the children are widgets: write `<slot></slot>` (the package keeps it as a real `<slot>` element, so Vue does not drop it).

Writing components with an LLM agent? Point it at [docs/authoring.md](docs/authoring.md): the contract, the rules, the traps and a recipe per case.
The guide is installed with the package, as `solara_html/authoring.md`.

## The three parts of the file

```html
<template> ... </template>                 <!-- required -->
<style> ... </style>                       <!-- optional, scoped to this component -->
<script type="module"> ... </script>       <!-- optional -->
```

### Template

Vue 3 template syntax. Everything in the Vue template guide works: `v-if` / `v-else-if` / `v-else`, `v-for`, `v-model` (text, checkbox, `select`, number),
`v-show`, `:class`, `:style`, `@event.modifiers`, refs, and `<component :is>`. The file is compiled in the browser (see Limits).

### Style

The CSS is applied inside a Shadow DOM, so it does not leak out, and the page's CSS does not leak in.
CSS variables and inherited properties (such as the font) still pass through.
Share a stylesheet between components with a relative `@import`:

```css
@import "./buttons.css";
```

The file is inlined in each component and watched for hot reload. `@import "./a.css"`, `@import url(./a.css)` and the quoted forms work.
Any other `@import` (a remote URL, an absolute path, a media query) raises a `ValueError`, because the browser would ignore it.
`url(...)` inside an imported file is not rewritten, so use absolute paths there.
For other stylesheets, add `<link rel="stylesheet" href="/static/public/shared.css" />` to the template. Solara serves the `public` folder next to your app at `/static/public`.

### Script

For logic, export a Vue options object named `component`. The Python props and events are available in it as `this.<name>`:

```html
<script type="module">
  import { characters } from "./format.js";

  export const component = {
    data() { return { draft: "" }; },
    computed: { countLabel() { return characters(this.name.length); } },
    watch: { name(value) { this.draft = value; } },
    methods: { save() { this.check(this.draft); } },   // `check` is event_check
    mounted() {},
    beforeUnmount() {},                                 // clean up timers and document listeners here
  };
</script>
```

The options API (`data`, `computed`, `watch`, `methods`, lifecycle hooks, `components`) is the supported form.
The script can import other files by relative path (see below), so a child Vue component can live in its own `.js` file:
[example/topic_picker.js](example/topic_picker.js) exports an options object with a template string and is registered in `components`.
Between two Vue components, `$emit` and `v-model` are the normal way to talk. Only the line to Python avoids `$emit`.

## Relative imports

```js
import { characters } from "./format.js";
import TopicPicker from "./topic_picker.js";
```

Each imported file becomes its own ES module (loaded once per page, and shared by the components that import it), and its own relative imports work the same way.
A bare import such as `import * as React from "react"` works as it does in any ipyreact module.
These forms are rewritten: `import x from "./a.js"`, `import "./a.js"`, and `export ... from "./a.js"`.
A dynamic `import("./a.js")` is not rewritten, so it does not work.
Imports inside comments and strings are left as they are.
Regular expression literals are not understood: a quote or `//` inside one can hide the imports after it.
An import inside a nested template literal, such as `` `${`import "./a.js"`}` ``, is still rewritten.
A missing file or an import cycle raises a `ValueError`.

## Hot reload

In development mode (`solara run` without `--production`), a change to the HTML file, to a file it imports, or to a CSS file it `@import`s reloads the app, like a change to a Python file.
The reload runs the decorator again only when the component is defined in a file under the app's directory.

## Security

Treat the template as code you wrote, and values from Python or users as untrusted.

- `v-html`, and the direct bindings `:innerHTML` / `:outerHTML`, are refused when the decorator runs (`ValueError`). They put unchecked text in the page as markup.
  This is a safety net for mistakes, not a wall: a dynamic form such as `v-bind="{ innerHTML: x }"` is not detected. The template is code you wrote, so review it like code.
- `v-safe-html="text"` is the safe replacement. It parses the text without running anything, keeps a short list of tags and attributes (text formatting, lists, tables, links, images),
  drops scripts, frames, forms and event handlers, checks URLs, and adds `rel="noopener noreferrer"` to links.
- A guard watches the component's DOM and removes every attribute whose name starts with `on` (so a harmless custom attribute such as `only` goes too), `srcdoc`, and URLs in `href`, `src`, `action`, `formaction`, `poster`, `data` and `xlink:href`
  that are not relative or `http`, `https`, `mailto` or `tel`. It reports each removal as a warning in the browser console.
  It covers every way to set them (`:href`, `v-bind="object"`, a dynamic attribute name). Only these attributes are checked, so do not bind an untrusted value to another attribute that takes a URL or code, such as the SVG `<animate to>`.
- Do not bind untrusted data to `<component :is>` (or to a dynamic tag name in any other way): the guard checks attributes, not tag names.
- The Vue template compiler needs `unsafe-eval` in the page's Content-Security-Policy. A page with a strict CSP (no `unsafe-eval`) cannot run these components.

[example/security_app.py](example/security_app.py) shows unsafe markup on purpose, and `example/check_security.py` proves it is neutralised.

## How it works

It runs on [ipyreact](https://github.com/widgetti/ipyreact) ES modules, which Solara already supports:

1. At import, the package defines two shared ES modules with `ipyreact.define_module`: Vue 3 (a copy of the full browser build, the production or the development build by the Solara mode, see [solara_html/vendor](solara_html/vendor/README.md)) and `solara-html` ([runtime.js](solara_html/runtime.js)).
   Vue runs from its own ES module, so it does not touch the Vue on the Solara page, whether that is Vue 2 or 3.
2. The decorator turns each `.html` file into its own small ES module that holds data only: the template, the CSS, the prop and event names, and the text of the script and of every file it imports.
   The module is named by a hash of its code, so an edit shows up live after a hot reload. Each edit defines a new data module; old ones stay until the server restarts (only in development mode, where files change).
3. Each component instance is an `ipyreact.Widget` that names that module.
   ipyreact waits until the module is loaded before it renders, and passes the traits, setters, events, and children to it as React props.
   The runtime loads the script itself, as blob modules (through the same loader as ipyreact, so bare imports resolve), and mounts the Vue app when it is ready.
   Your JavaScript is never part of an ipyreact module, so a mistake in it cannot stop the other components.
4. The runtime renders a `div`, attaches a shadow root with the CSS, and mounts a Vue app there.
   The props are reactive state, with a getter and a setter each. The events are methods. Children stay in the light DOM, so the browser shows them at the `<slot>`.
   If the template or the script fails, the shadow root shows the error.

The browser receives each component's code once per page, not once per instance.

## Errors

- In development mode (`solara run` without `--production`), the browser console also warns about mistakes that would otherwise show as an empty spot,
  such as a name in the template that does not exist (`solara-html: [Vue warn]: Property "nme" was accessed during render but is not defined`).
  Production mode uses a smaller Vue build without these warnings. Look at the console in development mode first.
- A mistake in the template or in a method shows as a red message in the component, and the page keeps working. The browser console has the stack.
- A JavaScript error in a component's `<script>` or in a file it imports (a syntax error, a missing export, an error thrown while the file runs) shows in that component as `file name: error`, and the other components keep working. The browser reports no line number for a syntax error, so open the named file.
- A script that does not export `component` logs a `solara-html:` warning in the console. The template still shows.
- A mistake that Python can see raises a `ValueError` when the app starts, and the message names the file.

## Data

Props and event data travel as JSON, through the widget channel.

- Use `str`, `int`, `float`, `bool`, `None`, `list` and `dict`. Convert anything else first (`date.isoformat()`, `array.tolist()`).
  There is no `to_json` / `from_json` as in `solara.component_vue`, and no binary buffers.
- JSON has one number type. A whole number that the browser writes to a `float` prop reaches Python as an `int` (`2`, not `2.0`).
- Python cannot call a method in the browser. To tell the browser to do something (focus an input, play a sound), send a value it can react to,
  such as a counter prop with a `watch` in the script.
- Every change to a list or dict prop copies and compares the whole value. That is fine for hundreds of rows, not for tens of thousands.
- The package sends Vue (about 173 KB, 63 KB gzipped; the development build is 564 KB), the runtime and every component to the browser once per page, through the widget channel.

## Limits

- It targets the Solara server. Jupyter is not a goal.
- It needs a browser from 2022 or later: Chrome and Edge 98, Firefox 101, Safari 16.4 (constructable stylesheets, `structuredClone`).
- The template is compiled in the browser, which needs `unsafe-eval` in the CSP (see Security). The Vue build is about 63 KB gzipped.
- Only the default `<slot>` exists. Named slots are not possible, because the children are widgets.
- `<template>` is required. There are no single-file-component features such as `<script setup>` or `<style scoped>`; the Shadow DOM scopes the CSS.
- React loads on the page next to Vue.
- Page-wide CSS resets (such as Vuetify's `* { padding: 0 }`) beat `:host` rules, so put spacing on an element inside the template.
- Page classes and components (Vuetify, Solara) do not apply inside the component. Use CSS variables, `@import`, or a `<link>` with an absolute path. Write the markup with plain HTML.

## Development and examples

```bash
uv venv --python 3.11
uv pip install -e ".[dev]"
uv run playwright install chromium   # only for the browser checks
uv run pytest                        # unit tests
uv run ruff check . && uv run mypy   # lint and types (CI runs both)

# All browser checks (starts its own servers; needs `python` and `solara` on PATH)
source .venv/bin/activate && scripts/run_browser_checks.sh
```

The examples, each with a Playwright check you can run by hand: start the app with `uv run solara run example/<app>.py --port 8765`,
then in a second shell `uv run python example/<check>.py --url http://localhost:8765`.

| App | What it shows | Check |
| --- | --- | --- |
| [greeting_app.py](example/greeting_app.py) | `v-model`, computed values, an event, relative imports, a slot | `check.py` |
| [beacon_app.py](example/beacon_app.py) | Two instances, a debounced input, watchers, lifecycle, Solara widgets in the slot | `check_beacon.py` |
| [settings_app.py](example/settings_app.py) | `select`, checkbox, number validation, `v-if` chains, computed gating, a modal `<dialog>`, a slow server, a shared `@import`ed stylesheet | `check_settings.py` |
| [quiz_app.py](example/quiz_app.py) | A child component (`topic_picker.js`), events with data, keyboard shortcuts, timers, a `<dialog>` | `check_quiz.py` |
| [todo_app.py](example/todo_app.py) | A list of dicts that the browser edits (in place or by assignment) | `check_todo.py` |
| [security_app.py](example/security_app.py) | What the guard and `v-safe-html` remove | `check_security.py` |
| [greeting_app.py](example/greeting_app.py) again | Several browsers on one server, and a reload | `check_sessions.py` |
| [errors/errors_app.py](example/errors/errors_app.py) | Broken on purpose (template, syntax error, bad import, missing export, throw): each error shows in its own component and names the file, the page keeps working | `errors/check_errors.py` |

Hot reload in development mode (starts its own server): `uv run python example/check_hot_reload.py`.
