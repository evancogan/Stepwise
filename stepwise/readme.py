"""Builds a README draft from the user's own answers. Every word in it is theirs;
Stepwise only supplies the headings that frame each answer."""

from collections.abc import Mapping

from .stages import QUESTIONS, SECTIONS
from .store import Project

PLACEHOLDER = "*Your answer will appear here.*"


def draft(project: Project, live: Mapping[str, str] | None = None, here: str | None = None) -> str:
    """`live` holds answers still being typed (not yet saved); `here` is the question on
    screen, which gets a placeholder while it's empty so the user sees where it lands."""
    live = live or {}

    def text(key: str) -> str:
        value = (live[key] if key in live else project.answer(key)).strip()
        return value or (PLACEHOLDER if key == here else "")

    out = [f"# {project.name}"]
    if intent := text("intent"):
        out.append(intent)

    questions = [q for stage in sorted(QUESTIONS) for q in QUESTIONS[stage]]
    for section in SECTIONS:
        body = []
        if section == "Build plan" and (steps := project.steps()):
            body.append("\n".join(f"- [ ] {step}" for step in steps))
        for q in (q for q in questions if q.section == section):
            if answer := text(q.key):
                body += [f"### {q.heading}", answer] if q.heading else [answer]
        if body:
            out.append(f"## {section}")
            out += body
    return "\n\n".join(out) + "\n"
