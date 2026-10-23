import argparse
import re
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import quote_plus

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
from .pages import Page, page_done, page_missing, pages
from .prereqs import CheckPanel, DependencyPanel
from .readme import draft, part_two
from .runner import RunPanel
from .stages import (INTROS, LAST_BUILT, PSEUDO_PRIMER, PSEUDO_WORDS, PSEUDOCODE_URL, RESOURCES_QUESTION,
                     SEARCH_URL, TEST_PRIMER, TITLES, search_query)
from .steps import StepEditor
from .store import Project, git_root, projects_dir, slugify

TOTAL = len(TITLES)
PREVIEW_AFTER_IDLE = 0.3  # seconds; the preview is in memory, so it can follow typing closely


def anchor(heading: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")


def open_in_code(project: Project, path: Path, what: str) -> None:
    code = shutil.which("code")
    if code and path.exists():
        project.log("readme", action="open_editor", file=path.name, what=what)
        subprocess.Popen([code, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def repo_here() -> Path | None:
    """The git repo Stepwise was started in, to offer building there. Never Stepwise's own source,
    so launching from it doesn't fill it with projects."""
    repo = git_root(Path.cwd())
    return repo if repo and repo != Path(__file__).resolve().parents[1] else None


class NameScreen(Screen):
    def __init__(self, repo: Path | None):
        super().__init__()
        self.repo = repo

    def compose(self) -> ComposeResult:
        with Vertical(id="welcome"):
            yield Label("Stepwise", id="welcome-title")
            yield Static("Stepwise asks the questions. You do the thinking and write every line.")
            if self.repo:
                yield Label("Build your app in this repo?", classes="question")
                yield Static(str(self.repo), classes="hint", markup=False)
                yield Button("Start here", id="start-here", variant="primary")
                yield Label("Or start a new app in its own folder. What's it called?", classes="question")
            else:
                yield Label("What's your app called?", classes="question")
            yield Input(placeholder="e.g. Breakout", id="app-name")

    @on(Button.Pressed, "#start-here")
    def start_here(self) -> None:
        self.app.project = Project.create(self.repo, self.repo.name)
        self.dismiss()

    @on(Input.Submitted, "#app-name")
    def create(self, event: Input.Submitted) -> None:
        name = event.value.strip()
        if not name:
            return
        root = projects_dir() / slugify(name)
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
            await self.push_screen(NameScreen(repo_here()), callback=lambda _: self.call_later(self.start))
        else:
            await self.start()

    async def start(self) -> None:
        self.project.log("open", stage=self.project.stage)
        stage = min(self.project.stage, LAST_BUILT + 1)
        await self.go(stage, self.first_open_page(stage))

    # --- navigation ----------------------------------------------------

    @property
    def pages(self) -> list[Page]:
        return pages(self.project, self.current) or [Page("empty", label="Nothing yet", note="Nothing here yet.")]

    @property
    def ahead(self) -> bool:
        """On a stage past the user's progress: clicked into to see what's coming, not to finish it."""
        return self.current > self.project.stage

    def first_open_page(self, stage: int) -> int:
        stage_pages = pages(self.project, stage)
        return next((i for i, p in enumerate(stage_pages) if page_missing(self.project, p)), 0)

    async def go(self, stage: int, page: int) -> None:
        self.save_all()
        self.current = stage
        self.page = max(0, min(page, len(self.pages) - 1))
        here = self.pages[self.page]
        self.project.log("view", stage=stage, page=here.key or here.kind, item=here.item or None,
                         ahead=self.ahead or None)
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
        if self.ahead:
            # Nothing on a stage the user hasn't reached is theirs to finish yet, so Next just moves on.
            if self.page < len(self.pages) - 1:
                await self.go(self.current, self.page + 1)
            elif self.current < LAST_BUILT:
                await self.go(self.current + 1, 0)
            return
        if self.page < len(self.pages) - 1:
            await self.go(self.current, self.page + 1)
            return
        # Pages can be skipped, so the whole stage is checked before leaving it.
        if missing := [p.label for p in self.pages if page_missing(self.project, p)]:
            self.project.log("blocked", stage=self.current, missing=missing)
            self.notify("Before moving on, finish: " + ", ".join(missing) + ".",
                        title="Not done yet", severity="warning", timeout=8)
            await self.go(self.current, self.first_open_page(self.current))
            return
        nxt = self.current + 1
        # Only finishing the furthest stage moves progress on; a stage revisited behind it never does.
        if self.current == self.project.stage:
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

    @on(Button.Pressed, "#open-research")
    def open_research(self) -> None:
        url = SEARCH_URL + quote_plus(search_query(self.project.name))
        self.project.log("open_research", url=url)
        self.open_url(url)

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
            where = "All ten stages done" if self.project.stage > LAST_BUILT else "Finish"
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
            # Stages past the user's progress stay clickable, so anyone can see what's coming; dim marks them as not started.
            sidebar.add_option(Option(Text(f"{mark} {i}. {title}", style="dim" if i > reached else ""), id=f"stage:{i}"))
            if i != self.current:
                continue
            for n, page in enumerate(self.pages):
                tick = "✓" if i <= reached and page_done(self.project, page) else "□"
                label = page.label if len(page.label) <= 24 else page.label[:23].rstrip() + "…"
                style = "bold" if n == self.page else "dim" if tick == "✓" or i > reached else ""
                if n == self.page:
                    highlight = sidebar.option_count
                sidebar.add_option(Option(Text(f"    {tick} {label}", style=style), id=f"page:{i},{n}"))
        finished = reached > LAST_BUILT
        mark = "›" if self.current > TOTAL else "✓" if finished else " "
        if self.current > TOTAL:
            highlight = sidebar.option_count
        sidebar.add_option(Option(Text(f"{mark} Finish", style="" if finished else "dim"), id=f"stage:{TOTAL + 1}"))
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
            back = Button("‹ Back", id="back")
            back.can_focus = False
            return [CongratsPanel(p), Horizontal(back, id="nav")]
        widgets: list[Widget] = [Label(f"{n}. {TITLES[n - 1]}", classes="stage-title")]
        if self.page == 0:
            widgets.append(Static(INTROS[n], classes="intro"))
        if n == 1 and self.page == 0:
            widgets.append(Static("Answers save when you pause typing. Each one becomes part of your app's "
                                  "README; the preview on the right shows where.", classes="hint"))
        if page.note and page.kind != "empty":
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
            title = {"files": "Your files", "tests": "Your tests", "resources": "Your resources"}[page.key]
            if page.key == "resources":
                widgets.append(Static(search_query(p.name), classes="quote", markup=False))
                widgets.append(Button("Search Google", id="open-research"))
                widgets.append(Label(RESOURCES_QUESTION, classes="question"))
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
        elif page.kind == "empty":
            widgets.append(Static(page.note, classes="waiting-note"))
            if page.placeholder:
                widgets.append(Static(page.placeholder, classes="waiting sample", markup=False))

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
        built = p.readme_draft.exists() if p.readme_is_original() else p.readme.exists()
        self.query_one("#build-draft", Button).label = "Rebuild draft" if built else "Build README draft"
        if p.readme_written():
            status = "[green]✓ README.md has your edits in it.[/]"
        elif p.readme_is_original() and p.readme_draft.exists():
            status = (f"[yellow]Your draft is in {p.readme_draft.name}. Bring what you want from it into "
                      "README.md and save.[/]")
        elif p.readme_is_original():
            status = "[dim]README.md was here before Stepwise. Your draft will go next to it.[/]"
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
            why = ("README.md was here before Stepwise" if self.project.readme_is_original()
                   else "You've already edited README.md")
            self.app.notify(f"{why}, so the new draft went to {target.name}.", timeout=8)
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
        yield Static("Part Two is added after README Part One, in stage 4.", classes="waiting-note", id="part2-waiting")
        with Vertical(classes="panel-body", id="part2-body"):
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
        # Part Two goes on the end of the README written in Part One; without it there's nothing to add to.
        ready = p.readme_written()
        self.query_one("#part2-waiting").display = not ready
        self.query_one("#part2-body").set_class(not ready, "waiting")
        self.query_one("#add-part-two", Button).disabled = not ready
        if not ready:
            status = ""
        elif p.part_two_written():
            status = "[green]✓ README.md has Part Two and your edits in it.[/]"
        elif p.part_two_added():
            status = "[yellow]Part Two is added but untouched. Edit it and save.[/]"
        else:
            status = "[dim]Part Two isn't in your README yet.[/]"
        self.query_one("#readme-status", Static).update(status)

    @on(Button.Pressed, "#add-part-two")
    def add(self) -> None:
        if not self.project.readme_written():
            return
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


class CongratsPanel(Vertical):
    """The page after stage 10. It opens at any time, like every stage, showing whatever's been done so far."""

    def __init__(self, project: Project):
        super().__init__(classes="congrats-panel")
        self.project = project

    def compose(self) -> ComposeResult:
        p = self.project
        with Vertical(classes="panel-body"):
            yield Label(f"Congratulations! You built {p.name}.", classes="congrats-title")
            yield Static("Every line of it is yours. You planned it, wrote it, ran it, tested it and wrote it up, "
                         "one stage at a time, without anything writing it for you.", classes="intro")
            yield Static("\n".join(f"• {line}" for line in self.stats()), classes="congrats-stats", markup=False)
            if again := p.answer("review.again"):
                yield Label("Your advice to yourself, for next time", classes="minor")
                yield Static(again, classes="quote", markup=False)
            if later := p.answer("steps.later"):
                yield Label("What you said you'd add next", classes="minor")
                yield Static(later, classes="quote", markup=False)
            yield Static(f"Your app, its README and your notes from every stage are in:\n  {p.root}",
                         classes="hint", markup=False)
            if shutil.which("code"):
                yield Button("Open your README", id="open-readme", variant="primary",
                             disabled=not p.readme.is_file())

    def stats(self) -> list[str]:
        p = self.project
        steps, tests = p.steps(), p.tests()
        built = sum(bool(p.answer(f"code{n}.done")) for n in range(1, len(steps) + 1))
        written = sum(bool(p.answer(f"test{n}.done")) for n in range(1, len(tests) + 1))
        lines = [f"{built} of {len(steps)} steps built, across {len(p.files())} files"]
        if tests:
            passing = " and passing" if p.outcome("tests") == "ok" else ""
            lines.append(f"{written} tests written{passing}")
        failures = p.failures("app")
        if p.outcome("app") == "ok":
            lines.append("It ran on the first try" if not failures else
                         f"It took {failures + 1} runs to get it working, and you explained every error on the way")
        if started := p.started():
            days = (time.time() - started.timestamp()) / 86400
            lines.append(f"Started {started:%d %B}" + (", and finished the same day" if days < 1 else
                                                         f", {int(days)} days ago"))
        return lines

    @on(Button.Pressed, "#open-readme")
    def open_readme(self) -> None:
        open_in_code(self.project, self.project.readme, "readme")


def main() -> None:
    parser = argparse.ArgumentParser(prog="stepwise", description="Build your own app, one stage at a time.")
    parser.add_argument("project", nargs="?", help="project folder to open or create")
    args = parser.parse_args()
    if args.project:
        root = Path(args.project)
        project = Project.find(root) or Project.create(root, root.resolve().name)
    else:
        project = Project.find_up(Path.cwd())
    app = StepwiseApp(project)
    started = time.monotonic()
    app.run()
    if app.project:
        app.project.log("quit", stage=app.current, minutes=round((time.monotonic() - started) / 60, 1))
