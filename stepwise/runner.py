"""Runs the user's app or tests with their own command, shows the output, passes on what the user
types, and branches on whether it worked: a failed run shows where the error points and what it
means, and asks the user to explain it before running again."""

import asyncio
import codecs
import os
import signal
import subprocess
import sys
import time
from urllib.parse import quote_plus

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Input, Label, RichLog, Static

from .answer import AnswerArea
from .errors import Help, explain, search_text
from .languages import language_of
from .stages import RUN_FAILED, SEARCH_URL, TESTS_FAILED
from .store import Project

NOT_FOUND_CODES = {9009, 127}  # cmd.exe and POSIX shells: "command not found"
# cmd.exe launched by Python exits 1, not 9009, for an unknown command, so its message is checked too.
NOT_FOUND_MARKERS = ("is not recognized as an internal or external command", "command not found")
STARTED_OK_AFTER = 2.0  # seconds; a window or server app stopped after this, without errors, ran fine
ERROR_MARKERS = ("Traceback (most recent call last)", "Error:", "error:")


def run_env() -> dict[str, str]:
    # Unbuffered so a Python app's prints show up as they happen, not when it exits.
    return {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}


async def run_capture(command: str, cwd, timeout: float = 30) -> tuple[int, str]:
    """Runs a short command the way a run would, and returns its exit code and output."""
    process = await asyncio.create_subprocess_shell(
        command, cwd=cwd, env=run_env(), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    try:
        out, _ = await asyncio.wait_for(process.communicate(), timeout)
    except asyncio.TimeoutError:
        process.kill()
        return -1, "(timed out)"
    return process.returncode, out.decode("utf-8", errors="replace").strip()


def outcome_of(code: int, stopped: bool, seconds: float, output: str) -> str:
    if stopped:
        clean = seconds >= STARTED_OK_AFTER and not any(m in output for m in ERROR_MARKERS)
        return "ok" if clean else "failed"
    if code == 0:
        return "ok"
    if code in NOT_FOUND_CODES or any(m in output[:500] for m in NOT_FOUND_MARKERS):
        return "not_found"
    return "failed"


class RunPanel(Vertical):
    """`kind` is "app" (stage 6) or "tests" (stage 9). On stage 5's pages `step` is the step being built:
    those runs are try-outs, so they show the output and what went wrong, but they aren't the app's
    recorded run and a failure doesn't have to be explained before running again."""

    def __init__(self, project: Project, kind: str, step: int = 0):
        super().__init__(classes="run-panel" + (" trial" if step else ""))
        self.project = project
        self.kind = kind
        self.step = step
        self.command = project.answer("run.command" if kind == "app" else "tests.command").strip()
        self.process: asyncio.subprocess.Process | None = None
        self.stopped = False
        self.output: list[str] = []
        self.partial = ""  # the last line printed so far, with no newline yet: often a prompt
        self.help: Help | None = None

    def compose(self) -> ComposeResult:
        if not self.command:
            what = "Your app runs" if self.kind == "app" else "Your tests run"
            where = "in stage 4" if self.kind == "app" else "on the previous page"
            yield Static(f"{what} here once you've typed {'its' if self.kind == 'app' else 'their'} command "
                         f"{where}.", classes="waiting-note")
        with Vertical(classes="panel-body" + ("" if self.command else " waiting")):
            yield Static(f"$ {self.command or '…'}", classes="command", markup=False)
            yield Static(f"Runs in {self.project.root}", classes="hint", markup=False)
            with Horizontal(classes="run-buttons"):
                yield Button(self.run_label(""), id="run", variant="primary", disabled=not self.command)
                yield Button("Stop", id="stop", disabled=True)
            yield RichLog(id="output", max_lines=2000, wrap=True)
            yield Static(id="partial", markup=False)
            yield Input(placeholder="Your app is waiting? Type here and press Enter to send it", id="send")
            yield Static(id="run-status")
            yield Vertical(id="branch")

    def run_label(self, outcome: str) -> str:
        if outcome:
            return "Run again"
        return "Run the tests" if self.kind == "tests" else "Run it"

    async def on_mount(self) -> None:
        self.query_one("#partial").display = False
        self.query_one("#send").display = False
        if not self.step and (outcome := self.project.outcome(self.kind)):
            await self.show_outcome(outcome)

    async def on_unmount(self) -> None:
        self.kill()

    # --- running ---------------------------------------------------------

    @on(Button.Pressed, "#run")
    def start(self) -> None:
        if self.process or not self.command:  # an empty command exits 0, which would look like a clean run
            return
        n = self.project.failures(self.kind)
        if (not self.step and self.project.outcome(self.kind) == "failed"
                and not self.project.answer(f"{self.kind}.attempt{n}")):
            self.app.save_all()
            if not self.project.answer(f"{self.kind}.attempt{n}"):
                self.app.notify("First, say in your own words what went wrong. Then run it again.",
                                severity="warning", timeout=6)
                return
        self.run_worker(self.run_command(), exclusive=True, group="run")

    @on(Button.Pressed, "#stop")
    def stop(self) -> None:
        self.stopped = True
        self.kill()

    def kill(self) -> None:
        if not self.process or self.process.returncode is not None:
            return
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.process.pid)], capture_output=True)
        else:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except ProcessLookupError:
                pass

    def set_running(self, running: bool) -> None:
        self.query_one("#run", Button).disabled = running
        self.query_one("#stop", Button).disabled = not running
        send = self.query_one("#send", Input)
        send.display = running
        if running:
            send.focus()

    async def run_command(self) -> None:
        if not self.command:
            return
        self.query_one("#output", RichLog).clear()
        await self.query_one("#branch").remove_children()
        self.set_running(True)
        self.query_one("#run-status", Static).update("[dim]Running…[/]")
        self.stopped = False
        self.output, self.partial = [], ""
        started = time.monotonic()
        group =({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if sys.platform == "win32"
                 else {"start_new_session": True})
        self.process = await asyncio.create_subprocess_shell(
            self.command, cwd=self.project.root, env=run_env(), stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, **group)
        # Read what's there, not whole lines: a prompt like "Total: " has no newline until it's answered.
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        while chunk := await self.process.stdout.read(4096):
            self.show_output(decoder.decode(chunk))
        self.show_output(decoder.decode(b"", final=True))
        if self.partial:
            self.show_output("\n")
        code = await self.process.wait()
        self.process = None
        self.set_running(False)
        seconds = round(time.monotonic() - started, 1)
        output = "\n".join(self.output)
        outcome = outcome_of(code, self.stopped, seconds, output)
        self.help = explain(output, self.project) if outcome == "failed" else None

        if self.step:
            self.project.log("run", kind="step", step=self.step, command=self.command, outcome=outcome, code=code,
                             seconds=seconds, stopped=self.stopped)
        else:
            self.project.set(f"{self.kind}_outcome", outcome)
            if outcome == "failed":
                n = self.project.failures(self.kind) + 1
                self.project.set(f"{self.kind}_failures", str(n))
                self.project.set_answer(f"{self.kind}.attempt{n}.error", "\n".join(self.output[-15:]))
            self.project.log("run", kind=self.kind, command=self.command, outcome=outcome, code=code,
                             seconds=seconds, stopped=self.stopped)
        if self.help:
            self.project.log("error_help", kind=self.help.kind, error=self.help.message[:120],
                             file=self.help.path.name if self.help.path else None, line=self.help.line or None)
        await self.show_outcome(outcome)
        self.app.refresh_sidebar()
        self.app.schedule_preview()

    def show_output(self, text: str) -> None:
        """Writes each finished line to the log, and shows the unfinished last one under it."""
        *lines, self.partial = (self.partial + text).split("\n")
        for line in lines:
            self.write_line(line.rstrip("\r"))
        partial = self.query_one("#partial", Static)
        partial.update(self.partial)
        partial.display = bool(self.partial)

    def write_line(self, line: str, typed: str | None = None) -> None:
        self.output.append(line if typed is None else line + typed)
        log = self.query_one("#output", RichLog)
        if typed is None:
            log.write(line)
        else:  # what the user typed, in the accent colour so it stands apart from what the app printed
            log.write(Text.assemble(line, (typed, self.app.current_theme.accent or "reverse")))

    @on(Input.Submitted, "#send")
    async def send(self, event: Input.Submitted) -> None:
        """Sends one line to the running app, as if typed into its terminal."""
        event.stop()
        process = self.process
        if not process or process.returncode is not None or process.stdin is None:
            return
        typed, event.input.value = event.value, ""
        self.write_line(self.partial, typed)  # a terminal shows the prompt and the answer on one line
        self.partial = ""
        self.query_one("#partial").display = False
        try:
            process.stdin.write((typed + "\n").encode("utf-8"))
            await process.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            pass  # the app finished before reading it
        self.project.log("run_input", kind="step" if self.step else self.kind)

    # --- branching on the result ---------------------------------------

    async def show_outcome(self, outcome: str) -> None:
        status = self.query_one("#run-status", Static)
        branch = self.query_one("#branch")
        await branch.remove_children()
        self.query_one("#run", Button).label = self.run_label(outcome)
        if outcome == "ok":
            next_hint = "" if self.step else " Press Next when you're ready."
            status.update(("[green]✓ It ran.[/]" if self.kind == "app" else "[green]✓ All the tests passed.[/]")
                          + next_hint)
        elif outcome == "not_found":
            program = self.command.split()[0] if self.command else "that command"
            status.update(f"[yellow]Your terminal didn't recognise “{program}”.[/] Check it's spelled right and "
                          "installed. You named your tools back in stage 4.")
        elif outcome == "failed":
            status.update("[red]✗ It didn't work.[/]")
            if self.help is None and not self.step:  # reopened after a failed run: its error was saved
                self.help = explain(self.project.answer(f"{self.kind}.attempt{self.project.failures(self.kind)}.error"),
                                    self.project)
            await branch.mount_all(self.help_widgets())
            if self.step:
                await branch.mount(Static("Fix it in your editor, save, then press Run again. Still stuck? Say what "
                                          "you expected and what happened in the box at the bottom.", classes="hint"))
            else:
                n = self.project.failures(self.kind)
                await branch.mount(
                    Label(RUN_FAILED if self.kind == "app" else TESTS_FAILED, classes="question"),
                    AnswerArea(f"{self.kind}.attempt{n}", self.project.answer(f"{self.kind}.attempt{n}")),
                    Static("Fix it in your editor, save, then press Run again.", classes="hint"),
                )

    def help_widgets(self) -> list[Widget]:
        """Where the error points in the user's code and what that kind of error means. Not the fix."""
        found = self.help
        if not found:
            return []
        title = "The error" if found.recognised else "The last thing it printed"
        widgets: list[Widget] = [Label(title, classes="minor"), Static(found.message, classes="quote", markup=False)]
        if found.path:
            name = found.path.relative_to(self.project.root).as_posix()
            steps = [str(n) for n in range(1, len(self.project.steps()) + 1)
                     if self.project.code_path(self.project.step_file(n)) == found.path]
            held = (f", the file for step {steps[0]}" if len(steps) == 1 else
                    f", the file for steps {', '.join(steps[:-1])} and {steps[-1]}" if steps else "")
            widgets += [Label(f"It points at line {found.line} of {name}{held}:", classes="minor"),
                        Static(f"{found.line} │ {found.code}", classes="quote", markup=False)]
        if found.meaning:
            widgets.append(Static(found.meaning, classes="hint"))
        widgets.append(Button("Search for this error", id="search-error"))
        return widgets

    @on(Button.Pressed, "#search-error")
    def search_error(self) -> None:
        if not self.help:
            return
        lang = language_of(self.help.path.name) if self.help.path else None
        url = SEARCH_URL + quote_plus(search_text(self.help, lang.name if lang else ""))
        self.project.log("error_search", kind=self.help.kind)
        self.app.open_url(url)
