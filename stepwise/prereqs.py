"""Checks the prerequisites the user listed in stage 4: that the language runs, that each
library is installed, and that the imports in their code match the list."""

import ast
import re
import sys
from dataclasses import dataclass

from rich.markup import escape
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from .runner import run_capture
from .store import Project

# The first word of a prerequisite line that names a language, and how to ask it for its version.
RUNTIMES = {
    "python": "python --version", "node": "node --version", "java": "java -version", "go": "go version",
    "ruby": "ruby --version", "dotnet": "dotnet --version", "php": "php --version", "rust": "rustc --version",
    "deno": "deno --version", "bun": "bun --version",
}
IMPORT_NAME = re.compile(r"^[A-Za-z_]\w*(\.[A-Za-z_]\w*)*$")


@dataclass
class Finding:
    ok: bool | None  # True passed, False blocks moving on, None is a heads-up that doesn't
    text: str


def split(project: Project) -> tuple[list[str], list[str]]:
    """Prerequisites as (languages, import names)."""
    runtimes, imports = [], []
    for name, _ in project.prereqs():
        first = name.split()[0].lower() if name.split() else ""
        (runtimes if first in RUNTIMES else imports).append(first if first in RUNTIMES else name)
    return runtimes, imports


def scan_imports(project: Project) -> tuple[dict[str, list[str]], list[str]]:
    """Third-party modules imported by the user's Python files, as {module: [files]}, plus notes
    about files that couldn't be read. The standard library and the user's own modules are left out."""
    names = [name for name, _ in project.files()] + [project.answer("tests.file").strip()]
    local = {p.stem for p in project.root.glob("*.py")}
    local |= {d.name for d in project.root.iterdir() if d.is_dir() and (d / "__init__.py").exists()}
    found: dict[str, list[str]] = {}
    notes = []
    for name in names:
        path = project.code_path(name)
        if not name.endswith(".py") or path is None or not path.is_file():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as e:
            notes.append(f"Couldn't read the imports in {name}: line {e.lineno} has a syntax error.")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules = [node.module]
            else:
                continue
            for module in modules:
                top = module.split(".")[0]
                if top not in sys.stdlib_module_names and top not in local and top != "__future__":
                    found.setdefault(top, [])
                    if name not in found[top]:
                        found[top].append(name)
    return found, notes


async def check(project: Project) -> list[Finding]:
    findings = []
    runtimes, imports = split(project)
    for runtime in runtimes:
        code, out = await run_capture(RUNTIMES[runtime], project.root)
        first = out.splitlines()[0] if out else ""
        findings.append(Finding(True, f"{runtime}: {first}") if code == 0 else
                        Finding(False, f"{runtime} didn't run ({first or 'no output'}). Is it installed, and can "
                                       "your terminal find it?"))
    is_python = "python" in runtimes or any(name.endswith(".py") for name, _ in project.files())
    if not runtimes:
        findings.append(Finding(None, "Stepwise didn't recognise a language in your list, so it can't check "
                                      "its version. Start the list with one, like Python 3.14."))
    if not is_python:
        if imports:
            findings.append(Finding(None, "Stepwise can only check libraries for Python apps, so check these "
                                          "yourself: " + ", ".join(imports) + "."))
        return findings

    bad = [n for n in imports if not IMPORT_NAME.match(n)]
    findings += [Finding(False, f"“{n}” isn't a name you could import. Use the name from your import line, "
                                "like PySide6.") for n in bad]
    tops = sorted({n.split(".")[0] for n in imports if IMPORT_NAME.match(n)})
    if tops:
        command = f'python -c "import importlib.util as u; print(*[n for n in {tops!r} if u.find_spec(n) is None])"'
        code, out = await run_capture(command, project.root)
        if code != 0:
            findings.append(Finding(False, f"Stepwise couldn't run python to check your libraries: {out[-200:]}"))
        else:
            missing = set(out.split())
            findings += [Finding(False, f"{n} isn't installed. Follow your setup steps from stage 4, then check "
                                        "again.") if n in missing else Finding(True, f"{n} is installed")
                         for n in tops]

    found, notes = scan_imports(project)
    declared = {n.lower() for n in tops}
    used = {m.lower() for m in found}
    findings += [Finding(False, f"Your code imports {module} (in {', '.join(files)}), but it isn't in your "
                                "prerequisites. Add it in stage 4.")
                 for module, files in sorted(found.items()) if module.lower() not in declared]
    findings += [Finding(None, f"You listed {n}, but your code doesn't import it. Remove it if you don't use it "
                               "any more, so your README stays right.")
                 for n in tops if n.lower() not in used]
    findings += [Finding(None, note) for note in notes]
    return findings


class CheckPanel(Vertical):
    def __init__(self, project: Project):
        super().__init__(classes="check-panel")
        self.project = project

    def compose(self) -> ComposeResult:
        yield Static("Before running your app, Stepwise checks your prerequisites from your project folder, "
                     "using the same terminal setup it runs your app with.", classes="intro")
        with Horizontal(classes="run-buttons"):
            yield Button("Check again", id="check", variant="primary")
            yield Button("Edit prerequisites", id="edit-prereqs")
        yield Static(id="check-results")

    def on_mount(self) -> None:
        if self.project.items("prereqs"):
            self.run_worker(self.run_check(), exclusive=True, group="check")
        else:
            self.query_one("#check-results", Static).update(
                "[yellow]You haven't listed any prerequisites yet.[/] Press Edit prerequisites to add them.")

    @on(Button.Pressed, "#check")
    def check_again(self) -> None:
        self.run_worker(self.run_check(), exclusive=True, group="check")

    @on(Button.Pressed, "#edit-prereqs")
    async def edit(self) -> None:
        await self.app.go_to_list("prereqs")

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
