"""A settings form: select, checkbox, number and text inputs, computed values, v-if chains and a modal dialog.

Run from the repository root:
    uv run solara run example/settings_app.py --no-open

The `on_<prop>` callbacks are real Solara state setters. The nickname setter is slow on purpose, to show that
fast typing is not lost while the server is behind.
"""

import time

import solara

import solara_html


@solara_html.component_html("settings.html")
def Settings(
    user: str = "",
    email: str = "",
    is_subscribed: bool = False,
    pro_credits: int = 0,
    value_num_questions: int = 10,
    on_value_num_questions=None,
    language_level: str = "A2",
    on_language_level=None,
    audio_questions: bool = False,
    on_audio_questions=None,
    ai_checker: bool = False,
    on_ai_checker=None,
    nickname: str = "",
    on_nickname=None,
    event_subscribe=None,
    event_manage_subscription=None,
    event_delete_account=None,
):
    pass


subscribed = solara.reactive(False)
credits = solara.reactive(0)
num = solara.reactive(10)
level = solara.reactive("B1")
audio = solara.reactive(False)
ai = solara.reactive(False)
nickname = solara.reactive("")
log = solara.reactive([])


def record(name: str):
    log.set([*log.value, name])


def slow_nickname(value: str):
    time.sleep(0.3)  # a slow server: the echo of each keystroke arrives late
    nickname.set(value)


@solara.component
def Page():
    with solara.Column(style={"padding": "1rem"}):
        Settings(
            user="Ada",
            email="ada@example.com",
            is_subscribed=subscribed.value,
            pro_credits=credits.value,
            value_num_questions=num.value,
            on_value_num_questions=num.set,
            language_level=level.value,
            on_language_level=level.set,
            audio_questions=audio.value,
            on_audio_questions=audio.set,
            ai_checker=ai.value,
            on_ai_checker=ai.set,
            nickname=nickname.value,
            on_nickname=slow_nickname,
            event_subscribe=lambda _data: (record("subscribe"), subscribed.set(True)),
            event_manage_subscription=lambda _data: record("manage"),
            event_delete_account=lambda _data: record("delete"),
        )
        solara.Text(
            f"Python sees: num={num.value} level={level.value} audio={audio.value} ai={ai.value} nick={nickname.value!r} events={log.value}",
            classes=["python-sees"],
        )
