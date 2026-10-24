"""Mock users for testing Stepwise: a language model plays a persona and fills Stepwise in, page by
page, through the real app.

This is test tooling only. Stepwise itself never uses AI; nothing in the stepwise package imports
this, and it isn't installed with it.

Both ways of running it use Pilot (Textual's headless test driver) to run the real StepwiseApp, and
put answers in the way a user would: typing into the box, picking an option with Enter, adding list
items one at a time, editing files on disk. Projects go in their own folder (~/Stepwise-mock by
default), never ~/Stepwise, and each one's usage log starts with a "mock" event so test data can't
be mistaken for real use.

`run`: the harness drives. For each page it describes what's on screen to a local model, asks it to
answer as the persona, and presses Next. The model is reached over an OpenAI-compatible chat API:
LM Studio / Bionic serves one at http://127.0.0.1:1235/v1/chat/completions, Ollama at
http://localhost:11434/v1/chat/completions.

    python tools/mock_user.py run --persona maya
    python tools/mock_user.py run --persona all --stages 1-4 --shots

Turns: an agent drives (the mock-user agent in .claude/agents). Each command opens the project
where the agent left off, does one thing, and prints the page as Stepwise shows it, in Stepwise's
own words, so the agent reads the app rather than a description of it.

    python tools/mock_user.py start --persona maya --fresh
    python tools/mock_user.py pick 2 --persona maya --why "I only use a laptop"
    python tools/mock_user.py type --persona maya <<'EOF'
    It splits a restaurant bill between friends.
    EOF
    python tools/mock_user.py next --persona maya
"""

import argparse
import asyncio
import json
import re
import shutil
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import stepwise.app as stepwise_app  # noqa: E402
from stepwise import choices  # noqa: E402
from stepwise.answer import AnswerArea, AnswerChoice, AnswerLine  # noqa: E402
from stepwise.languages import detect  # noqa: E402
from stepwise.pages import Page, page_missing, pages  # noqa: E402
from stepwise.prereqs import check_state  # noqa: E402
from stepwise.stages import INTROS, PSEUDO_WORDS, QUESTION, TITLES  # noqa: E402
from stepwise.store import Project, slugify  # noqa: E402
from textual.widgets import Button, Input, OptionList, Static, TextArea  # noqa: E402

URL = "http://127.0.0.1:1235/v1/chat/completions"
MODEL = "qwen3.6-35b-a3b-rotorquant"
HOME = Path.home() / "Stepwise-mock"
PERSONAS = Path(__file__).with_name("personas.json")

SYSTEM = """\
You are {name}, a real person using Stepwise, a coaching app that walks you through building your own \
app one stage at a time. Stepwise asks the questions and you answer them yourself. It never writes \
code for you, and you haven't written any code yet.

Who you are: {about}
The app you want to build, called {app_name}: {app}
How you write: {style}

Stay in character as {name} the whole time. Answer only what the page asks, the way you'd type it into \
the box: no preamble, no repeating the question, no Markdown headings, and never mention being an AI or \
a persona. Keep your answers consistent with what you've already written, which is shown with each \
question. If you don't know something, say so the way {name} would, or pick "Not sure yet" where it's \
offered."""

CHOICE_FORMAT = ("Reply with the number of the option you pick on the first line, then one short sentence, "
                 "in character, on why you picked it.")
LIST_FORMAT = {
    "resources": "List 2 or 3 web pages you found while researching, one full URL per line, nothing else.",
    "steps": "List your steps, one per line, in the order you'd build them. No numbers or bullets.",
    "files": "List your files, one per line, as the file name, a colon, and what it's for. No bullets.",
}


def ask(args, persona: dict, prompt: str, max_tokens: int | None = None) -> tuple[str, str, float]:
    """(answer, the model's reasoning, seconds) for one page."""
    body = {"model": args.model, "temperature": args.temperature,
            "max_tokens": max_tokens or args.max_tokens,
            "messages": [{"role": "system", "content": SYSTEM.format(**persona)},
                         {"role": "user", "content": prompt}]}
    if args.no_think:
        body["reasoning_effort"] = "none"
    request = urllib.request.Request(args.url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=args.timeout) as response:
        message = json.loads(response.read())["choices"][0]["message"]
    content = message.get("content") or ""
    reasoning = message.get("reasoning_content") or ""
    # Some servers leave the thinking inline instead of in reasoning_content.
    if m := re.match(r"\s*<think>(.*?)</think>\s*", content, re.S):
        reasoning, content = reasoning or m.group(1), content[m.end():]
    return content.strip(), reasoning.strip(), time.monotonic() - started


