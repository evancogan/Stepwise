"""A Stepwise project on disk.

Layout, inside the project folder:
  .stepwise/state           key=value lines: name, stage (furthest stage reached), README hashes, run outcomes
  .stepwise/<list>.txt      one item per line, for the steps, files and tests lists
  .stepwise/answers/*.txt   one file per answer: intent, each question's key, and per-item answers
  .stepwise/usage.jsonl     one JSON event per line: how the user moved through Stepwise
  notes.md                  every answer, rebuilt on each save
  README.md                 drafted from the answers in stage 4, extended in stage 10, written by the user
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

from .stages import INTENT_QUESTION, LAST_BUILT, QUESTIONS, TITLES

META = ".stepwise"

# Answers that belong to one item of a list, keyed by the item's position. They're rewritten
# whenever the list changes, so each one stays with its item when items move or are removed.
# "pseudo{n}" predates the other keys and is kept so existing projects still load.
ITEM_KEYS = {
    "steps": ["pseudo{n}", "code{n}.file", "code{n}.done", "code{n}.stuck"],
    "files": [],
    "tests": ["test{n}.pseudo", "test{n}.done", "test{n}.stuck"],
}


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "app"


def sha(text: str) -> str:
    return hashlib.sha256(text.replace("\r\n", "\n").strip().encode()).hexdigest()[:16]


def parse_file_line(line: str) -> tuple[str, str]:
    """`tip.py: works out the tip` -> ("tip.py", "works out the tip")."""
    name, _, purpose = line.partition(":")
    return name.strip().strip("`"), purpose.strip()


def _write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    # On Windows the rename fails while another program (an editor, a sync client, antivirus)
    # has the target open. Retry briefly, then write in place so the answer isn't lost.
    for attempt in range(5):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(0.05 * (attempt + 1))
    path.write_text(text, encoding="utf-8", newline="\n")
    tmp.unlink(missing_ok=True)


class Project:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.meta = self.root / META
        self.answers = self.meta / "answers"

    @classmethod
    def find(cls, root: Path) -> "Project | None":
        project = cls(root)
        return project if (project.meta / "state").is_file() else None

    @classmethod
    def create(cls, root: Path, name: str) -> "Project":
        project = cls(root)
        project.answers.mkdir(parents=True, exist_ok=True)
        if not (project.meta / "state").is_file():
            project._write_state({"name": name, "stage": "1"})
        return project

    # --- state ---------------------------------------------------------

    def _read_state(self) -> dict[str, str]:
        state = {}
        for line in (self.meta / "state").read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep:
                state[key] = value
        return state

    def _write_state(self, state: dict[str, str]) -> None:
        _write(self.meta / "state", "".join(f"{k}={v}\n" for k, v in state.items()))

    def get(self, key: str, default: str = "") -> str:
        return self._read_state().get(key, default)

    def set(self, key: str, value: str) -> None:
        state = self._read_state()
        state[key] = value
        self._write_state(state)

    @property
    def name(self) -> str:
        return self.get("name", self.root.name)

    @property
    def stage(self) -> int:
        return int(self.get("stage", "1"))

    @stage.setter
    def stage(self, value: int) -> None:
        self.set("stage", str(value))

    # --- usage log -----------------------------------------------------

    def log(self, event: str, **data) -> None:
        record = {"t": datetime.now().isoformat(timespec="seconds"), "event": event, **data}
        with open(self.meta / "usage.jsonl", "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # --- answers -------------------------------------------------------

    def answer(self, key: str) -> str:
        path = self.answers / f"{key}.txt"
        return path.read_text(encoding="utf-8").rstrip("\n") if path.is_file() else ""

    def set_answer(self, key: str, text: str) -> None:
        """Writes one answer. Callers rebuild notes.md themselves, once per batch of saves."""
        path = self.answers / f"{key}.txt"
        if text.strip():
            _write(path, text.rstrip() + "\n")
        else:
            path.unlink(missing_ok=True)
        if key == "tests.file" and text.strip():
            self.create_file(text.strip())

    # --- lists: steps, files, tests -------------------------------------

    def items(self, name: str) -> list[str]:
        path = self.meta / f"{name}.txt"
        if not path.is_file():
            return []
        return [s for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]

    def item_answers(self, name: str) -> list[dict[str, str]]:
        """Each item's own answers, keyed by template, in list order."""
        return [{key: self.answer(key.format(n=n)) for key in ITEM_KEYS[name]}
                for n in range(1, len(self.items(name)) + 1)]

    def set_items(self, name: str, items: list[str], answers: list[dict[str, str]]) -> None:
        """Saves a list with each item's answers, renumbered to the items' new positions."""
        old_count = len(self.items(name))
        _write(self.meta / f"{name}.txt", "".join(s + "\n" for s in items))
        for n, item_answers in enumerate(answers, 1):
            for key in ITEM_KEYS[name]:
                self.set_answer(key.format(n=n), item_answers.get(key, ""))
        for n in range(len(items) + 1, old_count + 1):
            for key in ITEM_KEYS[name]:
                (self.answers / f"{key.format(n=n)}.txt").unlink(missing_ok=True)
        if name == "files":
            for file_name, _ in self.files():
                self.create_file(file_name)
        self.write_notes()

    def steps(self) -> list[str]:
        return self.items("steps")

    def tests(self) -> list[str]:
        return self.items("tests")

    def files(self) -> list[tuple[str, str]]:
        """The app's files as (name, purpose)."""
        return [parse_file_line(line) for line in self.items("files")]

    def pseudo(self) -> list[str]:
        return [self.answer(f"pseudo{n}") for n in range(1, len(self.steps()) + 1)]

    # --- the user's code files -------------------------------------------

    def code_path(self, name: str) -> Path | None:
        """A file inside the project folder, or None for a name that points outside it."""
        if not name:
            return None
        path = (self.root / name).resolve()
        return path if path.is_relative_to(self.root) and path != self.root else None

    def create_file(self, name: str) -> None:
        """Creates an empty file for the user to write in. Never touches an existing file."""
        if (path := self.code_path(name)) and not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

    def step_file(self, n: int) -> str:
        return self.answer(f"code{n}.file")

    # --- runs ------------------------------------------------------------

    def outcome(self, kind: str) -> str:
        """The last run's result for "app" or "tests": "ok", "failed", "not_found" or ""."""
        return self.get(f"{kind}_outcome")

    def failures(self, kind: str) -> int:
        return int(self.get(f"{kind}_failures", "0"))

    def reminders(self) -> list[str]:
        """The user's own notes from building: stuck notes and explanations of failed runs."""
        notes = []
        for n, step in enumerate(self.steps(), 1):
            if text := self.answer(f"code{n}.stuck"):
                notes.append(f"Step {n} ({step}): {text}")
        for n, test in enumerate(self.tests(), 1):
            if text := self.answer(f"test{n}.stuck"):
                notes.append(f"Test {n} ({test}): {text}")
        for kind, label in (("app", "Run"), ("tests", "Test run")):
            for n in range(1, self.failures(kind) + 1):
                if text := self.answer(f"{kind}.attempt{n}"):
                    notes.append(f"{label} {n} failed: {text}")
        return notes

    # --- README --------------------------------------------------------

    @property
    def readme(self) -> Path:
        return self.root / "README.md"

    def write_draft(self, text: str) -> Path:
        """Writes the generated draft to README.md, unless the user has edited it since the
        last draft; then it goes to README.draft.md so their writing is never overwritten."""
        target = self.readme
        if self.readme.exists() and not self.readme_is_draft():
            target = self.root / "README.draft.md"
        _write(target, text)
        if target == self.readme:
            self.set("draft_sha", sha(text))
        return target

    def readme_text(self) -> str:
        return self.readme.read_text(encoding="utf-8") if self.readme.is_file() else ""

    def readme_is_draft(self) -> bool:
        """True while README.md is exactly what Stepwise generated."""
        return self.readme.is_file() and sha(self.readme_text()) == self.get("draft_sha")

    def readme_written(self) -> bool:
        return self.readme.is_file() and not self.readme_is_draft()

    def append_part_two(self, text: str) -> None:
        """Adds Part Two's sections to the end of README.md, leaving everything above untouched."""
        current = self.readme_text().rstrip("\n")
        new = f"{current}\n\n{text}" if text.strip() else current + "\n"
        _write(self.readme, new)
        self.set("part2_sha", sha(new))

    def part_two_added(self) -> bool:
        return bool(self.get("part2_sha"))

    def part_two_written(self) -> bool:
        return self.part_two_added() and sha(self.readme_text()) != self.get("part2_sha")

    # --- notes.md ------------------------------------------------------

    def write_notes(self) -> None:
        """notes.md collects every answer under the question that prompted it."""
        out = [f"# {self.name}: notes\n",
               "Your answers from Stepwise, by stage. Stepwise rewrites this file, "
               "so keep your own edits elsewhere.\n"]
        steps, tests = self.steps(), self.tests()
        for stage in range(1, LAST_BUILT + 1):
            parts = []
            if stage == 1 and self.answer("intent"):
                parts.append(f"**{INTENT_QUESTION}**\n\n{self.answer('intent')}\n")
            if stage == 2 and steps:
                parts.append("**Steps**\n\n" + "".join(f"{n}. {s}\n" for n, s in enumerate(steps, 1)))
            if stage == 3:
                for n, step in enumerate(steps, 1):
                    if text := self.answer(f"pseudo{n}"):
                        parts.append(f"**Step {n}: {step}**\n\n```\n{text}\n```\n")
            if stage == 4 and self.items("files"):
                parts.append("**Files**\n\n" + "".join(f"- {f}\n" for f in self.items("files")))
            if stage == 5:
                for n, step in enumerate(steps, 1):
                    if file := self.step_file(n):
                        done = "done" if self.answer(f"code{n}.done") else "not done yet"
                        parts.append(f"**Step {n}: {step}** in `{file}`, {done}\n")
                    if text := self.answer(f"code{n}.stuck"):
                        parts.append(f"Stuck on step {n}: {text}\n")
            if stage == 7 and tests:
                parts.append("**Tests**\n\n" + "".join(f"{n}. {t}\n" for n, t in enumerate(tests, 1)))
            if stage == 8:
                for n, test in enumerate(tests, 1):
                    if text := self.answer(f"test{n}.pseudo"):
                        parts.append(f"**Test {n}: {test}**\n\n```\n{text}\n```\n")
            if stage in (6, 9):
                kind = "app" if stage == 6 else "tests"
                for n in range(1, self.failures(kind) + 1):
                    if text := self.answer(f"{kind}.attempt{n}"):
                        parts.append(f"**Failed run {n}**\n\n{text}\n")
            for q in QUESTIONS.get(stage, []):
                if text := self.answer(q.key):
                    parts.append(f"**{q.prompt}**\n\n{text}\n")
            if parts:
                out.append(f"## {stage}. {TITLES[stage - 1]}\n")
                out += parts
        _write(self.root / "notes.md", "\n".join(out))
