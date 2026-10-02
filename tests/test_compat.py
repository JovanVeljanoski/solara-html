import importlib
import sys
import types

import solara_html._compat as compat


def test_watch_file_falls_back_to_a_noop_without_solara_support(monkeypatch, tmp_path):
    """Solara < 1.64 has no `watch_file`; the package must still import and work."""
    import solara.server.reload as reload_module

    monkeypatch.delattr(reload_module, "watch_file", raising=False)
    try:
        module = importlib.reload(compat)
        assert module.watch_file(tmp_path / "x.html") is None
        assert module.watch_file(tmp_path / "x.html", on_change=lambda path: None) is None
    finally:
        monkeypatch.undo()
        importlib.reload(compat)


def test_watch_file_uses_solara_when_available(monkeypatch):
    calls = []
    fake = types.ModuleType("solara.server.reload")
    fake.watch_file = lambda path, on_change=None: calls.append(path)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "solara.server.reload", fake)
    try:
        module = importlib.reload(compat)
        module.watch_file("somewhere.html")
        assert calls == ["somewhere.html"]
    finally:
        monkeypatch.undo()
        importlib.reload(compat)
