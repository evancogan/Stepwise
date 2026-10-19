import time

from textual.widgets import Input, TextArea

SAVE_AFTER_IDLE = 5.0  # seconds without typing before an answer is written to disk


class SavesAnswer:
    """Saving shared by the answer widgets: written to the project under `key` once the user
    pauses typing, leaves the field, or the app saves everything. Subclasses provide `text`."""

    key: str
    text: str

    def setup_saving(self, key: str, text: str) -> None:
        self.key = key
        self._focused_at = 0.0
        self._text_at_focus = text
        self._saved = text
        self._save_timer = None

    def changed(self) -> None:
        if self._save_timer:
            self._save_timer.stop()
        if self.text != self._saved:
            self._save_timer = self.set_timer(SAVE_AFTER_IDLE, self.save_and_note)
        self.app.schedule_preview()

    def save(self) -> bool:
        """Writes the answer if it changed since the last save. Returns whether it wrote."""
        if self._save_timer:
            self._save_timer.stop()
            self._save_timer = None
        if self.text == self._saved:
            return False
        self.app.project.set_answer(self.key, self.text)
        self._saved = self.text
        self.app.refresh_sidebar()
        return True

    def save_and_note(self) -> None:
        if self.save():
            self.app.project.write_notes()

    def on_focus(self) -> None:
        self._focused_at = time.monotonic()
        self._text_at_focus = self.text

    def on_blur(self) -> None:
        self.save_and_note()
        seconds = round(time.monotonic() - self._focused_at, 1)
        changed = self.text != self._text_at_focus
        if changed or seconds >= 1:
            self.app.project.log("answer", key=self.key, seconds=seconds, changed=changed,
                                 chars=len(self.text.strip()), lines=len(self.text.strip().splitlines()))


class AnswerArea(SavesAnswer, TextArea):
    """A multi-line answer."""

    def __init__(self, key: str, text: str, placeholder: str = ""):
        super().__init__(text, soft_wrap=True, tab_behavior="focus", classes="answer", placeholder=placeholder)
        self.setup_saving(key, text)

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        self.changed()


class AnswerLine(SavesAnswer, Input):
    """A one-line answer, for things Stepwise runs, like a command. Enter moves on."""

    def __init__(self, key: str, text: str, placeholder: str = ""):
        super().__init__(text, placeholder=placeholder, classes="answer-line")
        self.setup_saving(key, text)

    @property
    def text(self) -> str:
        return self.value

    def on_input_changed(self, event: Input.Changed) -> None:
        self.changed()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        await self.app.action_next()
