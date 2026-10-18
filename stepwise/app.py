import argparse
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, Footer, Input, Label, Markdown, OptionList, Static, TextArea
from textual.widgets.option_list import Option

from .readme import draft
from .stages import INTENT_QUESTION, INTROS, LAST_BUILT, PSEUDO_HINT, QUESTIONS, TITLES
from .steps import StepEditor
from .store import Project, slugify

TOTAL = len(TITLES)
SAVE_AFTER_IDLE = 5.0  # seconds without typing before an answer is written to disk
PREVIEW_AFTER_IDLE = 0.3  # seconds; the preview is in memory, so it can follow typing closely


@dataclass(frozen=True)
class Page:
    """One screen within a stage. Each holds a single thing to do, so no page is a wall of fields."""
    kind: str  # "answer", "steps", "readme" or "done"
    key: str = ""
    prompt: str = ""
    section: str = ""
    placeholder: str = ""


def pages(project: Project, stage: int) -> list[Page]:
    if stage > LAST_BUILT:
        return [Page("done")]
    questions = [Page("answer", q.key, q.prompt, q.section) for q in QUESTIONS[stage]]
    if stage == 1:
        return [Page("answer", "intent", INTENT_QUESTION, "the opening line"), *questions]
    if stage == 2:
        return [Page("steps"), *questions]
    if stage == 3:
        steps = project.steps()
        return [Page("answer", f"pseudo{n}", f"Step {n} of {len(steps)}: {step}", placeholder=PSEUDO_HINT)
                for n, step in enumerate(steps, 1)] + questions
    return [*questions, Page("readme")]


def page_missing(project: Project, page: Page) -> str:
    """What's left to do on this page, or an empty string."""
    if page.kind == "answer" and not project.answer(page.key):
        return "Answer this one before moving on."
    if page.kind == "steps" and not project.steps():
        return "Add at least one step before moving on."
    if page.kind == "readme" and not project.readme.is_file():
        return "Build your README draft before moving on."
    if page.kind == "readme" and project.readme_is_draft():
        return "Edit your README draft and save it before moving on."
    return ""


