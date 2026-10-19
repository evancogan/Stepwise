"""Checks an app's prerequisites against its real dependency file (requirements.txt,
package.json, go.mod, Cargo.toml, pom.xml or build.gradle, *.csproj): that the language runs,
that every library the code imports is listed and installed, and that nothing built in or
part of another library is listed as if it needed installing."""

import re
import shutil
import subprocess
from dataclasses import dataclass

from rich.markup import escape
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label, Static, TextArea

from .languages import Import, Language, code_files, detect, saved_date
from .runner import run_capture
from .store import Project

LIVE_CAPABLE = {"python", "javascript", "go"}  # languages whose installed tool can list its own built-ins


@dataclass
class Finding:
    ok: bool | None  # True passed, False blocks moving on, None is a heads-up that doesn't
    text: str


def version_numbers(text: str) -> list[str]:
    return re.findall(r"\d+", text)


def dependency_file(project: Project, lang: Language) -> tuple[str, list[str] | None, str]:
    """(file name, the names it lists or None if it can't be read, the problem if any)."""
    path = lang.dep_path(project)
    if path is None:
        return lang.dep_files[0], None, f"There's no {lang.dep_files[0]} yet."
    try:
        return path.name, lang.read_deps(path), ""
    except Exception as e:  # each format fails differently (JSON, TOML, XML); the message is shown as-is
        return path.name, None, f"Stepwise couldn't read {path.name}: {e}"


async def check(project: Project) -> list[Finding]:
    languages = detect(project)
    if not languages:
        return [Finding(None, "Stepwise doesn't recognise the language of your files, so it can't check what "
                              "they need. Check the Prerequisites in your README by hand.")]
    findings = []
    for lang in languages:
        findings += await check_language(project, lang)
    return findings


async def check_language(project: Project, lang: Language) -> list[Finding]:
    async def run(command: str) -> tuple[int, str]:
        return await run_capture(command, project.root)

    findings = []
    included = lang.comes_with.removeprefix("comes with ").removeprefix("is part of ")

    # The language itself, and the version the user said the app needs.
    code, out = await run(lang.version_command)
    first = out.splitlines()[0] if out else ""
    if code != 0:
        findings.append(Finding(False, f"{lang.tool} didn't run ({first or 'no output'}). Is it installed, and can "
                                       "your terminal find it?"))
    else:
        findings.append(Finding(True, f"{lang.tool}: {first}"))
        wanted, have = version_numbers(project.answer("lang.version")), version_numbers(first)
        if wanted and have and have[:len(wanted)] != wanted:
            findings.append(Finding(None, f"You said your app needs {lang.tool} {'.'.join(wanted)}, but this "
                                          f"computer has {'.'.join(have)}. Check that's what you meant."))

    builtins = await lang.builtins(run)
    if builtins.live:
        findings.append(Finding(True, f"Knows what {included} includes, from your installed {lang.tool}."))
    else:
        tip = f" Install {lang.tool} for an exact list." if lang.key in LIVE_CAPABLE else ""
        findings.append(Finding(None, f"Using Stepwise's saved list of what {included} includes "
                                      f"(fetched {saved_date()}).{tip}"))

    file_name, deps, problem = dependency_file(project, lang)
    if deps is None:
        findings.append(Finding(False, f"{problem} Press Edit dependency file to fix it."))

    imports, notes = [], []
    for name in code_files(project, lang):
        path = project.code_path(name)
        if path is None or not path.is_file():
            continue
        try:
            imports += lang.scan(path.read_text(encoding="utf-8", errors="replace"), name)
        except SyntaxError as e:
            notes.append(f"Couldn't read the imports in {name}: line {e.lineno} has a syntax error.")
    deps_path = lang.dep_path(project)
    parts = {i.name: i.part_of for i in imports if i.part_of}
    libraries = [i for i in imports if not i.part_of
                 and not lang.is_builtin(i.name, builtins) and not lang.is_local(i, project, deps_path)]

    if deps is not None:
        severity = False if lang.reliable_match else None
        real_deps = []
        for dep in deps:
            if dep in parts:
                findings.append(Finding(False, f"{dep} is part of {parts[dep]} (your code says from {parts[dep]} "
                                               f"import {dep}), so it doesn't go in {file_name}. {parts[dep]} does."))
            elif lang.is_builtin(dep, builtins):
                findings.append(Finding(severity, f"{dep} {lang.comes_with}, so it doesn't go in {file_name}. "
                                                  "You can remove it."))
            else:
                real_deps.append(dep)

        by_package: dict[str, list[Import]] = {}
        for imp in libraries:
            by_package.setdefault(lang.top(imp.name), []).append(imp)
        for package, uses in sorted(by_package.items()):
            if not any(lang.matches(uses[0], dep, builtins) for dep in real_deps):
                files = ", ".join(sorted({i.file for i in uses}))
                findings.append(Finding(severity, f"Your code imports {package} (in {files}), but {file_name} "
                                                  "doesn't list it. Add it by the name you'd install it with."))
        for dep in real_deps:
            if not dep.startswith("@types/") and not any(lang.matches(i, dep, builtins) for i in libraries):
                findings.append(Finding(None, f"{file_name} lists {dep}, but your code doesn't import it. Remove "
                                              "it if you don't use it any more."))

        install = lang.install_hint.format(file=file_name)
        unknown = []
        for dep in real_deps:
            state = lang.installed(dep, project, builtins)
            if state is None:
                unknown.append(dep)
            else:
                findings.append(Finding(True, f"{dep} is installed") if state else
                                Finding(False, f"{dep} is in {file_name} but isn't installed. {install}"))
        if unknown:
            findings.append(Finding(None, f"Stepwise can't check whether {', '.join(unknown)} "
                                          f"{'is' if len(unknown) == 1 else 'are'} installed. {install}"))
    findings += [Finding(None, note) for note in notes]
    return findings


