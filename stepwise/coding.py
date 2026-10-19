"""One step (or test) being coded: its pseudo-code beside a live view of the file it goes in."""

import shutil
import subprocess
import time

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Checkbox, Label, Select, Static, TextArea

from .answer import AnswerArea
from .store import Project

REFRESH_EVERY = 1.0  # seconds between checks of the file on disk


def ago(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s ago"
    if seconds < 3600:
        return f"{int(seconds // 60)} min ago"
    return f"{int(seconds // 3600)} h ago"


class CodePanel(Vertical):
    """`kind` is "steps" (stage 5) or "tests" (stage 9); `n` is the item's 1-based position."""

    def __init__(self, project: Project, kind: str, n: int):
        super().__init__(classes="code-panel")
        self.project = project
        self.kind = kind
        self.n = n
        self.prefix = f"code{n}" if kind == "steps" else f"test{n}"
        self.pseudo_key = f"pseudo{n}" if kind == "steps" else f"test{n}.pseudo"
        self._seen_mtime: float | None = None

    @property
    def file_name(self) -> str:
        if self.kind == "tests":
            return self.project.answer("tests.file").strip()
        return self.project.step_file(self.n)

    def compose(self) -> ComposeResult:
        p = self.project
        yield Label("Your pseudo-code", classes="minor")
        yield Static(p.answer(self.pseudo_key) or "(no pseudo-code yet)", classes="quote", markup=False)
        # The file part needs files from stage 4 (or, for tests, the test file named in stage 9).
        ready = bool(p.files()) if self.kind == "steps" else bool(self.file_name)
        if not ready:
            yield Static("Your files from stage 4 appear here." if self.kind == "steps"
                         else "Your test file appears here once you've named it on this stage's first page.",
                         classes="waiting-note")
        with Vertical(classes="panel-body" + ("" if ready else " waiting")):
            if self.kind == "steps":
                yield Label("Which file does this step go in?", classes="question")
                options = [(f"{name}  ({purpose})" if purpose else name, name) for name, purpose in p.files()]
                with Horizontal(classes="file-pick"):
                    yield Select(options, value=self.default_file(), prompt="Choose a file", id="file-select")
                    yield Button("Add a file", id="add-file")
            else:
                yield Label(f"Your test file: {self.file_name or '(not chosen yet)'}", classes="question")
            with Horizontal(classes="file-bar"):
                if shutil.which("code"):
                    yield Button("Open in VS Code", id="open-file")
                yield Static(id="file-status")
            yield TextArea("", read_only=True, soft_wrap=False, show_line_numbers=True, id="file-view")
            yield Checkbox("It's written and saved", value=bool(p.answer(f"{self.prefix}.done")), id="done",
                           disabled=not ready)
        yield Label("Stuck? What did you expect to happen, and what happened instead?", classes="question")
        yield AnswerArea(f"{self.prefix}.stuck", p.answer(f"{self.prefix}.stuck"), "Optional")

    def default_file(self):
        """This step's file, else the previous step's, else the only file there is."""
        names = [name for name, _ in self.project.files()]
        for n in range(self.n, 0, -1):
            if (name := self.project.step_file(n)) in names:
                if n != self.n:
                    self.project.set_answer(f"code{self.n}.file", name)
                return name
        if len(names) == 1:
            self.project.set_answer(f"code{self.n}.file", names[0])
            return names[0]
        return Select.NULL

    def on_mount(self) -> None:
        self.refresh_file()
        self.set_interval(REFRESH_EVERY, self.refresh_file)

    def refresh_file(self) -> None:
        status = self.query_one("#file-status", Static)
        view = self.query_one("#file-view", TextArea)
        path = self.project.code_path(self.file_name)
        if not self.file_name:
            status.update("[dim]Pick the file this step goes in.[/]")
            view.load_text("")
        elif path is None:
            status.update("[red]That file is outside your project folder.[/]")
        elif not path.exists():
            status.update(f"[yellow]Can't find {self.file_name} yet.[/]")
            view.load_text("")
            self._seen_mtime = None
        else:
            mtime = path.stat().st_mtime
            if mtime != self._seen_mtime:
                self._seen_mtime = mtime
                view.load_text(path.read_text(encoding="utf-8", errors="replace"))
            lines = len(view.text.splitlines())
            status.update(f"{self.file_name} · {lines} lines · saved {ago(time.time() - mtime)}"
                          if lines else f"{self.file_name} · [yellow]empty[/]")

    @on(Select.Changed, "#file-select")
    def file_chosen(self, event: Select.Changed) -> None:
        name = "" if event.value is Select.NULL else str(event.value)
        if name != self.project.step_file(self.n):
            self.project.set_answer(f"code{self.n}.file", name)
            self.project.log("code_file", step=self.n, file=name)
            self.project.write_notes()
        self._seen_mtime = None
        self.refresh_file()
        self.app.refresh_sidebar()
        self.app.schedule_preview()

    @on(Checkbox.Changed, "#done")
    def ticked(self, event: Checkbox.Changed) -> None:
        if event.value and (problem := self.tick_problem()):
            with event.checkbox.prevent(Checkbox.Changed):
                event.checkbox.value = False
            self.project.log("code_done_refused", item=self.prefix, reason=problem)
            self.app.notify(problem, severity="warning", timeout=8)
            return
        if event.value:
            self.project.record_tick(self.file_name, self.prefix)
        self.project.set_answer(f"{self.prefix}.done", "yes" if event.value else "")
        self.project.log("code_done", item=self.prefix, done=event.value)
        self.project.write_notes()
        self.app.refresh_sidebar()
        self.app.schedule_preview()

    def tick_problem(self) -> str:
        """Why this step can't be ticked done yet, or an empty string."""
        path = self.project.code_path(self.file_name)
        if not self.file_name:
            return "Pick the file this step goes in first."
        if path is None or not path.is_file():
            return f"Stepwise can't find {self.file_name}."
        if not path.read_text(encoding="utf-8", errors="replace").strip():
            return f"{self.file_name} is empty. Write this step's code and save it first."
        if not self.project.changed_since_last_tick(self.file_name, self.prefix):
            return (f"{self.file_name} hasn't changed since you ticked the last step in it. Write this "
                    "step's code and save, then tick it.")
        return ""

    @on(Button.Pressed, "#add-file")
    async def add_file(self) -> None:
        await self.app.go_to_list("files")

    @on(Button.Pressed, "#open-file")
    def open_file(self) -> None:
        code = shutil.which("code")
        if code and (path := self.project.code_path(self.file_name)) and path.exists():
            self.project.log("code_open", file=self.file_name)
            subprocess.Popen([code, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
