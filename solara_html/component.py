from __future__ import annotations

import functools
import inspect
import json
import re
from pathlib import Path
from typing import Any, Callable

import ipyreact
import traitlets

from solara.server.reload import watch_file
from solara_html.imports import ScriptModule, bundle_imports, inline_css_imports, module_name
from solara_html.parse import ComponentFile, parse_component_file

RUNTIME_MODULE = "solara-html"
VUE_MODULE = "solara-html-vue"

# Both are defined once, before any component module, so those can import them by name.
# Vue is the vendored `vue.esm-browser.prod.js` (the build with the template compiler); see vendor/README.md.
ipyreact.define_module(VUE_MODULE, Path(__file__).parent / "vendor" / "vue.esm-browser.prod.js")
ipyreact.define_module(RUNTIME_MODULE, Path(__file__).parent / "runtime.js")


def component_html(path: str) -> Callable[[Callable[..., None]], Callable[..., Any]]:
    """Turn a function signature plus a single-file HTML component into a Solara component.

    The path is relative to the file of the decorated function.
    A change to that file, or to a file it imports, reloads the app.
    The guide to writing the HTML file is `authoring.md`, next to this package's code.
    """

    def decorator(func: Callable[..., None]) -> Callable[..., Any]:
        signature = inspect.signature(func)
        component_path = (Path(inspect.getfile(func)).parent / path).resolve()
        watch_file(component_path)
        component = parse_component_file(component_path)
        _check_template(component.template, component_path)
        component = ComponentFile(
            template=_native_slots(component.template),
            css=inline_css_imports(component.css, component_path) if component.css else None,
            script=component.script,
        )
        prop_names, event_names = _split_arguments(list(signature.parameters))
        # The script and the files it imports go to the browser as text. The runtime loads them, so that an error in
        # one of them shows in this component and does not stop the page.
        modules = bundle_imports(component.script, component_path) if component.script else []
        code = _module_code(component, modules, prop_names, event_names)
        module = module_name(code)
        ipyreact.define_module(module, code=code)
        widget_class = _widget_from_signature(func.__name__ + "Widget", signature)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            values = dict(bound.arguments)
            if "children" in values and values["children"] is None:
                values["children"] = []  # ipyreact's children trait is a List
            # ipyreact passes each entry to React as a callable prop, named without the event_ prefix.
            events = {name[len("event_") :]: values.pop(name) for name in list(values) if name.startswith("event_")}
            # Reacton adds .element to widget classes at runtime
            return widget_class.element(_module=module, _type="Component", events=events, **values)  # type: ignore[attr-defined]

        return wrapper

    return decorator


def _split_arguments(arguments: list[str]) -> tuple[list[str], list[str]]:
    """The props and the event names among the arguments of the decorated function.

    `children` and `event_<name>` are not props. `on_<prop>` is a callback of that prop, when `<prop>` is an argument too.
    """
    props = [n for n in arguments if n != "children" and not n.startswith("event_") and not (n.startswith("on_") and n[len("on_") :] in arguments)]
    events = [n[len("event_") :] for n in arguments if n.startswith("event_")]
    return props, events


def _widget_from_signature(class_name: str, signature: inspect.Signature) -> type:
    """An ipyreact widget class with one synced trait per prop.

    ipyreact passes each trait to React as a prop, with a set<Name> setter.
    Two arguments that give the same React prop name are rejected, because one would hide the other.
    """
    arguments = list(signature.parameters)
    props, _ = _split_arguments(arguments)
    properties = {}
    react_names: dict[str, str] = {}  # React prop name -> the argument that gives it

    def claim(react_name: str, argument: str) -> None:
        if react_name in react_names:
            raise ValueError(f"{class_name}: arguments {react_names[react_name]!r} and {argument!r} both give the React prop {react_name!r}")
        react_names[react_name] = argument

    for name in arguments:
        if name.startswith("event_"):
            claim(name[len("event_") :], name)  # ipyreact already has events
        elif name in props:
            if name.startswith("_") or hasattr(ipyreact.Widget, name):
                raise ValueError(f"{class_name}: argument {name!r} clashes with an ipyreact.Widget attribute")
            claim(name, name)
            claim("set" + name[0].upper() + name[1:], name)
            properties[name] = traitlets.Any().tag(sync=True)
    return type(class_name, (ipyreact.Widget,), properties)


_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
# `v-html` and a binding to `innerHTML` or `outerHTML` put text in the page as markup. `v-safe-html` cleans it first.
_RAW_HTML_BINDING = re.compile(r"(?<![\w-])(?:v-html|(?:v-bind)?:\.?(?:innerhtml|outerhtml))(?![\w-])", re.IGNORECASE)


def _check_template(template: str, path: Path) -> None:
    match = _RAW_HTML_BINDING.search(_COMMENT.sub("", template))
    if match:
        raise ValueError(f"{path}: {match.group(0)!r} is not allowed because it inserts unchecked markup; use v-safe-html")


# Vue reads `<slot>` as a Vue slot outlet and drops it. A dynamic component named "slot" gives the native element,
# which shows the Python children (they stay in the light DOM) inside the shadow root.
_SLOT_OPEN = re.compile(r"<slot(?=[\s/>])")
_SLOT_CLOSE = re.compile(r"</slot\s*>")


def _native_slots(template: str) -> str:
    return _SLOT_CLOSE.sub("</component>", _SLOT_OPEN.sub("<component :is=\"'slot'\"", template))


def _module_code(component: ComponentFile, modules: list[ScriptModule], prop_names: list[str], event_names: list[str]) -> str:
    """The ipyreact module for one component. It holds data only, no user code, so it always loads."""
    spec = {
        "template": component.template,
        "css": component.css,
        "modules": [{"id": m.id, "file": m.file, "code": m.code, "imports": list(m.imports)} for m in modules],
        "entry": modules[-1].id if modules else None,
        "propNames": prop_names,
        "eventNames": event_names,
    }
    return f"""import {{ defineHtmlComponent }} from "{RUNTIME_MODULE}";
export const Component = defineHtmlComponent({json.dumps(spec)});
"""
