"""A quiz page in one HTML file: a topic picker, events that carry data, keyboard shortcuts and a modal dialog.

Run from the repository root:
    uv run solara run example/quiz_app.py --no-open

quiz.html imports a child component (topic_picker.js) and a shared stylesheet (buttons.css).
The Python side owns the quiz state. The browser sends `start`, `check`, `next` and `cancel` events.
"""

import solara

import solara_html

TOPICS = ["Greetings", "Food", "Travel", "Numbers"]
TOPICS_DONE = [1, 0, 0, 0]
QUESTIONS = [
    ("Translate to Spanish", "hello", "hola"),
    ("Translate to Spanish", "goodbye", "adios"),
    ("Translate to Spanish", "thanks", "gracias"),
]


@solara_html.component_html("quiz.html")
def Quiz(
    page_header: str = "",
    topic: list = [],
    on_topic=None,
    topics: list = [],
    topics_done: list = [],
    loading: bool = False,
    is_active: bool = False,
    is_checked: bool = False,
    is_correct: bool = False,
    question_prompt: str = "",
    question: str = "",
    message: str = "",
    progress: float = 0,
    event_start=None,
    event_check=None,
    event_next=None,
    event_cancel=None,
):
    pass


topic = solara.reactive([])
active = solara.reactive(False)
index = solara.reactive(0)
checked = solara.reactive(False)
correct = solara.reactive(False)
correct_count = solara.reactive(0)
log = solara.reactive([])


def record(*entry):
    log.set([*log.value, entry])


def start(topics):
    record("start", list(topics))
    index.set(0)
    correct_count.set(0)
    checked.set(False)
    active.set(True)


def check(answer):
    record("check", answer)
    ok = answer.strip().lower() == QUESTIONS[index.value][2]
    correct.set(ok)
    correct_count.set(correct_count.value + (1 if ok else 0))
    checked.set(True)


def next_question(_data):
    record("next")
    checked.set(False)
    if index.value + 1 >= len(QUESTIONS):
        active.set(False)
        record("finished", correct_count.value)
    else:
        index.set(index.value + 1)


def cancel(_data):
    record("cancel")
    active.set(False)


@solara.component
def Page():
    prompt, question, _answer = QUESTIONS[index.value]
    with solara.Column(style={"padding": "1rem"}):
        Quiz(
            page_header="Quiz",
            topic=topic.value,
            on_topic=topic.set,
            topics=TOPICS,
            topics_done=TOPICS_DONE,
            is_active=active.value,
            is_checked=checked.value,
            is_correct=correct.value,
            question_prompt=prompt,
            question=question,
            message="Great!" if correct.value else "The answer was different.",
            progress=100 * correct_count.value / len(QUESTIONS),
            event_start=start,
            event_check=check,
            event_next=next_question,
            event_cancel=cancel,
        )
        solara.Text(f"Python sees: events={log.value} topic={topic.value}", classes=["python-sees"])
