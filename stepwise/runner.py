"""Runs the user's app or tests with their own command, shows the output, and branches on
whether it worked: a failed run asks the user to explain the error before running again."""

import asyncio
import os
import signal
import subprocess
import sys
import time

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label, RichLog, Static

from .answer import AnswerArea
from .stages import RUN_FAILED, TESTS_FAILED
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
    """`kind` is "app" (stage 6) or "tests" (stage 9)."""

    def __init__(self, project: Project, kind: str):
        super().__init__(classes="run-panel")
        self.project = project
        self.kind = kind
        self.command = project.answer("run.command" if kind == "app" else "tests.command").strip()
        self.process: asyncio.subprocess.Process | None = None
        self.stopped = False

    def compose(self) -> ComposeResult:
        if not self.command:
            what = "Your app runs" if self.kind == "app" else "Your tests run"
            yield Static(f"{what} here once you've typed {'its' if self.kind == 'app' else 'their'} command "
                         "on the previous page.", classes="waiting-note")
        with Vertical(classes="panel-body" + ("" if self.command else " waiting")):
            yield Static(f"$ {self.command or '…'}", classes="command", markup=False)
            yield Static(f"Runs in {self.project.root}", classes="hint", markup=False)
            with Horizontal(classes="run-buttons"):
                yield Button("Run it" if self.kind == "app" else "Run the tests", id="run", variant="primary",
                             disabled=not self.command)
                yield Button("Stop", id="stop", disabled=True)
            yield RichLog(id="output", max_lines=2000, wrap=True)
            yield Static(id="run-status")
            yield Vertical(id="branch")

    async def on_mount(self) -> None:
        if outcome := self.project.outcome(self.kind):
            await self.show_outcome(outcome)

    async def on_unmount(self) -> None:
        self.kill()

    # --- running ---------------------------------------------------------

    @on(Button.Pressed, "#run")
    def start(self) -> None:
        if self.process or not self.command:  # an empty command exits 0, which would look like a clean run
            return
        n = self.project.failures(self.kind)
        if self.project.outcome(self.kind) == "failed" and not self.project.answer(f"{self.kind}.attempt{n}"):
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

    async def run_command(self) -> None:
        if not self.command:
            return
        log = self.query_one("#output", RichLog)
        log.clear()
        await self.query_one("#branch").remove_children()
        self.query_one("#run", Button).disabled = True
        self.query_one("#stop", Button).disabled = False
        self.query_one("#run-status", Static).update("[dim]Running…[/]")
        self.stopped = False
        output: list[str] = []
        started = time.monotonic()
        env = run_env()
        group =({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if sys.platform == "win32"
                 else {"start_new_session": True})
        self.process = await asyncio.create_subprocess_shell(
            self.command, cwd=self.project.root, env=env,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, **group)
        async for raw in self.process.stdout:
            line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            output.append(line)
            log.write(line)
        code = await self.process.wait()
        self.process = None
        seconds = round(time.monotonic() - started, 1)
        outcome = outcome_of(code, self.stopped, seconds, "\n".join(output))

        self.project.set(f"{self.kind}_outcome", outcome)
        if outcome == "failed":
            n = self.project.failures(self.kind) + 1
            self.project.set(f"{self.kind}_failures", str(n))
            self.project.set_answer(f"{self.kind}.attempt{n}.error", "\n".join(output[-15:]))
        self.project.log("run", kind=self.kind, command=self.command, outcome=outcome, code=code,
                         seconds=seconds, stopped=self.stopped)
        self.query_one("#run", Button).disabled = False
        self.query_one("#stop", Button).disabled = True
        await self.show_outcome(outcome)
        self.app.refresh_sidebar()
        self.app.schedule_preview()

    # --- branching on the result ---------------------------------------

    async def show_outcome(self, outcome: str) -> None:
        status = self.query_one("#run-status", Static)
        branch = self.query_one("#branch")
        await branch.remove_children()
        self.query_one("#run", Button).label = (
            "Run again" if outcome else "Run it" if self.kind == "app" else "Run the tests")
        if outcome == "ok":
            status.update("[green]✓ It ran.[/] Press Next when you're ready." if self.kind == "app"
                          else "[green]✓ All the tests passed.[/] Press Next when you're ready.")
        elif outcome == "not_found":
            program = self.command.split()[0] if self.command else "that command"
            status.update(f"[yellow]Your terminal didn't recognise “{program}”.[/] Check it's spelled right and "
                          "installed. You named your tools back in stage 4.")
        elif outcome == "failed":
            n = self.project.failures(self.kind)
            status.update("[red]✗ It didn't work.[/]")
            await branch.mount(
                Label(RUN_FAILED if self.kind == "app" else TESTS_FAILED, classes="question"),
                AnswerArea(f"{self.kind}.attempt{n}", self.project.answer(f"{self.kind}.attempt{n}")),
                Static("Fix it in your editor, save, then press Run again.", classes="hint"),
            )
