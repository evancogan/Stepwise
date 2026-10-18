import argparse
import shutil
import subprocess
import time
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, Footer, Input, Label, OptionList, Static, TextArea
from textual.widgets.option_list import Option

from .readme import draft
from .stages import INTENT_QUESTION, INTROS, LAST_BUILT, PSEUDO_HINT, QUESTIONS, TITLES, Question
from .steps import StepEditor
from .store import Project, slugify

TOTAL = len(TITLES)


class AnswerArea(TextArea):
    """A multi-line answer, saved to the project under `key` as it's typed."""

    BINDINGS = [Binding("tab", "next_field", "Next field", show=False)]

    def __init__(self, key: str, text: str, placeholder: str = ""):
        super().__init__(text, soft_wrap=True, tab_behavior="focus", classes="answer", placeholder=placeholder)
        self.key = key
        self.follow: "AnswerArea | None" = None
        self._focused_at = 0.0
        self._text_at_focus = text

    def on_focus(self) -> None:
        self._focused_at = time.monotonic()
        self._text_at_focus = self.text

    def on_blur(self) -> None:
        seconds = round(time.monotonic() - self._focused_at, 1)
        changed = self.text != self._text_at_focus
        if changed or seconds >= 1:
            self.app.project.log("answer", key=self.key, seconds=seconds, changed=changed,
                                 chars=len(self.text.strip()), lines=len(self.text.strip().splitlines()))
        if self.follow_waiting():
            self.reveal_follow()

    def follow_waiting(self) -> bool:
        return bool(self.follow and self.text.strip() and not self.follow.parent.display)

    def reveal_follow(self) -> None:
        self.follow.parent.display = True
        self.app.project.log("follow_up", key=self.key)

    def action_next_field(self) -> None:
        """Tab after a first answer opens its follow-up and moves there, like a reply in a conversation."""
        if self.follow_waiting():
            self.reveal_follow()
            self.follow.focus()
            self.call_after_refresh(self.follow.scroll_visible)
        else:
            self.screen.focus_next()


class QuestionBlock(Vertical):
    def __init__(self, project: Project, key: str, prompt: str, section: str = "",
                 follow: str = "", follow_key: str = "", placeholder: str = ""):
        super().__init__(classes="qa")
        self.main = AnswerArea(key, project.answer(key), placeholder)
        self.prompt, self.section, self.follow_prompt = prompt, section, follow
        if follow:
            self.main.follow = AnswerArea(follow_key, project.answer(follow_key))

    @classmethod
    def of(cls, project: Project, q: Question) -> "QuestionBlock":
        return cls(project, q.key, q.prompt, q.section, q.follow, q.follow_key)

    def compose(self) -> ComposeResult:
        yield Label(self.prompt, classes="question")
        if self.section:
            yield Static(f"→ README · {self.section}", classes="tag")
        yield self.main
        if self.main.follow:
            with Vertical(classes="follow") as box:
                box.display = bool(self.main.text.strip())
                yield Label(self.follow_prompt, classes="question")
                yield self.main.follow


