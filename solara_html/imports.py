"""Relative imports in component scripts: each imported file becomes its own ES module.

The browser runtime loads these modules itself, from the source text, so that an error in one file stays in
its component. (A module that ipyreact loads and that fails would stop every widget on the page.)

Only static imports are rewritten. A dynamic `import("./x.js")` is left as is, and does not work.
Comments and string literals are skipped, so an import inside them is not rewritten.
Regular expression literals are not understood: a quote or `//` inside one can hide the code after it.
An import-like string inside a nested template literal (`${`import "./x.js"`}` inside backticks) is still
rewritten, because a regular expression cannot track that nesting.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from solara.server.reload import watch_file

_RELATIVE_IMPORT = re.compile(
    r"""
    # Comments and string literals, kept as they are. They are matched where they start, so an import inside is skipped.
    (?P<skip>
        //[^\n]*
      | /\*.*?\*/
      | "(?:\\.|[^"\\\n])*"
      | '(?:\\.|[^'\\\n])*'
      | `(?:\\.|[^`\\])*`
    )
    # `import x from "./a.js"`, `import "./a.js"` and `export ... from "./a.js"`, with single or double quotes.
    # Between `import` or `export` and `from` there can be comments, but no string, call or other `/`.
  | (?P<head>
        \b(?:import|export)\b(?:[^'"`();/] | /\*(?:[^*]|\*(?!/))*\*/ | //[^\n]*\n)*?\bfrom\s*
      | \bimport\s*
    )
    (?P<quote>["'])(?P<specifier>\.\.?/[^'"\n]*)(?P=quote)
    """,
    re.DOTALL | re.VERBOSE,
)


def module_name(code: str) -> str:
    """The ES module name for some code, by content.

    The browser cannot point an existing module name at new code, so an edit must give a new name
    for hot reload to show it. Imported names are part of the importer's code, so the change propagates.
    """
    return "solara-html-" + hashlib.sha256(code.encode()).hexdigest()[:12]


def rewrite_relative_imports(code: str, to_name: Callable[[str], str]) -> str:
    """Replace each relative import specifier in `code` with `to_name(specifier)`."""

    def replace(match: re.Match[str]) -> str:
        if match.group("skip") is not None:
            return match.group("skip")
        quote = match.group("quote")
        return match.group("head") + quote + to_name(match.group("specifier")) + quote

    return _RELATIVE_IMPORT.sub(replace, code)


@dataclass(frozen=True)
class ScriptModule:
    """One JavaScript file for the runtime. Its relative imports are replaced by the ids of the modules they name."""

    id: str
    file: str  # for messages: the path relative to the component file
    code: str
    imports: tuple[str, ...]  # the ids of the modules this one imports, in order


def bundle_imports(code: str, importer: Path) -> list[ScriptModule]:
    """The script `code` and every file it imports relatively, in dependency order (the script is last).

    Each file is listed once and is watched for hot reload.
    """
    importer = importer.resolve()
    modules: dict[Path, ScriptModule] = {}
    _bundle(code, importer, importer.name + " (script)", importer.parent, modules, (importer,))
    return list(modules.values())


def _bundle(code: str, importer: Path, file: str, root: Path, modules: dict[Path, ScriptModule], stack: tuple[Path, ...]) -> None:
    imports: list[str] = []

    def to_name(specifier: str) -> str:
        path = (importer.parent / specifier).resolve()
        if path in stack:
            raise ValueError("import cycle: " + " -> ".join(str(p) for p in stack[stack.index(path) :] + (path,)))
        if path not in modules:
            if not path.is_file():
                raise ValueError(f"{importer}: imported file {specifier!r} does not exist ({path})")
            watch_file(path)
            _bundle(path.read_text(encoding="utf-8"), path, os.path.relpath(path, root), root, modules, stack + (path,))
        name = modules[path].id
        if name not in imports:
            imports.append(name)
        return name

    rewritten = rewrite_relative_imports(code, to_name)
    modules[importer] = ScriptModule(id=module_name(rewritten), file=file, code=rewritten, imports=tuple(imports))


# Any `@import`, except inside a comment. The browser ignores an `@import` in the stylesheet that the component builds
# from text, so every one must be a relative file (it is inlined) or an error.
_CSS_IMPORT = re.compile(r"(?P<comment>/\*.*?\*/)|@import\s+(?P<target>[^;]*);", re.DOTALL)
# `"./a.css"`, `'./a.css'`, `url("./a.css")`, `url(./a.css)`
_CSS_TARGET = re.compile(r"""(?:url\(\s*)?(?P<quote>["']?)(?P<specifier>\.\.?/[^"')\s]*)(?P=quote)\s*\)?""")


def inline_css_imports(css: str, importer: Path) -> str:
    """Replace each `@import "./file.css";` in `css` with the content of the file, and watch the file for hot reload.

    The component's stylesheet is built from text, and the browser ignores `@import` in such a stylesheet, so the files are
    inlined here. `url(...)` inside the files is not rewritten: it resolves against the page, so use absolute paths there.
    Any other `@import` (a remote URL, a media query) raises a `ValueError`.
    """
    return _inline_css_imports(css, importer.resolve(), (importer.resolve(),))


def _inline_css_imports(css: str, importer: Path, stack: tuple[Path, ...]) -> str:
    def replace(match: re.Match[str]) -> str:
        if match.group("comment"):
            return match.group("comment")
        target = _CSS_TARGET.fullmatch(match.group("target").strip())
        if target is None:
            raise ValueError(
                f"{importer}: cannot import {match.group('target').strip()!r}: only a relative file such as \"./a.css\" can be imported "
                'in <style>. Put other stylesheets in the template: <link rel="stylesheet" href="https://..." />'
            )
        specifier = target.group("specifier")
        path = (importer.parent / specifier).resolve()
        if path in stack:
            raise ValueError("CSS import cycle: " + " -> ".join(str(p) for p in stack[stack.index(path) :] + (path,)))
        if not path.is_file():
            raise ValueError(f"{importer}: imported file {specifier!r} does not exist ({path})")
        watch_file(path)
        return _inline_css_imports(path.read_text(encoding="utf-8"), path, stack + (path,))

    return _CSS_IMPORT.sub(replace, css)