def context(project: Project) -> str:
    """What the persona has written so far, short enough to send with every page."""
    def cut(text: str, n: int = 220) -> str:
        text = " ".join(text.split())
        return text if len(text) <= n else text[:n - 1] + "…"

    lines = []
    if intent := project.answer("intent"):
        lines.append(f"- Your app, in a sentence: {cut(intent)}")
    for name, label in (("resources", "Links you found"), ("steps", "Your steps"), ("files", "Your files")):
        if items := project.items(name):
            lines.append(f"- {label}: " + "; ".join(cut(i, 80) for i in items))
    for n, step in enumerate(project.steps(), 1):
        if text := project.answer(f"pseudo{n}"):
            lines.append(f"- Pseudocode for step {n}: {cut(text, 160)}")
    for key, q in QUESTION.items():
        if text := project.answer(key):
            lines.append(f"- {cut(q.prompt, 70)} → {cut(choices.shown(key, text))}")
    return "\n".join(lines) or "(nothing yet)"


def page_prompt(project: Project, app, page: Page) -> str:
    stage = app.current
    parts = [f"Stepwise, stage {stage}: {TITLES[stage - 1]}."]
    if app.page == 0:
        parts.append(INTROS[stage])
    if page.note:
        parts.append(page.note)
    parts.append(f"The page asks: {page.prompt}" if page.prompt else "")
    if page.placeholder:
        parts.append(f"The box's placeholder says: {page.placeholder}")
    if page.key.startswith("pseudo") and page.key[6:].isdigit():
        parts.append(f"Write it as pseudocode, in plain sentences, one action per line, using these words for the "
                     f"structure: {PSEUDO_WORDS}. Indent what belongs inside an IF or REPEAT.")
    if page.line:
        parts.append("This box takes one line only.")
    parts.append(f"What you've written in Stepwise so far:\n{context(project)}")
    return "\n\n".join(p for p in parts if p)


