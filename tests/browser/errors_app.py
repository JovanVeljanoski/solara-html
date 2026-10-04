"""Broken on purpose: an error in one component is shown in that component, and the page keeps working.

Run from the repository root:
    uv run solara run tests/browser/errors_app.py --no-open
"""

import solara

import solara_html


@solara_html.component_html("errors.html")
def Broken(name: str = ""):
    pass


@solara_html.component_html("errors_clash.html")
def Clash(name: str = ""):
    pass


@solara_html.component_html("errors_syntax.html")
def Syntax():
    pass


@solara_html.component_html("errors_import.html")
def BrokenImport():
    pass


@solara_html.component_html("errors_export.html")
def MissingExport():
    pass


@solara_html.component_html("errors_throw.html")
def Throws():
    pass


@solara_html.component_html("errors_nocomponent.html")
def NoComponent():
    pass


@solara_html.component_html("errors_react.html")
def UsesReact():
    pass


@solara_html.component_html("errors_fine.html")
def Fine(name: str = "World"):
    pass


show = solara.reactive(True)


@solara.component
def Page():
    with solara.Column(style={"padding": "1rem"}):
        # A component that comes and goes while its script loads must not leave anything behind.
        solara.Button("Toggle", on_click=lambda: show.set(not show.value), classes=["toggle"])
        if show.value:
            UsesReact()
        Broken(name="x")
        Clash(name="x")
        Syntax()
        BrokenImport()
        MissingExport()
        Throws()
        NoComponent()
        Fine()