def shown(w: Widget) -> bool:
    return all(node.display for node in w.ancestors_with_self if isinstance(node, Widget))


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
        self.project.log("open", stage=self.project.stage)
        await self.show_stage(min(self.project.stage, LAST_BUILT + 1))

    # --- navigation ----------------------------------------------------

    async def show_stage(self, n: int) -> None:
        self.current = n
        self.project.log("view", stage=n)
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
        fields = [w for w in self.query("#stage AnswerArea, #stage StepEditor Input") if shown(w)]
        empty = next((w for w in fields if not getattr(w, "text", getattr(w, "value", ""))), None)
        if target := empty or (fields[0] if fields else None):
            target.focus()
            self.call_after_refresh(target.scroll_visible)

    async def action_next_stage(self) -> None:
        if self.current > LAST_BUILT:
            return
        if missing := self.project.missing(self.current):
            self.project.log("blocked", stage=self.current, missing=missing)
            self.notify("Before moving on, fill in: " + ", ".join(missing) + ".",
                        title="Not done yet", severity="warning", timeout=8)
            return
        nxt = self.current + 1
        if nxt > self.project.stage:
            self.project.stage = nxt
            self.project.log("advance", stage=nxt)
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
                Static(f"Stages 1 to {LAST_BUILT} are done. You have a plan, pseudo-code, a stack "
                       "and a README draft, all in your own words.", classes="intro"),
                Static(f"Stage {n} isn't in Stepwise yet. Your files are in:\n\n  {p.root}", classes="intro"),
            ]

        widgets: list[Widget] = [
            Label(f"{n}. {TITLES[n - 1]}", classes="stage-title"),
            Static(INTROS[n], classes="intro"),
        ]
        if n == 1:
            widgets.append(Static("Answers save as you type. Tab moves to the next field. "
                                  "Each answer goes into your app's README, so write it for a reader.",
                                  classes="hint"))
            widgets.append(QuestionBlock(p, "intent", INTENT_QUESTION, "the opening line"))
        if n == 2:
            widgets.append(Static(p.answer("intent"), classes="quote"))
            widgets.append(StepEditor(p))
        if n == 3:
            for i, step in enumerate(p.steps(), 1):
                widgets.append(QuestionBlock(p, f"pseudo{i}", f"Step {i}: {step}", placeholder=PSEUDO_HINT))
            widgets.append(Label("Now look back over your pseudo-code.", classes="section"))
        widgets += [QuestionBlock.of(p, q) for q in QUESTIONS[n]]
        if n == 4:
            widgets.append(ReadmePanel(p))
        return widgets


class ReadmePanel(Vertical):
    """Stage 4's last task: build the README draft from the answers, then make it yours."""

    def __init__(self, project: Project):
        super().__init__(id="readme-panel")
        self.project = project

    def compose(self) -> ComposeResult:
        yield Label("Now turn your answers into README Part One.", classes="section")
        yield Static("Build a draft from everything you've answered so far, then open it and make it read "
                     "well: fix the flow, cut what's repeated, add what's missing. Stepwise won't move on "
                     "until you've edited it.", classes="intro")
        with Horizontal(id="readme-buttons"):
            yield Button("Build README draft", id="build-draft", variant="primary")
            if shutil.which("code"):
                yield Button("Open in VS Code", id="open-code")
        yield Static(str(self.project.readme), classes="hint")
        yield Static(id="readme-status")

    def on_mount(self) -> None:
        self.check()
        self.set_interval(1.5, self.check)

    def check(self) -> None:
        p = self.project
        self.query_one("#build-draft", Button).label = "Rebuild draft" if p.readme.exists() else "Build README draft"
        if p.readme_written():
            status = "[green]✓ README.md has your edits in it.[/]"
        elif p.readme.exists():
            status = "[yellow]README.md is still the untouched draft. Edit it and save.[/]"
        else:
            status = "[dim]No README yet.[/]"
        self.query_one("#readme-status", Static).update(status)

    @on(Button.Pressed, "#build-draft")
    def build(self) -> None:
        target = self.project.write_draft(draft(self.project))
        self.project.log("readme", action="draft", file=target.name)
        if target != self.project.readme:
            self.app.notify(f"You've already edited README.md, so the new draft went to {target.name}.",
                            timeout=8)
        self.check()
        self.open_code(target)

    @on(Button.Pressed, "#open-code")
    def open_code(self, target: Path | None = None) -> None:
        code = shutil.which("code")
        path = target if isinstance(target, Path) else self.project.readme
        if code and path.exists():
            self.project.log("readme", action="open_editor", file=path.name)
            subprocess.Popen([code, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> None:
    parser = argparse.ArgumentParser(prog="stepwise", description="Build your own app, one stage at a time.")
    parser.add_argument("project", nargs="?", help="project folder to open or create")
    args = parser.parse_args()
    if args.project:
        root = Path(args.project)
        project = Project.find(root) or Project.create(root, root.resolve().name)
    else:
        project = Project.find(Path.cwd())
    app = StepwiseApp(project)
    started = time.monotonic()
    app.run()
    if app.project:
        app.project.log("quit", stage=app.current, minutes=round((time.monotonic() - started) / 60, 1))