def anchor(heading: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")


class AnswerArea(TextArea):
    """A multi-line answer, saved to the project under `key` once the user pauses typing."""

    def __init__(self, key: str, text: str, placeholder: str = ""):
        super().__init__(text, soft_wrap=True, tab_behavior="focus", classes="answer", placeholder=placeholder)
        self.key = key
        self._focused_at = 0.0
        self._text_at_focus = text
        self._saved = text
        self._save_timer = None

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if self._save_timer:
            self._save_timer.stop()
        if self.text != self._saved:
            self._save_timer = self.set_timer(SAVE_AFTER_IDLE, self.save)
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
        return True

    def on_focus(self) -> None:
        self._focused_at = time.monotonic()
        self._text_at_focus = self.text

    def on_blur(self) -> None:
        if self.save():
            self.app.project.write_notes()
        seconds = round(time.monotonic() - self._focused_at, 1)
        changed = self.text != self._text_at_focus
        if changed or seconds >= 1:
            self.app.project.log("answer", key=self.key, seconds=seconds, changed=changed,
                                 chars=len(self.text.strip()), lines=len(self.text.strip().splitlines()))


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
        Binding("ctrl+n", "next", "Next", priority=True),
        Binding("ctrl+b", "back", "Back", priority=True),
        Binding("ctrl+r", "toggle_preview", "README preview", priority=True),
        Binding("ctrl+q", "quit", "Quit", priority=True),
    ]

    def __init__(self, project: Project | None):
        super().__init__()
        self.project = project
        self.current = 1
        self.page = 0
        self._preview_timer = None

    def compose(self) -> ComposeResult:
        yield Static(id="topbar")
        with Horizontal():
            yield OptionList(id="sidebar")
            yield VerticalScroll(id="stage")
            with VerticalScroll(id="preview"):
                yield Static("README preview · Ctrl+R hides it", id="preview-title")
                yield Markdown(id="preview-md")
        yield Footer()

    async def on_mount(self) -> None:
        if self.project is None:
            await self.push_screen(NameScreen(), callback=lambda _: self.call_later(self.start))
        else:
            await self.start()

    async def start(self) -> None:
        self.project.log("open", stage=self.project.stage)
        stage = min(self.project.stage, LAST_BUILT + 1)
        await self.go(stage, self.first_open_page(stage))

    # --- navigation ----------------------------------------------------

    @property
    def pages(self) -> list[Page]:
        return pages(self.project, self.current)

    def first_open_page(self, stage: int) -> int:
        stage_pages = pages(self.project, stage)
        return next((i for i, p in enumerate(stage_pages) if page_missing(self.project, p)), 0)

    async def go(self, stage: int, page: int) -> None:
        self.save_all()
        self.current = stage
        self.page = max(0, min(page, len(self.pages) - 1))
        here = self.pages[self.page]
        self.project.log("view", stage=stage, page=here.key or here.kind)
        self.refresh_chrome()
        container = self.query_one("#stage", VerticalScroll)
        await container.remove_children()
        await container.mount_all(self.page_widgets(here))
        container.scroll_home(animate=False)
        if field := next(iter(self.query("#stage AnswerArea, #stage StepEditor Input")), None):
            field.focus()
        self.schedule_preview()

    async def action_next(self) -> None:
        if self.current > LAST_BUILT:
            return
        self.save_all()
        if problem := page_missing(self.project, self.pages[self.page]):
            self.project.log("blocked", stage=self.current, page=self.pages[self.page].key or self.pages[self.page].kind)
            self.notify(problem, severity="warning", timeout=5)
            return
        if self.page < len(self.pages) - 1:
            await self.go(self.current, self.page + 1)
            return
        # Pages can be skipped through the sidebar, so the whole stage is checked before leaving it.
        if missing := self.project.missing(self.current):
            self.project.log("blocked", stage=self.current, missing=missing)
            self.notify("Before moving on, fill in: " + ", ".join(missing) + ".",
                        title="Not done yet", severity="warning", timeout=8)
            await self.go(self.current, self.first_open_page(self.current))
            return
        nxt = self.current + 1
        if nxt > self.project.stage:
            self.project.stage = nxt
            self.project.log("advance", stage=nxt)
        await self.go(nxt, 0)

    async def action_back(self) -> None:
        if self.page > 0:
            await self.go(self.current, self.page - 1)
        elif self.current > 1:
            await self.go(self.current - 1, len(pages(self.project, self.current - 1)) - 1)

    @on(Button.Pressed, "#next")
    async def next_pressed(self) -> None:
        await self.action_next()

    @on(Button.Pressed, "#back")
    async def back_pressed(self) -> None:
        await self.action_back()

    @on(OptionList.OptionSelected, "#sidebar")
    async def jump(self, event: OptionList.OptionSelected) -> None:
        n = int(event.option.id)
        if n != self.current:
            await self.go(n, self.first_open_page(n))

    def refresh_chrome(self) -> None:
        reached = self.project.stage
        bar = "".join(
            "[green]■[/]" if i < reached and i != self.current
            else "[b $accent]■[/]" if i == self.current
            else "[dim]□[/]"
            for i in range(1, TOTAL + 1)
        )
        where = f"Stage {self.current} of {TOTAL}"
        if len(self.pages) > 1:
            where += f" · {self.page + 1} of {len(self.pages)}"
        self.query_one("#topbar", Static).update(f"[b]Stepwise[/b] · {self.project.name}    {bar}  {where}")
        sidebar = self.query_one("#sidebar", OptionList)
        sidebar.clear_options()
        for i, title in enumerate(TITLES, 1):
            mark = "✓" if i < reached else "›" if i == self.current else " "
            sidebar.add_option(Option(f"{mark} {i}. {title}", id=str(i), disabled=i > reached or i > LAST_BUILT))
        sidebar.highlighted = self.current - 1

    # --- saving --------------------------------------------------------

    def save_all(self) -> None:
        """Writes any answer still waiting on its idle timer, then rebuilds notes.md once."""
        saved = [area.save() for area in self.query(AnswerArea)]
        if any(saved):
            self.project.write_notes()

    async def action_quit(self) -> None:
        self.save_all()
        self.exit()

    # --- preview -------------------------------------------------------

    def action_toggle_preview(self) -> None:
        preview = self.query_one("#preview")
        preview.display = not preview.display
        self.project.log("preview", shown=preview.display)
        self.schedule_preview()

    def schedule_preview(self) -> None:
        if self._preview_timer:
            self._preview_timer.stop()
        self._preview_timer = self.set_timer(PREVIEW_AFTER_IDLE, self.refresh_preview)

    async def refresh_preview(self) -> None:
        preview = self.query_one("#preview", VerticalScroll)
        if not preview.display:
            return
        here = self.pages[self.page]
        live = {area.key: area.text for area in self.query(AnswerArea)}
        markdown = self.query_one("#preview-md", Markdown)
        await markdown.update(draft(self.project, live, here.key if here.kind == "answer" else None))
        # Keep the part of the README this page writes in view.
        section = {"steps": "Build plan"}.get(here.kind, here.section)
        if section and section != "the opening line":
            markdown.goto_anchor(anchor(section))
        else:
            preview.scroll_home(animate=False)

    # --- pages ---------------------------------------------------------

    def page_widgets(self, page: Page) -> list[Widget]:
        p, n = self.project, self.current
        widgets: list[Widget] = [Label(f"{n}. {TITLES[n - 1]}", classes="stage-title")]
        if page.kind == "done":
            return widgets + [
                Static(f"Stages 1 to {LAST_BUILT} are done. You have a plan, pseudo-code, a stack "
                       "and a README draft, all in your own words.", classes="intro"),
                Static(f"Stage {n} isn't in Stepwise yet. Your files are in:\n\n  {p.root}", classes="intro"),
            ]
        if self.page == 0:
            widgets.append(Static(INTROS[n], classes="intro"))
        if n == 1 and self.page == 0:
            widgets.append(Static("Answers save when you pause typing. Each one becomes part of your app's "
                                  "README; the preview on the right shows where.", classes="hint"))
        if page.kind == "answer":
            widgets.append(Label(page.prompt, classes="question"))
            if page.section:
                widgets.append(Static(f"→ README · {page.section}", classes="tag"))
            widgets.append(AnswerArea(page.key, p.answer(page.key), page.placeholder))
        elif page.kind == "steps":
            widgets.append(Static(p.answer("intent"), classes="quote"))
            widgets.append(StepEditor(p))
        elif page.kind == "readme":
            widgets.append(ReadmePanel(p))
        back = Button("‹ Back", id="back", disabled=n == 1 and self.page == 0)
        back.can_focus = False  # so Tab from an answer lands on Next, and Tab, Enter moves forward
        widgets.append(Horizontal(back, Button("Next ›", id="next", variant="primary"), id="nav"))
        return widgets


class ReadmePanel(Vertical):
    """Stage 4's last page: build the README draft from the answers, then make it yours."""

    def __init__(self, project: Project):
        super().__init__(id="readme-panel")
        self.project = project

    def compose(self) -> ComposeResult:
        yield Label("Now turn your answers into README Part One.", classes="question")
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
        self.app.save_all()
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
