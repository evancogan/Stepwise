"""Builds a README draft from the user's own answers. Every word in it is theirs;
Stepwise only supplies the headings that frame each answer."""

import re
from collections.abc import Mapping

from .languages import detect
from .prereqs import dependency_file
from .stages import PART_TWO_SECTIONS, QUESTIONS, SECTIONS
from .store import Project

PLACEHOLDER = "Your answer will appear here."


def highlight(text: str) -> str:
    """Marks every line as Markdown strong, which the preview styles as a highlight.
    List markers stay outside the markup so lists still render."""
    lines = []
    for line in text.splitlines():
        marker, content = re.match(r"(\s*(?:[-*+]|\d+\.)?\s*(?:\[[ x]\]\s*)?)(.*)", line).groups()
        lines.append(f"{marker}**{content.strip()}**" if content.strip() else line)
    return "\n".join(lines)


def checklist(items: list[str], done: list[bool], here: int | None) -> str:
    """`here` is the 0-based item being worked on, or -1 to highlight the whole list."""
    lines = [f"- [{'x' if ticked else ' '}] {item}" for item, ticked in zip(items, done)]
    return "\n".join(highlight(line) if here in (-1, i) else line for i, line in enumerate(lines))


def draft(project: Project, live: Mapping[str, str] | None = None, here: str | None = None) -> str:
    """`live` holds answers still being typed (not yet saved). `here` is what's on screen: a
    question key, "list:<name>" or "code:<steps|tests>:<n>". Its text is highlighted, or shown
    as a highlighted placeholder while empty, so the user sees where their writing lands."""
    live = live or {}
    kind, _, target = (here or "").partition(":")

    def text(key: str) -> str:
        value = (live[key] if key in live else project.answer(key)).strip()
        if key != here:
            return value
        return highlight(value) if value else f"***{PLACEHOLDER}***"

    def list_here(name: str) -> int | None:
        if here == f"list:{name}":
            return -1
        if kind == "code" and target.startswith(f"{name}:"):
            return int(target.split(":")[1]) - 1
        return None

    out = [f"# {project.name}"]
    if intent := text("intent"):
        out.append(intent)

    steps, tests = project.steps(), project.tests()
    questions = [q for stage in sorted(QUESTIONS) for q in QUESTIONS[stage] if q.section]
    for section in SECTIONS:
        body = []
        if section == "Build plan" and steps:
            done = [bool(project.answer(f"code{n}.done")) for n in range(1, len(steps) + 1)]
            body.append(checklist(steps, done, list_here("steps")))
        if section == "Project structure" and (files := project.files()):
            lines = []
            for name, purpose in files:
                lines.append(f"- `{name}`" + (f": {purpose}" if purpose else ""))
                lines += [f"  - Step {n}: {step}" for n, step in enumerate(steps, 1) if project.step_file(n) == name]
            if test_file := project.answer("tests.file").strip():
                lines.append(f"- `{test_file}`: the tests")
            structure = "\n".join(lines)
            body.append(highlight(structure) if here == "list:files" else structure)
        if section == "Prerequisites":
            lines = [f"- {version}"] if (version := text("lang.version")) else []
            libraries = []
            for lang in detect(project):
                file_name, deps, _ = dependency_file(project, lang)
                if deps:
                    libraries.append(f"- Libraries, from `{file_name}`: " + ", ".join(deps))
            lines += [highlight(line) for line in libraries] if here == "deps" else libraries
            if lines:
                body.append("\n".join(lines))
        if section == "Further resources" and (links := project.items("resources")):
            listing = "\n".join(f"- {link}" for link in links)
            body.append(highlight(listing) if here == "list:resources" else listing)
        if section == "Testing" and tests:
            done = [bool(project.answer(f"test{n}.done")) for n in range(1, len(tests) + 1)]
            body.append(checklist(tests, done, list_here("tests")))
        for q in (q for q in questions if q.section == section and q.key != "lang.version"):
            if answer := text(q.key):
                if q.code and q.key != here:  # a highlight inside a code block would show as literal **
                    answer = f"```\n{answer}\n```"
                body += [f"### {q.heading}", answer] if q.heading else [answer]
        if body:
            out.append(f"## {section}")
            out += body
    return "\n\n".join(out) + "\n"


def part_two(project: Project) -> str:
    """The Part Two sections of the draft that README.md doesn't have yet."""
    have = {line[3:].strip().lower() for line in project.readme_text().splitlines() if line.startswith("## ")}
    sections = re.split(r"\n\n(?=## )", draft(project))
    wanted = {s.lower() for s in PART_TWO_SECTIONS} - have
    picked = [s for s in sections if s.startswith("## ") and s[3:].split("\n", 1)[0].strip().lower() in wanted]
    return "\n\n".join(picked).rstrip("\n") + ("\n" if picked else "")
