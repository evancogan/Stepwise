import argparse
import shutil
import subprocess
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, Footer, Input, Label, OptionList, Static, TextArea
from textual.widgets.option_list import Option

from .stages import INTENT_QUESTION, INTROS, LAST_BUILT, QUESTIONS, TITLES
from .steps import StepEditor
from .store import Project, slugify

TOTAL = len(TITLES)


class AnswerArea(TextArea):
    """A multi-line answer, saved to the project under `key` as it's typed."""

    def __init__(self, key: str, text: str):
        super().__init__(text, soft_wrap=True, tab_behavior="focus", classes="answer")
        self.key = key


def question(prompt: str, key: str, project: Project) -> list[Widget]:
    return [Label(prompt, classes="question"), AnswerArea(key, project.answer(key))]


class NameScreen(Screen):
    def compose(self) -> ComposeResult:
        with Vertical(id="welcome"):
            yield Label("Stepwise", id="welcome-title")
            yield Static("Stepwise asks the questions. You do the thinking and write every line.")
            yield Label("What's your app called?", classes="question")
            yield Input(placeholder="e.g. Breakout", id="app-name")

    @on(Input.Submitted, "#app-name")
    def create(self, event: Input.Submitted) -> None:
        name = event.value.strip()
        if not name:
            return
        root = Path.cwd() / slugify(name)
        self.app.project = Project.find(root) or Project.create(root, name)
        self.dismiss()


class StepwiseApp(App):
    CSS_PATH = "stepwise.tcss"
    TITLE = "Stepwise"
    BINDINGS = [
        Binding("ctrl+n", "next_stage", "Next stage", priority=True),
        Binding("ctrl+b", "prev_stage", "Back", priority=True),
        Binding("ctrl+q", "quit", "Quit", priority=True),
    ]

    def __init__(self, project: Project | None):
        super().__init__()
        self.project = project
        self.current = 1

    def compose(self) -> ComposeResult:
        yield Static(id="topbar")
        with Horizontal():
            yield OptionList(id="sidebar")
            yield VerticalScroll(id="stage")
        yield Footer()

    async def on_mount(self) -> None:
        if self.project is None:
            await self.push_screen(NameScreen(), callback=lambda _: self.call_later(self.start))
        else:
            await self.start()

    async def start(self) -> None:
        await self.show_stage(min(self.project.stage, LAST_BUILT + 1))

    # --- navigation ----------------------------------------------------

    async def show_stage(self, n: int) -> None:
        self.current = n
        self.refresh_chrome()
        stage = self.query_one("#stage", VerticalScroll)
        await stage.remove_children()
        await stage.mount_all(self.stage_widgets(n))
        stage.scroll_home(animate=False)
        self.focus_first_empty()

    def refresh_chrome(self) -> None:
        reached = self.project.stage
        bar = "".join(
            "[green]■[/]" if i < reached and i != self.current
            else "[b $accent]■[/]" if i == self.current
            else "[dim]□[/]"
            for i in range(1, TOTAL + 1)
        )
        self.query_one("#topbar", Static).update(
            f"[b]Stepwise[/b] · {self.project.name}    {bar}  Stage {self.current} of {TOTAL}"
        )
        sidebar = self.query_one("#sidebar", OptionList)
        sidebar.clear_options()
        for i, title in enumerate(TITLES, 1):
            mark = "✓" if i < reached else "›" if i == self.current else " "
            sidebar.add_option(Option(f"{mark} {i}. {title}", id=str(i), disabled=i > reached or i > LAST_BUILT))
        sidebar.highlighted = self.current - 1

    def focus_first_empty(self) -> None:
        fields = [w for w in self.query("#stage AnswerArea, #stage StepEditor Input") if w.focusable]
        empty = next((w for w in fields if not getattr(w, "text", getattr(w, "value", ""))), None)
        if target := empty or (fields[0] if fields else None):
            target.focus()
            self.call_after_refresh(target.scroll_visible)

    async def action_next_stage(self) -> None:
        if self.current > LAST_BUILT:
            return
        if missing := self.project.missing(self.current):
            self.notify("Before moving on, fill in: " + ", ".join(missing) + ".",
                        title="Not done yet", severity="warning", timeout=6)
            return
        nxt = self.current + 1
        if nxt > self.project.stage:
            self.project.stage = nxt
        await self.show_stage(nxt)

    async def action_prev_stage(self) -> None:
        if self.current > 1:
            await self.show_stage(self.current - 1)

    @on(OptionList.OptionSelected, "#sidebar")
    async def jump(self, event: OptionList.OptionSelected) -> None:
        n = int(event.option.id)
        if n != self.current:
            await self.show_stage(n)

    @on(TextArea.Changed)
    def save_answer(self, event: TextArea.Changed) -> None:
        if isinstance(event.text_area, AnswerArea):
            self.project.set_answer(event.text_area.key, event.text_area.text)

    # --- stages --------------------------------------------------------

    def stage_widgets(self, n: int) -> list[Widget]:
        p = self.project
        if n > LAST_BUILT:
            return [
                Label(f"{n}. {TITLES[n - 1]}", classes="stage-title"),
                Static(f"Stages 1 to {LAST_BUILT} are done. You have a plan, pseudo-code and a stack, "
                       "all in your own words.", classes="intro"),
                Static(f"Stage {n} isn't in Stepwise yet. Your files are in:\n\n  {p.root}", classes="intro"),
            ]

        widgets: list[Widget] = [
            Label(f"{n}. {TITLES[n - 1]}", classes="stage-title"),
            Static(INTROS[n], classes="intro"),
        ]
        if n == 1:
            widgets.append(Static("Answers save as you type. Tab moves to the next field.", classes="hint"))
            widgets += question(INTENT_QUESTION, "intent", p)
        if n == 2:
            widgets.append(Static(p.answer("intent"), classes="quote"))
            widgets.append(StepEditor(p))
        if n == 3:
            for i, step in enumerate(p.steps(), 1):
                widgets += question(f"Step {i}: {step}", f"pseudo{i}", p)
            widgets.append(Label("Now look back over your pseudo-code.", classes="section"))
        widgets += [w for i, q in enumerate(QUESTIONS[n], 1) for w in question(q, f"s{n}q{i}", p)]
        if n == 4:
            widgets.append(ReadmePanel(p))
        return widgets


