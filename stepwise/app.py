import argparse
import re
import shutil
import subprocess
import time
from pathlib import Path

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, Footer, Input, Label, Markdown, OptionList, Static
from textual.widgets.option_list import Option

from .answer import AnswerArea, AnswerLine, SavesAnswer
from .coding import CodePanel
from .pages import Page, page_missing, pages
from .prereqs import CheckPanel, DependencyPanel
from .readme import draft, part_two
from .runner import RunPanel
from .stages import INTROS, LAST_BUILT, PSEUDO_PRIMER, PSEUDO_WORDS, PSEUDOCODE_URL, TEST_PRIMER, TITLES
from .steps import StepEditor
from .store import Project, slugify

TOTAL = len(TITLES)
PREVIEW_AFTER_IDLE = 0.3  # seconds; the preview is in memory, so it can follow typing closely


def anchor(heading: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")


def open_in_code(project: Project, path: Path, what: str) -> None:
    code = shutil.which("code")
    if code and path.exists():
        project.log("readme", action="open_editor", file=path.name, what=what)
        subprocess.Popen([code, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


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
        self.project.log("view", stage=stage, page=here.key or here.kind, item=here.item or None)
        self.refresh_chrome()
        container = self.query_one("#stage", VerticalScroll)
        await container.remove_children()
        await container.mount_all(self.page_widgets(here))
        container.scroll_home(animate=False)
        if field := next(iter(self.query("#stage AnswerArea, #stage AnswerLine, #stage StepEditor Input")), None):
            field.focus()
        self.schedule_preview()

    async def go_to_page(self, stage: int, kind: str, key: str = "") -> None:
        """Jumps to the first page of a kind (and key, if given) in a stage."""
        stage_pages = pages(self.project, stage)
        await self.go(stage, next(i for i, p in enumerate(stage_pages)
                                  if p.kind == kind and (not key or p.key == key)))

    async def go_to_list(self, name: str) -> None:
        await self.go_to_page(4, "list", name)

    async def action_next(self) -> None:
        if self.current > LAST_BUILT:
            return
        self.save_all()
        here = self.pages[self.page]
        if problem := page_missing(self.project, here):
            self.project.log("blocked", stage=self.current, page=here.key or here.kind, reason=problem)
            self.notify(problem, severity="warning", timeout=5)
            return
        if self.page < len(self.pages) - 1:
            await self.go(self.current, self.page + 1)
            return
        # Pages can be skipped through the sidebar, so the whole stage is checked before leaving it.
        if missing := [p.label for p in self.pages if page_missing(self.project, p)]:
            self.project.log("blocked", stage=self.current, missing=missing)
            self.notify("Before moving on, finish: " + ", ".join(missing) + ".",
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

    @on(Button.Pressed, "#open-article")
    def open_article(self) -> None:
        self.project.log("open_article", url=PSEUDOCODE_URL)
        self.open_url(PSEUDOCODE_URL)

    @on(OptionList.OptionSelected, "#sidebar")
    async def jump(self, event: OptionList.OptionSelected) -> None:
        kind, _, target = event.option.id.partition(":")
        if kind == "page":
            stage, page = map(int, target.split(","))
            if (stage, page) != (self.current, self.page):
                await self.go(stage, page)
        elif (n := int(target)) != self.current:
            await self.go(n, self.first_open_page(n))

    def refresh_chrome(self) -> None:
        reached = self.project.stage
        bar = "".join(
            "[green]■[/]" if i < reached and i != self.current
            else "[b $accent]■[/]" if i == self.current
            else "[dim]□[/]"
            for i in range(1, TOTAL + 1)
        )
        if self.current > TOTAL:
            where = "All ten stages done"
        else:
            where = f"Stage {self.current} of {TOTAL}"
            if len(self.pages) > 1:
                where += f" · {self.page + 1} of {len(self.pages)}"
        self.query_one("#topbar", Static).update(f"[b]Stepwise[/b] · {self.project.name}    {bar}  {where}")
        self.refresh_sidebar()

    def refresh_sidebar(self) -> None:
        """Lists the stages, with the current stage's pages as a checklist underneath it."""
        reached = self.project.stage
        sidebar = self.query_one("#sidebar", OptionList)
        sidebar.clear_options()
        highlight = 0
        for i, title in enumerate(TITLES, 1):
            mark = "✓" if i < reached else "›" if i == self.current else " "
            sidebar.add_option(Option(f"{mark} {i}. {title}", id=f"stage:{i}", disabled=i > reached))
            if i != self.current:
                continue
            for n, page in enumerate(self.pages):
                tick = "□" if page_missing(self.project, page) else "✓"
                label = page.label if len(page.label) <= 24 else page.label[:23].rstrip() + "…"
                style = "bold" if n == self.page else "dim" if tick == "✓" else ""
                if n == self.page:
                    highlight = sidebar.option_count
                sidebar.add_option(Option(Text(f"    {tick} {label}", style=style), id=f"page:{i},{n}"))
        sidebar.highlighted = highlight or min(self.current, TOTAL) - 1

    # --- saving --------------------------------------------------------

    def save_all(self) -> None:
        """Writes any answer still waiting on its idle timer, then rebuilds notes.md once."""
        saved = [field.save() for field in self.answer_fields()]
        if any(saved):
            self.project.write_notes()

    def answer_fields(self) -> list[SavesAnswer]:
        return [*self.query(AnswerArea), *self.query(AnswerLine)]

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
        focus = {"answer": here.key, "list": f"list:{here.key}", "code": f"code:{here.key}:{here.item}",
                 "deps": "deps"}.get(here.kind)
        live = {field.key: field.text for field in self.answer_fields()}
        markdown = self.query_one("#preview-md", Markdown)
        await markdown.update(draft(self.project, live, focus))
        # Keep the part of the README this page writes in view.
        if here.section and here.section != "the opening line":
            markdown.goto_anchor(anchor(here.section))
        else:
            preview.scroll_home(animate=False)

    # --- pages ---------------------------------------------------------

    def page_widgets(self, page: Page) -> list[Widget]:
        p, n = self.project, self.current
        if page.kind == "done":
            return [
                Label("You built it.", classes="stage-title"),
                Static(f"All ten stages are done. {p.name} has a plan, code you wrote yourself, tests, and a "
                       "README in your own words.", classes="intro"),
                Static(f"Everything is in:\n\n  {p.root}", classes="intro"),
                Static("Your notes from every stage are in notes.md.", classes="hint"),
            ]
        widgets: list[Widget] = [Label(f"{n}. {TITLES[n - 1]}", classes="stage-title")]
        if self.page == 0:
            widgets.append(Static(INTROS[n], classes="intro"))
        if n == 1 and self.page == 0:
            widgets.append(Static("Answers save when you pause typing. Each one becomes part of your app's "
                                  "README; the preview on the right shows where.", classes="hint"))
        if page.note:
            widgets.append(Label(page.note, classes="section"))
        if page.prompt:
            widgets.append(Label(page.prompt, classes="question"))
        if page.section and page.kind in ("answer", "list", "code"):
            widgets.append(Static(f"→ README · {page.section}", classes="tag"))

        if page.kind == "answer" and page.line:
            widgets.append(AnswerLine(page.key, p.answer(page.key), page.placeholder))
            widgets.append(Static(f"Runs in {p.root}", classes="hint", markup=False))
        elif page.kind == "answer":
            widgets.append(AnswerArea(page.key, p.answer(page.key), page.placeholder))
            if page.key.startswith("pseudo") and page.key[6:].isdigit():
                widgets.append(Static(f"Pseudocode words: {PSEUDO_WORDS}", classes="hint"))
            if page.key == "review.hardest" and (notes := p.reminders()):
                widgets.append(Label("Your notes from building it:", classes="minor"))
                widgets.append(Static("\n".join(f"• {note}" for note in notes), classes="quote", markup=False))
        elif page.kind == "list" and page.key == "steps":
            widgets.append(Static(p.answer("intent"), classes="quote", markup=False))
            widgets.append(StepEditor(p, "steps", "Your steps"))
        elif page.kind == "list":
            title = {"files": "Your files", "tests": "Your tests"}[page.key]
            widgets.append(StepEditor(p, page.key, title))
        elif page.kind == "info":
            widgets.append(Markdown(PSEUDO_PRIMER if page.key == "pseudo" else TEST_PRIMER, classes="primer"))
            widgets.append(Static(PSEUDOCODE_URL, classes="hint", markup=False))
            widgets.append(Button("Open the article", id="open-article"))
        elif page.kind == "code":
            widgets.append(CodePanel(p, page.key, page.item))
        elif page.kind == "deps":
            widgets.append(DependencyPanel(p))
        elif page.kind == "check":
            widgets.append(CheckPanel(p))
        elif page.kind == "run":
            if page.key == "app":
                widgets.append(Static("If your app opens a window or keeps running, press Stop once you've "
                                      "seen it work.", classes="hint"))
            widgets.append(RunPanel(p, page.key))
        elif page.kind == "readme":
            widgets.append(ReadmePanel(p))
        elif page.kind == "part2":
            widgets.append(PartTwoPanel(p))

        back = Button("‹ Back", id="back", disabled=n == 1 and self.page == 0)
        back.can_focus = False  # so Tab from an answer lands on Next, and Tab, Enter moves forward
        widgets.append(Horizontal(back, Button("Next ›", id="next", variant="primary"), id="nav"))
        return widgets


class ReadmePanel(Vertical):
    """Stage 4's last page: build the README draft from the answers, then make it yours."""

    def __init__(self, project: Project):
        super().__init__(classes="readme-panel")
        self.project = project

    def compose(self) -> ComposeResult:
        yield Label("Now turn your answers into README Part One.", classes="question")
        yield Static("Build a draft from everything you've answered so far, then open it and make it read "
                     "well: fix the flow, cut what's repeated, add what's missing. Stepwise won't move on "
                     "until you've edited it.", classes="intro")
        with Horizontal(classes="readme-buttons"):
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
        self.app.refresh_sidebar()
        open_in_code(self.project, target, "draft")

    @on(Button.Pressed, "#open-code")
    def open_code(self) -> None:
        open_in_code(self.project, self.project.readme, "readme")


class PartTwoPanel(Vertical):
    """Stage 10's last page: add the sections that only exist now the app is built."""

    def __init__(self, project: Project):
        super().__init__(classes="readme-panel")
        self.project = project

    def compose(self) -> ComposeResult:
        yield Label("Now finish your README with Part Two.", classes="question")
        yield Static("This adds the sections your app has earned since Part One (how it's laid out, how to run "
                     "it, what's known to break, the tests, and what you learned) to the end of README.md. "
                     "Nothing you've already written is changed.", classes="intro")
        yield Static("If a stranger read your README, what would they still have to guess? Fix that, then save.",
                     classes="hint")
        with Horizontal(classes="readme-buttons"):
            yield Button("Add Part Two to README", id="add-part-two", variant="primary")
            if shutil.which("code"):
                yield Button("Open in VS Code", id="open-code")
        yield Static(str(self.project.readme), classes="hint")
        yield Static(id="readme-status")

    def on_mount(self) -> None:
        self.check()
        self.set_interval(1.5, self.check)

    def check(self) -> None:
        p = self.project
        if p.part_two_written():
            status = "[green]✓ README.md has Part Two and your edits in it.[/]"
        elif p.part_two_added():
            status = "[yellow]Part Two is added but untouched. Edit it and save.[/]"
        else:
            status = "[dim]Part Two isn't in your README yet.[/]"
        self.query_one("#readme-status", Static).update(status)

    @on(Button.Pressed, "#add-part-two")
    def add(self) -> None:
        self.app.save_all()
        text = part_two(self.project)
        self.project.append_part_two(text)
        self.project.log("readme", action="part_two", added=bool(text.strip()))
        if not text.strip():
            self.app.notify("Your README already has every Part Two section. Read it through and save.",
                            timeout=8)
        self.check()
        self.app.refresh_sidebar()
        open_in_code(self.project, self.project.readme, "part_two")

    @on(Button.Pressed, "#open-code")
    def open_code(self) -> None:
        open_in_code(self.project, self.project.readme, "readme")


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
