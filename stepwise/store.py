"""A Stepwise project on disk.

Layout, inside the project folder:
  .stepwise/state           key=value lines: name, stage (furthest stage reached), draft_sha
  .stepwise/steps.txt       one step per line
  .stepwise/answers/*.txt   one file per answer: intent, pseudo<n>, and each question's key
  .stepwise/usage.jsonl     one JSON event per line: how the user moved through Stepwise
  notes.md                  every answer, rebuilt on each save
  README.md                 drafted from the answers in stage 4, then written by the user
"""

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path

from .stages import INTENT_QUESTION, LAST_BUILT, QUESTIONS, TITLES

META = ".stepwise"


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "app"


def sha(text: str) -> str:
    return hashlib.sha256(text.replace("\r\n", "\n").strip().encode()).hexdigest()[:16]


def _write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


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
        path = self.answers / f"{key}.txt"
        if text.strip():
            _write(path, text.rstrip() + "\n")
        else:
            path.unlink(missing_ok=True)
        self.write_notes()

    # --- steps ---------------------------------------------------------

    def steps(self) -> list[str]:
        path = self.meta / "steps.txt"
        if not path.is_file():
            return []
        return [s for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]

    def set_steps(self, steps: list[str], pseudo: list[str]) -> None:
        """Saves steps with their pseudo-code, so pseudo stays with its step when steps move."""
        old_count = len(self.steps())
        _write(self.meta / "steps.txt", "".join(s + "\n" for s in steps))
        for n, text in enumerate(pseudo, 1):
            path = self.answers / f"pseudo{n}.txt"
            if text.strip():
                _write(path, text.rstrip() + "\n")
            else:
                path.unlink(missing_ok=True)
        for n in range(len(pseudo) + 1, old_count + 1):
            (self.answers / f"pseudo{n}.txt").unlink(missing_ok=True)
        self.write_notes()

    def pseudo(self) -> list[str]:
        return [self.answer(f"pseudo{n}") for n in range(1, len(self.steps()) + 1)]

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

    def readme_is_draft(self) -> bool:
        """True while README.md is exactly what Stepwise generated."""
        return self.readme.is_file() and sha(self.readme.read_text(encoding="utf-8")) == self.get("draft_sha")

    def readme_written(self) -> bool:
        return self.readme.is_file() and not self.readme_is_draft()

    # --- progress ------------------------------------------------------

    def missing(self, stage: int) -> list[str]:
        """What still has to be filled in before leaving this stage."""
        missing = []
        if stage == 1 and not self.answer("intent"):
            missing.append("your app description")
        if stage == 2 and not self.steps():
            missing.append("at least one step")
        if stage == 3:
            missing += [f"pseudo-code for step {n}" for n, p in enumerate(self.pseudo(), 1) if not p]
        for q in QUESTIONS.get(stage, []):
            short = q.prompt if len(q.prompt) <= 50 else q.prompt[:47].rsplit(" ", 1)[0] + "…"
            if not self.answer(q.key):
                missing.append(f"“{short}”")
            elif q.follow and not self.answer(q.follow_key):
                missing.append(f"the follow-up to “{short}”")
        if stage == 4 and not self.readme.is_file():
            missing.append("your README (press Build README draft)")
        elif stage == 4 and self.readme_is_draft():
            missing.append("your README (it's still the untouched draft)")
        return missing

    # --- notes.md ------------------------------------------------------

    def write_notes(self) -> None:
        """notes.md collects every answer under the question that prompted it."""
        out = [f"# {self.name}: notes\n",
               "Your answers from Stepwise, by stage. Stepwise rewrites this file, "
               "so keep your own edits elsewhere.\n"]
        steps = self.steps()
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
            for q in QUESTIONS.get(stage, []):
                if text := self.answer(q.key):
                    parts.append(f"**{q.prompt}**\n\n{text}\n")
                if q.follow and (text := self.answer(q.follow_key)):
                    parts.append(f"**{q.follow}**\n\n{text}\n")
            if parts:
                out.append(f"## {stage}. {TITLES[stage - 1]}\n")
                out += parts
        _write(self.root / "notes.md", "\n".join(out))
