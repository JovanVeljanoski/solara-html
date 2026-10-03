"""Unsafe markup on purpose, to show what solara-html removes. The check is `check_security.py`.

Run from the repository root:
    uv run solara run example/security_app.py --no-open
"""

import solara

import solara_html

UNSAFE_HTML = (
    '<b class="x">bold</b>'
    "<script>window.pwned = 1</script>"
    '<img alt="pic" src="javascript:window.pwned = 1" onerror="window.pwned = 1">'
    '<a href="javascript:window.pwned = 1">bad link</a>'
    '<a href="https://example.com/">good link</a>'
    '<iframe src="https://example.com/"></iframe>'
)


@solara_html.component_html("security.html")
def Unsafe(url: str = "", html: str = ""):
    pass


@solara.component
def Page():
    Unsafe(url="javascript:window.pwned = 1", html=UNSAFE_HTML)
