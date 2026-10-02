"""Compatibility with Solara releases that do not have `solara.server.reload.watch_file` yet.

`watch_file` only powers hot reload in development mode (`solara run` without `--production`).
Everything else works without it. On a Solara release without it, editing an HTML component file
needs a restart of the server, instead of a reload of the app.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, Union

try:
    from solara.server.reload import watch_file
except ImportError:  # Solara < 1.64

    def watch_file(path: Union[str, Path], on_change: Optional[Callable[[str], None]] = None) -> None:  # type: ignore[misc]
        """No-op stand-in: this Solara release cannot hot reload files other than Python files."""


__all__ = ["watch_file"]
