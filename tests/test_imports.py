import json
import unittest.mock
from pathlib import Path

import pytest

import solara_html.imports
from solara_html.imports import bundle_imports, inline_css_imports, module_name, rewrite_relative_imports


def test_rewrite_static_relative_imports_only():
    code = """
import a from "./a.js";
import { b,
  c } from '../b.js';
import "./side.js";
export * from "./d.js";
export { e } from './e.js';
import React from "react";
const lazy = import("./lazy.js");
"""
    rewritten = rewrite_relative_imports(code, lambda specifier: "m:" + specifier)

    assert 'import a from "m:./a.js";' in rewritten
    assert "c } from 'm:../b.js';" in rewritten
    assert 'import "m:./side.js";' in rewritten
    assert 'export * from "m:./d.js";' in rewritten
    assert "export { e } from 'm:./e.js';" in rewritten
    assert 'import React from "react";' in rewritten
    assert 'import("./lazy.js")' in rewritten


def test_rewrite_skips_comments_and_strings():
    code = r"""
// import "./line.js";
/* import a from "./block.js";
   export * from "./block2.js"; */
const s = 'import "./single.js"';
const d = "import \"./double.js\"; import './inner.js'";
const t = `import x from "./template.js"`;
export { a } // from "./trailing.js"
import b from "./real.js";
"""
    rewritten = rewrite_relative_imports(code, lambda specifier: "m:" + specifier)

    assert rewritten == code.replace('"./real.js"', '"m:./real.js"')


def test_rewrite_import_with_comments_before_from():
    code = """
import x /* c */ from "./x.js";
import { a, // note
  b } from './y.js';
"""
    rewritten = rewrite_relative_imports(code, lambda specifier: "m:" + specifier)

    assert rewritten == code.replace('"./x.js"', '"m:./x.js"').replace("'./y.js'", "'m:./y.js'")


def test_rewrite_leaves_json_template_string_alone():
    # The generated component code holds the template as a JSON string.
    code = 'import "./a.js";\nconst template = ' + json.dumps("<script type=\"module\">import './b.js';</script>") + ";"

    rewritten = rewrite_relative_imports(code, lambda specifier: "m:" + specifier)

    assert rewritten == code.replace('"./a.js"', '"m:./a.js"')


@pytest.fixture(autouse=True)
def watch_file():
    with unittest.mock.patch.object(solara_html.imports, "watch_file") as watch_file:
        yield watch_file


def test_bundle_ignores_commented_import_of_missing_file(tmp_path: Path):
    code = '// import "./missing.js";\nexport const a = 1;'

    (entry,) = bundle_imports(code, tmp_path / "main.html")

    assert entry.code == code
    assert entry.imports == ()


def test_bundle_depth_first_and_once(tmp_path: Path, watch_file):
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "a.js").write_text('import { c } from "./c.js";\nexport const a = c;', encoding="utf-8")
    (tmp_path / "lib" / "c.js").write_text("export const c = 1;", encoding="utf-8")
    (tmp_path / "b.js").write_text('import { c } from "./lib/c.js";\nexport const b = c;', encoding="utf-8")

    c, a, b, entry = bundle_imports('import { a } from "./lib/a.js";\nimport { b } from "./b.js";', tmp_path / "main.html")

    assert c.id == module_name("export const c = 1;")
    assert (c.file, a.file, b.file, entry.file) == (str(Path("lib/c.js")), str(Path("lib/a.js")), "b.js", "main.html (script)")
    assert a.code == f'import {{ c }} from "{c.id}";\nexport const a = c;'
    assert a.imports == (c.id,)
    assert b.imports == (c.id,)
    assert entry.code == f'import {{ a }} from "{a.id}";\nimport {{ b }} from "{b.id}";'
    assert entry.imports == (a.id, b.id)
    assert {call.args[0] for call in watch_file.call_args_list} == {(tmp_path / n).resolve() for n in ("lib/a.js", "lib/c.js", "b.js")}


def test_bundle_without_imports(tmp_path: Path):
    (entry,) = bundle_imports("export const component = {};", tmp_path / "main.html")

    assert entry.imports == ()
    assert entry.id == module_name("export const component = {};")


def test_bundle_missing_file_names_importer(tmp_path: Path):
    (tmp_path / "a.js").write_text('import "./missing.js";', encoding="utf-8")

    with pytest.raises(ValueError, match=r"a\.js: imported file './missing.js' does not exist"):
        bundle_imports('import "./a.js";', tmp_path / "main.html")


def test_bundle_cycle(tmp_path: Path):
    (tmp_path / "a.js").write_text('import "./b.js";', encoding="utf-8")
    (tmp_path / "b.js").write_text('import "./a.js";', encoding="utf-8")

    with pytest.raises(ValueError, match="import cycle"):
        bundle_imports('import "./a.js";', tmp_path / "main.html")


def test_bundle_keeps_a_broken_file_as_text(tmp_path: Path):
    # The Python side does not read JavaScript. A syntax error is for the browser to report, in its component.
    (tmp_path / "a.js").write_text("export const a = ;", encoding="utf-8")

    a, entry = bundle_imports('import { a } from "./a.js";', tmp_path / "main.html")

    assert a.code == "export const a = ;"


def test_module_name_is_by_content():
    assert module_name("export const a = 1;") == module_name("export const a = 1;")
    assert module_name("export const a = 1;") != module_name("export const a = 2;")


def test_inline_css_imports(tmp_path: Path):
    (tmp_path / "shared").mkdir()
    (tmp_path / "shared" / "base.css").write_text(".a { color: red; }", encoding="utf-8")
    (tmp_path / "buttons.css").write_text('@import "./shared/base.css";\n.b { color: blue; }', encoding="utf-8")

    with unittest.mock.patch.object(solara_html.imports, "watch_file") as watch_file:
        css = inline_css_imports('@import "./buttons.css";\n@import url(\'./shared/base.css\');\n.c { color: green; }', tmp_path / "main.html")

    assert css == ".a { color: red; }\n.b { color: blue; }\n.a { color: red; }\n.c { color: green; }"
    watched = {call.args[0] for call in watch_file.call_args_list}
    assert watched == {(tmp_path / "buttons.css").resolve(), (tmp_path / "shared" / "base.css").resolve()}


def test_inline_css_imports_leaves_remote_and_absolute_imports(tmp_path: Path):
    css = '@import "https://example.com/a.css";\n@import url(/static/public/b.css);'

    assert inline_css_imports(css, tmp_path / "main.html") == css


def test_inline_css_imports_missing_file_names_importer(tmp_path: Path):
    with pytest.raises(ValueError, match=r"main\.html: imported file './missing.css' does not exist"):
        inline_css_imports('@import "./missing.css";', tmp_path / "main.html")


def test_inline_css_imports_cycle(tmp_path: Path):
    (tmp_path / "a.css").write_text('@import "./b.css";', encoding="utf-8")
    (tmp_path / "b.css").write_text('@import "./a.css";', encoding="utf-8")

    with unittest.mock.patch.object(solara_html.imports, "watch_file"), pytest.raises(ValueError, match="CSS import cycle"):
        inline_css_imports('@import "./a.css";', tmp_path / "main.html")


def test_inline_css_imports_ignores_comments(tmp_path: Path):
    css = '/* use @import "./missing.css"; here */\n.a { color: red; }'

    assert inline_css_imports(css, tmp_path / "main.html") == css
