"""Broken on purpose: shows that an error in one component is shown in that component, and the page keeps working.

Run from the repository root:
    uv run solara run example/errors_app.py --no-open
"""

import solara

import solara_html


@solara_html.component_html("errors.html")
def Broken(name: str = ""):
    pass


@solara_html.component_html("errors_clash.html")
def Clash(name: str = ""):
    pass


@solara_html.component_html("greeting.html")
def Fine(name: str = "World", is_default: bool = True, on_name=None, event_reset=None, children=[]):
    pass


@solara.component
def Page():
    with solara.Column(style={"padding": "1rem"}):
        Broken(name="x")
        Clash(name="x")
        Fine()