class CheckPanel(Vertical):
    def __init__(self, project: Project):
        super().__init__(classes="check-panel")
        self.project = project
        self.ready = bool(project.files())  # what to check comes from the files listed in stage 4

    def compose(self) -> ComposeResult:
        if not self.ready:
            yield Static("Stepwise checks your prerequisites once you've listed your files in stage 4.",
                         classes="waiting-note")
        with Vertical(classes="panel-body" + ("" if self.ready else " waiting")):
            yield Static("Before running your app, Stepwise checks your prerequisites from your project folder, "
                         "using the same terminal setup it runs your app with.", classes="intro")
            with Horizontal(classes="run-buttons"):
                yield Button("Check again", id="check", variant="primary", disabled=not self.ready)
                yield Button("Edit dependency file", id="edit-deps", disabled=not self.ready)
            yield Static(id="check-results")

    def on_mount(self) -> None:
        if self.ready:
            self.run_worker(self.run_check(), exclusive=True, group="check")

    @on(Button.Pressed, "#check")
    def check_again(self) -> None:
        if self.ready:
            self.run_worker(self.run_check(), exclusive=True, group="check")

    @on(Button.Pressed, "#edit-deps")
    async def edit(self) -> None:
        await self.app.go_to_page(4, "deps")

    async def run_check(self) -> None:
        results = self.query_one("#check-results", Static)
        results.update("[dim]Checking…[/]")
        findings = await check(self.project)
        passed = bool(findings) and all(f.ok is not False for f in findings)
        self.project.set("prereq_check", "ok" if passed else "failed")
        self.project.log("prereq_check", passed=passed, findings=[f.text for f in findings if f.ok is not True])
        marks = {True: "[green]✓[/]", False: "[red]✗[/]", None: "[yellow]•[/]"}
        lines = [f"{marks[f.ok]} {escape(f.text)}" for f in findings]
        lines.append("")
        lines.append("[green]Everything's in place. Press Next to run your app.[/]" if passed
                     else "[red]Fix the ✗ items, then press Check again.[/]")
        results.update("\n".join(lines))
        self.app.refresh_sidebar()


class DependencyPanel(Vertical):
    """Stage 4: the dependency file for each language the app's files are written in."""

    def __init__(self, project: Project):
        super().__init__(classes="deps-panel")
        self.project = project
        self.languages = detect(project)
        self._seen: dict[str, float] = {}
        for lang in self.languages:
            if lang.dep_path(project) is None:
                lang.new_dep_path(project).write_text(lang.starter(project), encoding="utf-8", newline="\n")
                project.log("deps_created", file=lang.new_dep_path(project).name)

    def compose(self) -> ComposeResult:
        if not self.project.files():
            yield Static("Your dependency file appears here once you've listed your files.", classes="waiting-note")
            yield Static("requirements.txt, package.json, go.mod…\n\nThe file, live as you save it\n"
                         "Stepwise reads: …", classes="waiting sample", markup=False)
            return
        if not self.languages:
            yield Static("Stepwise doesn't recognise the language of the files you listed, so it can't make a "
                         "dependency file for you. List the libraries your app needs under Prerequisites in your "
                         "README instead.", classes="intro")
            return
        for lang in self.languages:
            path = lang.dep_path(self.project)
            yield Label(f"{lang.name}: {path.name}", classes="question")
            yield Static(f"Real projects list what has to be installed in a dependency file. For {lang.name} "
                         f"that's {path.name}. {lang.dep_example} Only list what you installed yourself: things "
                         "that come with the language, and parts of a library, don't go in.",
                         classes="intro", markup=False)
            with Horizontal(classes="file-bar"):
                if shutil.which("code"):
                    yield Button("Open in VS Code", id=f"open-{lang.key}", classes="open-deps")
                yield Static(id=f"deps-status-{lang.key}")
            yield TextArea("", read_only=True, soft_wrap=False, show_line_numbers=True,
                           id=f"deps-view-{lang.key}", classes="deps-view")

    def on_mount(self) -> None:
        self.refresh_files()
        self.set_interval(1.0, self.refresh_files)

    def refresh_files(self) -> None:
        for lang in self.languages:
            path = lang.dep_path(self.project)
            status = self.query_one(f"#deps-status-{lang.key}", Static)
            if path is None:
                status.update(f"[yellow]Can't find {lang.dep_files[0]}.[/]")
                continue
            mtime = path.stat().st_mtime
            if self._seen.get(lang.key) != mtime:
                self._seen[lang.key] = mtime
                self.query_one(f"#deps-view-{lang.key}", TextArea).load_text(
                    path.read_text(encoding="utf-8", errors="replace"))
                self.app.schedule_preview()  # the file is edited outside Stepwise, so nothing else would
            _, deps, problem = dependency_file(self.project, lang)
            if deps is None:
                status.update(f"[red]{escape(problem)}[/]")
            elif deps:
                status.update("Stepwise reads: " + escape(", ".join(deps)))
            else:
                status.update("[dim]No libraries listed yet. That's fine if your app doesn't install any.[/]")

    @on(Button.Pressed, ".open-deps")
    def open_file(self, event: Button.Pressed) -> None:
        lang = next(l for l in self.languages if event.button.id == f"open-{l.key}")
        code, path = shutil.which("code"), lang.dep_path(self.project)
        if code and path:
            self.project.log("deps_open", file=path.name)
            subprocess.Popen([code, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def deps_missing(project: Project) -> str:
    """What's wrong with the dependency files, for the stage 4 page gate."""
    for lang in detect(project):
        _, deps, problem = dependency_file(project, lang)
        if deps is None:
            return problem
    return ""