class ReadmePanel(Vertical):
    """Stage 4's last task: the user writes README Part One in their editor."""

    def __init__(self, project: Project):
        super().__init__(id="readme-panel")
        self.project = project
        project.ensure_readme()

    def compose(self) -> ComposeResult:
        yield Label("Now write Part One of your README.", classes="section")
        yield Static("Open README.md in your editor and fill in each section in your own words. "
                     "Your answers so far are in notes.md.", classes="intro")
        yield Static(f"{self.project.readme}\n{self.project.root / 'notes.md'}", classes="hint")
        if shutil.which("code"):
            yield Button("Open in VS Code", id="open-code")
        yield Static(id="readme-status")

    def on_mount(self) -> None:
        self.check()
        self.set_interval(1.5, self.check)

    def check(self) -> None:
        done = self.project.readme_written()
        self.query_one("#readme-status", Static).update(
            "[green]✓ README.md has your writing in it.[/]" if done
            else "[yellow]README.md still matches the empty template. Save your edits there.[/]"
        )

    @on(Button.Pressed, "#open-code")
    def open_code(self) -> None:
        subprocess.Popen([shutil.which("code"), str(self.project.readme), str(self.project.root / "notes.md")],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> None:
    parser = argparse.ArgumentParser(prog="stepwise", description="Build your own app, one stage at a time.")
    parser.add_argument("project", nargs="?", help="project folder to open or create")
    args = parser.parse_args()
    if args.project:
        root = Path(args.project)
        project = Project.find(root) or Project.create(root, root.resolve().name)
    else:
        project = Project.find(Path.cwd())
    StepwiseApp(project).run()
