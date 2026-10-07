"""The docs page (docs/index.html) must say what the shipped code does.

The code in the page is run (here: loaded; tests/browser/check_docs.py also drives it in a browser).
The facts in the page that are also in the code (versions, names, lists) are compared with the code.
"""

import inspect
import re
import runpy
import tomllib
from html.parser import HTMLParser
from pathlib import Path

import ipyreact
import pytest

from solara_html.component import _check_template, _widget_from_signature

ROOT = Path(__file__).parent.parent
PAGE = ROOT / "docs" / "index.html"
REPOSITORY = "https://github.com/JovanVeljanoski/solara-html"


class _Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.files: dict[str, str] = {}  # code with a data-file attribute
        self.sync: dict[str, str] = {}  # text of an element with a data-sync attribute
        self.links: list[str] = []
        self.images: dict[str, str] = {}  # src -> alt
        self.ids: list[str] = []
        self.tags_before_first_h2: list[str] = []
        self._collect: tuple[str, str, str] | None = None  # (kind, key, tag) of the element that is being read
        self._text: list[str] = []
        self._seen_h2 = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "h2":
            self._seen_h2 = True
        if not self._seen_h2:
            self.tags_before_first_h2.append(attributes.get("id") or tag)
        if attributes.get("id"):
            self.ids.append(attributes["id"])
        if tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"])
        if tag == "img":
            self.images[attributes.get("src") or ""] = attributes.get("alt") or ""
        if attributes.get("data-file"):
            self._collect, self._text = ("file", attributes["data-file"], tag), []
        elif attributes.get("data-sync"):
            self._collect, self._text = ("sync", attributes["data-sync"], tag), []

    def handle_data(self, data: str) -> None:
        if self._collect:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._collect and self._collect[2] == tag:
            kind, key, _ = self._collect
            (self.files if kind == "file" else self.sync)[key] = "".join(self._text)
            self._collect = None


@pytest.fixture(scope="module")
def page() -> _Page:
    parsed = _Page()
    parsed.feed(PAGE.read_text(encoding="utf-8"))
    return parsed


def _words(text: str) -> list[str]:
    return [word.strip() for word in text.split(",") if word.strip()]


def _js_set(name: str) -> list[str]:
    """The strings in `const <name> = new Set([...])` of runtime.js."""
    runtime = (ROOT / "solara_html" / "runtime.js").read_text(encoding="utf-8")
    match = re.search(rf"const {name} = new Set\(\[(.*?)\]\)", runtime, re.DOTALL)
    assert match, f"{name} not found in runtime.js"
    return re.findall(r'"([^"]*)"', match.group(1))


def test_the_page_starts_with_the_alpha_warning(page: _Page) -> None:
    assert "alpha-warning" in page.tags_before_first_h2
    assert "likely to change" in PAGE.read_text(encoding="utf-8")


def test_ids_are_unique_and_anchors_exist(page: _Page) -> None:
    assert len(page.ids) == len(set(page.ids))
    for link in page.links:
        if link.startswith("#"):
            assert link[1:] in page.ids, link


def test_links_to_the_repository_point_to_files_that_exist(page: _Page) -> None:
    for link in page.links:
        match = re.fullmatch(rf"{re.escape(REPOSITORY)}/(?:blob|tree)/master/(.+)", link)
        if match:
            assert (ROOT / match.group(1)).exists(), link


def test_every_example_has_an_app_and_its_files(page: _Page) -> None:
    folders = {name.split("/")[0] for name in page.files}
    assert folders
    for folder in folders:
        assert f"{folder}/app.py" in page.files
        app = page.files[f"{folder}/app.py"]
        for html in re.findall(r'component_html\("([^"]+)"\)', app):
            assert f"{folder}/{html}" in page.files, f"{folder}: {html} is not in the page"


def test_the_examples_load(page: _Page, tmp_path: Path) -> None:
    for name, text in page.files.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    for app in sorted(tmp_path.glob("*/app.py")):
        namespace = runpy.run_path(str(app))  # the decorator reads and checks the HTML file
        assert "Page" in namespace, app


def test_every_example_shows_its_result(page: _Page) -> None:
    # check_docs.py saves these pictures when the page is published; they are not in the repository.
    for folder in {name.split("/")[0] for name in page.files}:
        assert page.images.get(f"img/{folder}.png"), f"no <img src=\"img/{folder}.png\" alt=...> for the example {folder}"


def test_every_example_app_is_listed(page: _Page) -> None:
    for app in sorted((ROOT / "example").glob("*_app.py")):
        assert f"{REPOSITORY}/blob/master/example/{app.name}" in page.links, f"{app.name} is not listed on the page"


def test_the_install_command_is_the_one_in_the_readme() -> None:
    command = f"pip install git+{REPOSITORY}.git"
    assert command in PAGE.read_text(encoding="utf-8")
    assert command in (ROOT / "README.md").read_text(encoding="utf-8")


def test_python_and_solara_versions_are_the_ones_in_pyproject(page: _Page) -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["requires-python"] == f">={page.sync['python']}"
    assert f"solara-ui>={page.sync['solara']}" in project["dependencies"]


def test_the_vue_version_is_the_vendored_one(page: _Page) -> None:
    for build in ("vue.esm-browser.js", "vue.esm-browser.prod.js"):
        header = (ROOT / "solara_html" / "vendor" / build).read_text(encoding="utf-8")[:200]
        assert f"vue v{page.sync['vue'].removeprefix('Vue ')}" in header, build


def test_reserved_names_are_refused(page: _Page) -> None:
    names = _words(page.sync["reserved"])
    assert names
    for name in names:
        namespace: dict = {}
        exec(f"def f({name}=None): pass", namespace)
        with pytest.raises(ValueError, match="clashes"):
            _widget_from_signature("Widget", inspect.signature(namespace["f"]))
        assert hasattr(ipyreact.Widget, name)


def test_refused_bindings_are_refused(page: _Page) -> None:
    names = _words(page.sync["refused"])
    assert names
    for name in names:
        with pytest.raises(ValueError):
            _check_template(f'<p {name}="x"></p>', Path("x.html"))


def test_the_guard_lists_are_the_ones_in_the_runtime(page: _Page) -> None:
    assert set(_words(page.sync["url-attributes"])) == set(_js_set("URL_ATTRIBUTES"))
    assert set(_words(page.sync["protocols"])) == set(_js_set("SAFE_PROTOCOLS"))
