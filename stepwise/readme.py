"""Builds a README draft from the user's own answers. Every word in it is theirs;
Stepwise only supplies the headings that frame each answer."""

import re
from collections.abc import Mapping

from .stages import QUESTIONS, SECTIONS
from .store import Project

PLACEHOLDER = "Your answer will appear here."
STEPS = "steps"  # `here` value for the step list page


def bold(text: str) -> str:
    """Bolds every line, keeping list markers outside the bold so lists still render."""
    lines = []
    for line in text.splitlines():
        marker, content = re.match(r"(\s*(?:[-*+]|\d+\.)?\s*(?:\[[ x]\]\s*)?)(.*)", line).groups()
        lines.append(f"{marker}**{content.strip()}**" if content.strip() else line)
    return "\n".join(lines)


def draft(project: Project, live: Mapping[str, str] | None = None, here: str | None = None) -> str:
    """`live` holds answers still being typed (not yet saved). `here` is what's on screen:
    a question key, or STEPS. Its text is bolded in the draft, or replaced by a bold
    placeholder while empty, so the user sees where their writing lands."""
    live = live or {}

    def text(key: str) -> str:
        value = (live[key] if key in live else project.answer(key)).strip()
        if key != here:
            return value
        return bold(value) if value else f"***{PLACEHOLDER}***"

    out = [f"# {project.name}"]
    if intent := text("intent"):
        out.append(intent)

    questions = [q for stage in sorted(QUESTIONS) for q in QUESTIONS[stage]]
    for section in SECTIONS:
        body = []
        if section == "Build plan" and (steps := project.steps()):
            plan = "\n".join(f"- [ ] {step}" for step in steps)
            body.append(bold(plan) if here == STEPS else plan)
        for q in (q for q in questions if q.section == section):
            if answer := text(q.key):
                body += [f"### {q.heading}", answer] if q.heading else [answer]
        if body:
            out.append(f"## {section}")
            out += body
    return "\n\n".join(out) + "\n"
