"""A two-file demo of native HTML and existing Solara/Vue widgets together.

Run from the repository root:
    uv run solara run example/beacon_app.py --no-open

The native Beacon is defined by beacon.html. The Solara slider and button are
Vue-backed widgets projected into its <slot>. Both control the same Python state.
The call-sign input keeps a local draft, so Python receives committed values
(after a pause, with Enter, or on blur) rather than one update per keystroke.
"""

import solara

import solara_html


@solara_html.component_html("beacon.html")
def Beacon(
    title: str,
    callsign: str,
    intensity: int,
    hue: int,
    transmissions: int,
    status: str,
    on_callsign=None,
    event_pulse=None,
    children=None,
):
    pass


@solara.component
def Station(title: str, initial_callsign: str, initial_intensity: int, hue: int):
    callsign, set_callsign = solara.use_state(initial_callsign)
    intensity, set_intensity = solara.use_state(initial_intensity)
    transmissions, set_transmissions = solara.use_state(0)

    def send_pulse(_payload):
        set_transmissions(transmissions + 1)

    def reset():
        set_callsign(initial_callsign)
        set_intensity(initial_intensity)
        set_transmissions(0)

    status = f"{transmissions:02d} transmissions · {intensity}% power"

    with solara.Column():
        Beacon(
            title=title,
            callsign=callsign,
            on_callsign=set_callsign,
            intensity=intensity,
            hue=hue,
            transmissions=transmissions,
            status=status,
            event_pulse=send_pulse,
            children=[
                solara.SliderInt("Power · Vue widget", value=intensity, min=0, max=100, on_value=set_intensity),
                solara.Button("Reset station · Vue widget", on_click=reset, text=True),
            ],
        )
        solara.Text(f"Python sees call sign: {callsign}", classes=["python-sees"])


@solara.component
def Page():
    with solara.Column(style={"max-width": "1160px", "margin": "32px auto", "padding": "0 16px"}):
        solara.Text("Beacon Lab", style={"font-size": "34px", "font-weight": "700", "color": "#182a3b"})
        solara.Text(
            "Two independent instances of one native HTML component. Edit a call sign or send a pulse inside either beacon; "
            "use the Vue-backed Solara controls embedded below each display to change its power. "
            "Call signs reach Python after a 500 ms pause, Enter, or blur.",
            style={"color": "#536979", "margin-bottom": "10px"},
        )
        with solara.ColumnsResponsive(12, medium=6):
            Station("Aurora relay", "AURORA-7", 64, 184)
            Station("Ember relay", "EMBER-3", 38, 24)
        solara.Text(
            "See example/beacon_app.py for Python state and the decorator, and example/beacon.html for the Vue template, scoped CSS, and browser JavaScript. "
            "The page shell and slotted sliders/buttons still use Solara's existing Vue path.",
            style={"color": "#536979", "font-size": "13px"},
        )
