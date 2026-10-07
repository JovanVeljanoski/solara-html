"""A list of dicts as a prop: the browser changes it in place or by assignment, and Python sees both.

Run from the repository root:
    uv run solara run example/todo_app.py --no-open
"""

import solara

import solara_html


@solara_html.component_html("todo.html")
def Todo(items: list = [], on_items=None, focus_count: int = 0):
    pass


items = solara.reactive([{"text": "Write the docs", "done": False}, {"text": "Ship it", "done": False}])
focus_count = solara.reactive(0)


@solara.component
def Page():
    with solara.Column(style={"padding": "1rem"}):
        Todo(items=items.value, on_items=items.set, focus_count=focus_count.value)
        solara.Button("Focus the input", on_click=lambda: focus_count.set(focus_count.value + 1), classes=["focus"])
        solara.Text(f"Python sees: {items.value}", classes=["python-sees"])
