import pytest
import solara

import solara_html


def test_argument_clashing_with_widget_attribute(tmp_path):
    path = tmp_path / "c.html"
    path.write_text("<template></template>", encoding="utf-8")

    def Component(open=False):
        pass

    with pytest.raises(ValueError, match="'open' clashes"):
        solara_html.component_html(str(path))(Component)


def prop_and_its_setter(x=None, setX=None):
    pass


def props_that_differ_in_case(x=None, X=None):
    pass


def prop_and_event(click=None, event_click=None):
    pass


@pytest.mark.parametrize(
    "Component, first, second, react_name",
    [
        (prop_and_its_setter, "x", "setX", "setX"),
        (props_that_differ_in_case, "x", "X", "setX"),
        (prop_and_event, "click", "event_click", "click"),
    ],
)
def test_arguments_with_the_same_react_prop(tmp_path, Component, first, second, react_name):
    path = tmp_path / "c.html"
    path.write_text("<template></template>", encoding="utf-8")

    with pytest.raises(ValueError, match=f"'{first}' and '{second}' both give the React prop '{react_name}'"):
        solara_html.component_html(str(path))(Component)


@pytest.mark.parametrize("children", [None, []])
def test_children_none_or_empty(tmp_path, children):
    path = tmp_path / "c.html"
    path.write_text("<template><slot></slot></template>", encoding="utf-8")

    @solara_html.component_html(str(path))
    def Html(name="World", children=[]):
        pass

    @solara.component
    def Test():
        return Html(name="Solara", children=children)

    widget, rc = solara.render_fixed(Test(), handle_error=False)
    assert widget.children == []
    assert widget.name == "Solara"
    rc.close()


@pytest.mark.parametrize(
    "template",
    [
        '<div v-html="text"></div>',
        '<div :innerHTML="text"></div>',
        '<div v-bind:innerHTML="text"></div>',
        '<div :outerHTML.prop="text"></div>',
        '<div :.innerHTML="text"></div>',
        '<DIV V-HTML="text"></DIV>',
    ],
)
def test_raw_html_bindings_are_refused(tmp_path, template):
    path = tmp_path / "c.html"
    path.write_text(f"<template>{template}</template>", encoding="utf-8")

    def Html(text=""):
        pass

    with pytest.raises(ValueError, match="use v-safe-html"):
        solara_html.component_html(str(path))(Html)


def test_safe_html_and_commented_raw_html_are_allowed(tmp_path):
    path = tmp_path / "c.html"
    path.write_text('<template><!-- v-html is refused --><div v-safe-html="text"></div></template>', encoding="utf-8")

    def Html(text=""):
        pass

    solara_html.component_html(str(path))(Html)


def test_native_slots():
    from solara_html.component import _native_slots

    assert _native_slots("<slot></slot>") == "<component :is=\"'slot'\"></component>"
    assert _native_slots('<slot name="x" />') == "<component :is=\"'slot'\" name=\"x\" />"
    assert _native_slots("<slotted></slotted>") == "<slotted></slotted>"


def test_props_and_events_are_passed_to_the_runtime(tmp_path):
    from solara_html.component import _module_code
    from solara_html.parse import parse_component_file

    path = tmp_path / "c.html"
    path.write_text('<template><p>{{ name }}</p></template><script type="module">export const component = {};</script>', encoding="utf-8")

    code = _module_code(parse_component_file(path), ["name"], ["reset"])

    assert "export const component = {};" in code
    assert 'propNames: ["name"]' in code
    assert 'eventNames: ["reset"]' in code


def test_property_and_event_names(tmp_path):
    path = tmp_path / "c.html"
    path.write_text("<template><p></p></template>", encoding="utf-8")
    seen = {}

    import solara_html.component as module

    original = module._module_code

    def spy(component, prop_names, event_names):
        seen["props"], seen["events"] = prop_names, event_names
        return original(component, prop_names, event_names)

    module._module_code = spy
    try:

        @solara_html.component_html(str(path))
        def Html(name="", on_name=None, on_other=None, event_reset=None, children=[]):
            pass

    finally:
        module._module_code = original

    # `on_name` belongs to the prop `name`; `on_other` has no prop, so it is a prop of its own.
    assert seen == {"props": ["name", "on_other"], "events": ["reset"]}
