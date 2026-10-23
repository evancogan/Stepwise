import time

from rich.text import Text
from textual.widgets import Input, OptionList, TextArea
from textual.widgets.option_list import Option

from . import choices

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


class AnswerChoice(OptionList):
    """A multiple-choice answer. Picking an option saves it straight away, so unlike typed answers
    there's nothing to wait for. The picked option is marked ◉, like the sidebar's ticks."""

    def __init__(self, key: str, options: list[choices.Option], picked: str):
        super().__init__(classes="choice")
        self.key = key
        self.choices = options
        self.picked = picked

    def on_mount(self) -> None:
        # None draws a line between options, so each one's explanation reads as part of it.
        self.add_options(item for c in self.choices for item in (Option(self.prompt(c), id=c.key), None))
        keys = [c.key for c in self.choices]
        self.highlighted = keys.index(self.picked) if self.picked in keys else 0

    def prompt(self, option: choices.Option) -> Text:
        on = option.key == self.picked
        text = Text(f"{'◉' if on else '○'} {option.label}", style="bold" if on else "")
        for line in option.hint.splitlines():
            text.append(f"\n{line}", style="dim")  # flush left: a long line wraps there anyway
        return text

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        before, self.picked = self.picked, event.option.id
        for i, option in enumerate(self.choices):
            self.replace_option_prompt_at_index(i, self.prompt(option))
        project = self.app.project
        project.set_answer(self.key, self.picked)
        project.write_notes()
        # What was on offer is logged too, so the ranking can be judged against what people pick.
        project.log("choice", key=self.key, picked=self.picked, before=before or None,
                    shown=[c.key for c in self.choices])
        self.app.refresh_chrome()  # a pick can add or remove pages, which the top bar counts
        self.app.schedule_preview()