class Run:
    def __init__(self, args, persona: dict):
        self.args, self.persona = args, persona
        root = args.home / slugify(persona["app_name"])
        if args.fresh and (root / ".stepwise" / "mock.jsonl").is_file():
            shutil.rmtree(root)  # only ever a folder this harness made
        self.project = Project.find(root) or Project.create(root, persona["app_name"])
        self.transcript = self.project.meta / "mock.jsonl"
        if not self.transcript.is_file():
            self.project.log("mock", persona=persona["key"], model=args.model, think=not args.no_think)
            self.transcript.touch()
        self.shots = root / ".stepwise" / "mock-shots"

    def record(self, page: Page, **data) -> None:
        entry = {"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "persona": self.persona["key"], "model": self.args.model,
                 "stage": self.app.current, "page": page.key or page.kind, "kind": page.kind, **data}
        with open(self.transcript, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        answer = str(data.get("answer", data.get("picked", data.get("note", ""))))
        print(f"  [{entry['stage']}] {page.label[:28]:<28} {data.get('seconds', 0):>5.0f}s  {answer[:90]!r}",
              flush=True)

    async def model(self, prompt: str, max_tokens: int | None = None) -> tuple[str, str, float]:
        return await asyncio.to_thread(ask, self.args, self.persona, prompt, max_tokens)

    async def fill(self, page: Page) -> None:
        app, project = self.app, self.project
        # A page that's already done is left alone, so a stopped run carries on where it was. The
        # dependency file counts as done as soon as it can be read, so it's always edited.
        if page.kind in ("info", "empty") or (page.kind not in ("deps", "check") and not page_missing(project, page)):
            return
        prompt = page_prompt(project, app, page)

        if page.kind == "choice":
            options = choices.options(page.key, project.answer)
            listing = "\n".join(f"{i}. {o.label}" + (f" ({' '.join(o.hint.split())})" if o.hint else "")
                                for i, o in enumerate(options, 1))
            reply, reasoning, seconds = await self.model(f"{prompt}\n\nOptions:\n{listing}\n\n{CHOICE_FORMAT}")
            m = re.search(r"\d+", reply)
            index = min(max(int(m.group()) - 1, 0), len(options) - 1) if m else 0
            widget = app.query_one("#stage AnswerChoice", AnswerChoice)
            widget.focus()
            widget.highlighted = index
            await self.pilot.press("enter")
            await self.pilot.pause(0.2)
            why = reply.split("\n", 1)[1].strip() if "\n" in reply else ""
            self.record(page, picked=options[index].key, label=options[index].label, why=why,
                        offered=[o.key for o in options], reasoning=reasoning, seconds=seconds)

        elif page.kind == "answer":
            reply, reasoning, seconds = await self.model(prompt)
            if page.line:
                reply = reply.strip().strip("`").splitlines()[0] if reply.strip() else ""
                app.query_one("#stage AnswerLine", AnswerLine).value = reply
            else:
                app.query_one("#stage AnswerArea", AnswerArea).load_text(reply)
            self.record(page, answer=reply, reasoning=reasoning, seconds=seconds)

        elif page.kind == "list":
            reply, reasoning, seconds = await self.model(f"{prompt}\n\n{LIST_FORMAT[page.key]}")
            items = [re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip() for line in reply.splitlines()]
            box = app.query_one("#stage #step-input")
            for item in [i for i in items if i][:12]:
                box.focus()
                box.value = item
                await self.pilot.press("enter")
                await self.pilot.pause(0.1)
            self.record(page, answer=items, reasoning=reasoning, seconds=seconds)

        elif page.kind == "deps":
            for lang in detect(project):
                path = lang.dep_path(project)
                if path is None:
                    continue
                reply, reasoning, seconds = await self.model(
                    f"{prompt}\n\nStepwise made your {path.name} for {lang.name}. It says: {lang.dep_example} Only "
                    f"list what you have to install yourself. Here it is now:\n\n{path.read_text(encoding='utf-8')}\n\n"
                    f"Reply with the whole file as you'd save it, and nothing else.")
                text = re.sub(r"^```\w*\n|```\s*$", "", reply.strip(), flags=re.M).strip() + "\n"
                path.write_text(text, encoding="utf-8", newline="\n")
                self.record(page, file=path.name, answer=text, reasoning=reasoning, seconds=seconds)

        elif page.kind == "check":
            state = check_state(page.key)
            for _ in range(240):  # the check runs the user's real tools, which can be slow the first time
                if project.get(state) in ("ok", "failed"):
                    break
                await self.pilot.pause(0.5)
            results = str(app.query_one("#check-results").render())
            self.record(page, note=project.get(state) or "didn't finish", findings=results)

        elif page.kind == "readme":
            panel = app.query_one(stepwise_app.ReadmePanel)
            panel.build()
            target = project.readme_draft if project.readme_is_original() else project.readme
            reply, reasoning, seconds = await self.model(
                f"{prompt}\n\nStepwise built your README draft from your answers. Edit it so it reads well: fix the "
                f"flow, cut what's repeated, add what's missing. Keep it your own words. Here it is:\n\n"
                f"{target.read_text(encoding='utf-8')}\n\nReply with the whole edited README in Markdown, and "
                f"nothing else.", max_tokens=self.args.max_tokens * 2)
            text = re.sub(r"^```(?:markdown|md)?\n|```\s*$", "", reply.strip(), flags=re.M).strip() + "\n"
            project.readme.write_text(text, encoding="utf-8", newline="\n")
            panel.check()
            self.record(page, file=project.readme.name, answer=text, reasoning=reasoning, seconds=seconds)

    async def stage(self, n: int) -> None:
        """Fills every page of stage `n` and presses Next past its last one. Next never blocks, so a page
        the model couldn't fill is left behind, and the transcript says which."""
        app = self.app
        await app.go(n, 0)
        await self.pilot.pause(0.3)
        while app.current == n:
            page = app.pages[app.page]
            await self.fill(page)
            if self.args.shots:
                self.shots.mkdir(parents=True, exist_ok=True)
                app.save_screenshot(str(self.shots / f"{n}-{app.page + 1:02d}-{slugify(page.label)}.svg"))
            await app.action_next()
            await self.pilot.pause(0.3)
        if left := [p.label for p in pages(self.project, n) if page_missing(self.project, p)]:
            self.record(Page("stage", label=f"Stage {n}"), stage=n, note="left unfinished", missing=left)

    async def go(self) -> None:
        first, _, last = self.args.stages.partition("-")
        stages = range(int(first), int(last or first) + 1)
        stepwise_app.open_in_code = lambda *a, **k: None  # never open VS Code windows during a run
        self.app = stepwise_app.StepwiseApp(self.project)
        print(f"{self.persona['name']}: {self.project.root}", flush=True)
        async with self.app.run_test(size=(170, 48)) as self.pilot:
            await self.pilot.pause(0.5)
            for n in stages:
                await self.stage(n)
        print(f"  done: reached stage {self.project.stage}. Transcript: {self.transcript}", flush=True)


END_STAGE = 4  # an agent's run stops once it's through this stage
SIZE = (170, 48)
LIVE = """\
<!doctype html><meta charset="utf-8"><title>Mock user, live</title>
<style>body{margin:0;background:#111;color:#ddd;font:14px system-ui}img{width:100%;display:block}
p{margin:8px 16px}</style><img id="shot"><p id="what"></p>
<script>
let seen = -1;
async function tick() {
  try {
    const turn = await (await fetch("latest.json?" + Date.now())).json();
    if (turn.n !== seen) {
      seen = turn.n;
      document.getElementById("shot").src = "latest.svg?" + turn.n;
      document.getElementById("what").textContent = `#${turn.n} ${turn.action} ${turn.value || ""}` + (turn.why ? ` · ${turn.why}` : "");
    }
  } catch (e) {}
}
setInterval(tick, 1000); tick();
</script>
"""


def screen_text(app) -> str:
    """The stage pane as the user sees it, top to bottom, in Stepwise's own words, then the sidebar: Next
    never blocks, so its ticks are how Stepwise shows what's still to do."""
    lines = [str(app.query_one("#topbar", Static).render()), ""]
    for w in app.query_one("#stage").query("*"):
        if not all(node.display for node in w.ancestors_with_self):
            continue
        if isinstance(w, Button):
            lines.append(f"[ {w.label} ]" + (" (greyed out)" if w.disabled else ""))
        elif isinstance(w, AnswerChoice):
            for i, option in enumerate(w.options, 1):
                first, *rest = str(option.prompt).splitlines()
                lines.append(f"  {i}. {first}")
                lines += [f"     {line}" for line in rest]
        elif isinstance(w, Input):
            lines.append(f"[text box: {w.value}]" if w.value else f"[empty text box: {w.placeholder}]")
        elif isinstance(w, TextArea):
            label = "file, read only" if w.read_only else "text box"
            body = w.text or (f"(empty: {w.placeholder})" if getattr(w, "placeholder", "") else "(empty)")
            lines += [f"[{label}]", *(f"  | {line}" for line in str(body).splitlines()), "[end]"]
        elif isinstance(w, Static) and (text := str(w.render()).strip()):
            lines.append(text)
    sidebar = app.query_one("#sidebar", OptionList)
    lines += ["", "[sidebar]", *(str(sidebar.get_option_at_index(i).prompt) for i in range(sidebar.option_count)),
              "[end sidebar]"]
    return "\n".join(lines)


class Turn:
    """One thing the agent playing a persona does: open the project where it left off, act, show the page."""

    def __init__(self, args, persona: dict):
        self.args, self.persona = args, persona
        self.root = args.home / slugify(persona["app_name"])
        if args.command == "start":
            if args.fresh and (self.root / ".stepwise" / "mock.jsonl").is_file():
                shutil.rmtree(self.root)  # only ever a folder this harness made
            if not Project.find(self.root):
                project = Project.create(self.root, persona["app_name"])
                project.log("mock", persona=persona["key"], model="agent")
                (project.meta / "mock.jsonl").touch()
        self.project = Project.find(self.root)
        if self.project is None:
            sys.exit(f"No project for {persona['key']} yet. Run: python tools/mock_user.py start --persona {persona['key']}")
        self.at = self.project.meta / "mock-at"
        self.shots = self.project.meta / "mock-shots"
        self.notes: list[str] = []

    def file(self, name: str) -> Path:
        path = (self.project.root / name).resolve()
        if not path.is_relative_to(self.project.root):
            sys.exit(f"{name} isn't in your project folder ({self.project.root}).")
        return path

    def outside(self, path: Path) -> None:
        name = path.relative_to(self.project.root).as_posix()
        self.notes.append(f"(VS Code opens {name}. Read it: open {name} · Save your version: edit {name})")

    async def settle(self) -> None:
        """Waits out what Stepwise does after an action: saving, and a prerequisite check that takes a while."""
        await self.pilot.pause(0.5)
        for _ in range(240):
            results = next(iter(self.app.query("#check-results")), None)
            if results is None or "Checking" not in str(results.render()):
                break
            await self.pilot.pause(0.5)

    async def act(self) -> str:
        """Does the command. Returns what it did, for the transcript."""
        args, app = self.args, self.app
        if args.command == "type":
            text = args.text if args.text is not None else sys.stdin.read()
            if line := next(iter(app.query("#stage AnswerLine")), None):
                line.value = text.strip().splitlines()[0] if text.strip() else ""
            elif area := next(iter(app.query("#stage AnswerArea")), None):
                area.load_text(text.strip())
            elif box := next(iter(app.query("#stage #step-input")), None):
                for item in [i.strip() for i in text.splitlines() if i.strip()]:
                    box.focus()
                    box.value = item
                    await self.pilot.press("enter")
                    await self.pilot.pause(0.1)
            else:
                self.notes.append("(There's no box to type in on this page.)")
            return text.strip()
        if args.command == "pick":
            widget = next(iter(app.query("#stage AnswerChoice")), None)
            if widget is None or not 1 <= args.number <= widget.option_count:
                self.notes.append("(There's no option with that number on this page.)")
                return str(args.number)
            widget.focus()
            widget.highlighted = args.number - 1
            await self.pilot.press("enter")
            return str(args.number)
        if args.command == "press":
            want = args.label.strip("‹› ").lower()
            button = next((b for b in app.query("#stage Button") if str(b.label).strip("‹› ").lower() == want), None)
            if button is None or button.disabled:
                self.notes.append(f"(There's no {args.label!r} button you can press on this page.)")
            else:
                button.press()
            return args.label
        if args.command == "next":
            await app.action_next()
        elif args.command == "back":
            await app.action_back()
        elif args.command == "open":
            path = self.file(args.file)
            self.notes.append(f"--- {args.file} ---\n" + (path.read_text(encoding="utf-8") if path.is_file()
                                                       else "(no such file yet)") + "\n--- end ---")
            return args.file
        elif args.command == "edit":
            path = self.file(args.file)
            text = args.text if args.text is not None else sys.stdin.read()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text.strip() + "\n", encoding="utf-8", newline="\n")
            await self.pilot.pause(1.2)  # the dependency view rereads its file every second
            await app.go(app.current, app.page)  # the README check reads the file when the page opens
            self.notes.append(f"(Saved {args.file}.)")
            return args.file
        return ""

    def record(self, page: Page, value: str, **data) -> None:
        entry = {"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "persona": self.persona["key"], "by": "agent",
                 "stage": self.app.current, "page": page.key or page.kind, "kind": page.kind,
                 "action": self.args.command, "value": value, "why": self.args.why, **data}
        if self.args.command == "pick" and (widget := next(iter(self.app.query("#stage AnswerChoice")), None)):
            offered = choices.options(page.key, self.project.answer)
            if 1 <= self.args.number <= len(offered):
                entry |= {"picked": offered[self.args.number - 1].key, "offered": [o.key for o in offered],
                          "best": [o.key for o in offered if o.hint.startswith("Best match")]}
        with open(self.project.meta / "mock.jsonl", "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def snapshot(self, value: str) -> None:
        """Saves the screen for the live view (tools/mock_user.py serves nothing; any static server will do)."""
        self.shots.mkdir(parents=True, exist_ok=True)
        n = len(list(self.shots.glob("turn-*.svg"))) + 1
        self.app.save_screenshot(str(self.shots / f"turn-{n:03d}.svg"))
        shutil.copyfile(self.shots / f"turn-{n:03d}.svg", self.shots / "latest.svg")
        (self.shots / "latest.json").write_text(json.dumps({"n": n, "action": self.args.command, "value": value[:120],
                                                            "why": self.args.why}), encoding="utf-8")
        if not (self.shots / "index.html").is_file():
            (self.shots / "index.html").write_text(LIVE, encoding="utf-8")

    async def go(self) -> None:
        stepwise_app.open_in_code = lambda project, path, what: self.outside(path)
        self.app = app = stepwise_app.StepwiseApp(self.project)
        app.open_url = lambda url, **kw: self.notes.append(f"(Your browser opens {url})")
        app.notify = lambda message, title="", **kw: self.notes.append(f"Stepwise says: {title + ': ' if title else ''}{message}")
        async with app.run_test(size=SIZE) as self.pilot:
            await self.pilot.pause(0.5)
            if self.args.command != "start" and self.at.is_file():
                stage, page = map(int, self.at.read_text().split())
                await app.go(stage, page)
            page, before = app.pages[app.page], self.project.stage
            value = await self.act()
            await self.settle()
            app.save_all()
            if self.args.command not in ("screen", "open"):
                self.record(page, value)
            self.at.write_text(f"{app.current} {app.page}")
            self.snapshot(value)
            for note in self.notes:
                print(note)
            if self.project.stage > END_STAGE:
                # Next never blocks, so getting past the last stage doesn't mean everything in it was done.
                left = [f"{p.label} (stage {n})" for n in range(1, END_STAGE + 1)
                        for p in pages(self.project, n) if page_missing(self.project, p)]
                if before <= END_STAGE:
                    self.record(Page("end", label="End of the run"), "", note="end of run", left=left)
                print(f"\nThat's the end of this test run: you're past stage {END_STAGE}.")
                if left:
                    print("Still unticked in the sidebar: " + "; ".join(left))
            else:
                print(screen_text(app))


TURNS = {
    "start": "make the persona's project and show the first page",
    "screen": "show the page you're on",
    "type": "type into the page's box (text from --text or stdin); on a list page, each line is added",
    "pick": "pick an option by its number",
    "press": "press a button by its label",
    "next": "press Next",
    "back": "press Back",
    "open": "read a file in your project folder, as you would in VS Code",
    "edit": "save a file in your project folder (text from --text or stdin), as you would in VS Code",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="a local model plays the persona through the stages")
    run.add_argument("--persona", default="maya", help="a key from personas.json, or all")
    run.add_argument("--stages", default="1-4", help="like 1-4 or 2")
    run.add_argument("--url", default=URL)
    run.add_argument("--model", default=MODEL)
    run.add_argument("--no-think", action="store_true", help="ask the model not to reason first (faster)")
    run.add_argument("--max-tokens", type=int, default=8000, help="thinking counts toward this")
    run.add_argument("--temperature", type=float, default=0.8)
    run.add_argument("--timeout", type=int, default=1800, help="seconds to wait for one answer")
    run.add_argument("--home", type=Path, default=HOME, help="where mock projects go")
    run.add_argument("--fresh", action="store_true", help="start the persona's project over")
    run.add_argument("--shots", action="store_true", help="save an SVG screenshot of every page")
    for name, help in TURNS.items():
        turn = commands.add_parser(name, help=help)
        if name == "pick":
            turn.add_argument("number", type=int)
        elif name == "press":
            turn.add_argument("label")
        elif name in ("open", "edit"):
            turn.add_argument("file", help="relative to your project folder")
        if name in ("type", "edit"):
            turn.add_argument("--text", help="instead of stdin")
        if name == "start":
            turn.add_argument("--fresh", action="store_true", help="start the persona's project over")
        turn.add_argument("--persona", required=True)
        turn.add_argument("--why", default="", help="the persona's reason, kept in the transcript")
        turn.add_argument("--home", type=Path, default=HOME, help="where mock projects go")
    args = parser.parse_args()
    # Textual passes prints through while it runs but never flushes, so a piped log would sit in the buffer.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    sys.stdin.reconfigure(encoding="utf-8")
    personas = json.loads(PERSONAS.read_text(encoding="utf-8"))
    picked = personas if args.persona == "all" else [p for p in personas if p["key"] == args.persona]
    if not picked or (args.command != "run" and len(picked) > 1):
        sys.exit(f"No persona {args.persona!r}. Choose from: {', '.join(p['key'] for p in personas)}")
    for persona in picked:
        asyncio.run(Run(args, persona).go() if args.command == "run" else Turn(args, persona).go())


if __name__ == "__main__":
    main()
