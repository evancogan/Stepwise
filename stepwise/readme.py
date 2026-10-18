"""Builds a README draft from the user's own answers. Every word in it is theirs;
Stepwise only supplies the headings and the labels that frame each answer."""

from .stages import QUESTIONS, SECTIONS
from .store import Project


def draft(project: Project) -> str:
    out = [f"# {project.name}"]
    if intent := project.answer("intent"):
        out.append(intent)

    questions = [q for stage in sorted(QUESTIONS) for q in QUESTIONS[stage]]
    for section in SECTIONS:
        body = []
        if section == "Build steps":
            body += ["\n".join(f"- [ ] {step}" for step in project.steps())] if project.steps() else []
        for q in (q for q in questions if q.section == section):
            for label, key in ((q.label, q.key), (q.follow_label, q.follow_key)):
                if text := project.answer(key):
                    body.append(f"**{label}:** {text}" if label else text)
        if body:
            out.append(f"## {section}")
            out += body
    return "\n\n".join(out) + "\n"
