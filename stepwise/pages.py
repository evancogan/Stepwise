"""The pages of each stage, and what each one needs before the user can move on."""

from dataclasses import dataclass, replace

from . import choices
from .prereqs import check_state, deps_missing
from .stages import (BUILT_WHY, FILES_QUESTION, INTENT_QUESTION, LAST_BUILT, PSEUDO_PLACEHOLDER, QUESTION,
                     RESEARCH_PROMPT, TESTS_QUESTION, TEST_PLACEHOLDER)
from .store import Project


@dataclass(frozen=True)
class Page:
    """One screen within a stage. Each holds a single thing to do, so no page is a wall of fields.

    kind: "answer", "choice" (multiple choice; the options come from choices.py),
    "list" (key is the list: steps, files, tests or resources, which also has the search button), "info" (key is the primer:
    pseudo or tests), "deps" (the dependency file), "code" (key is steps or tests, item is the
    position), "check" (the prerequisites check; key is setup in stage 4 or app in stage 6), "run"
    (key is app or tests), "readme", "part2",
    "empty" (stands in for pages that need steps or tests the user hasn't added yet) or "done".
    """
    kind: str
    key: str = ""
    prompt: str = ""
    section: str = ""
    placeholder: str = ""
    label: str = ""  # short name for the sidebar checklist
    item: int = 0
    note: str = ""  # a line shown above the question, e.g. to mark a look-back
    line: bool = False  # a one-line answer, for commands Stepwise runs


def question(key: str, note: str = "", label: str = "") -> Page:
    q = QUESTION[key]
    return Page("answer", q.key, q.prompt, q.section, label=label or q.heading or q.section, note=note, line=q.code or q.line)


def choice(key: str, label: str, section: str = "") -> Page:
    """`section` is where the preview scrolls to, for picks that feed the README without being an answer in it."""
    q = QUESTION[key]
    return Page("choice", q.key, q.prompt, section or q.section, label=label)


def choosing(project: Project) -> list[Page]:
    """Stage 4's questionnaire: where the app runs, a language, then a stack for it."""
    answer = project.answer
    ranking = [choice("choose.work", "What it does"),
               *([choice("choose.ship", "How it ships")] if choices.asks_ship(answer) else []),
               choice("choose.types", "Types"), choice("choose.memory", "Speed and memory"),
               choice("choose.conc", "Doing things at once"), choice("choose.errors", "Errors")]
    stack = [choice("choose.data", "Saving things"), choice("choose.effort", "How much help"),
             choice("choose.stack", "Your stack", "Tech stack")]
    built = question("stack.built")
    return [choice("choose.runs", "Where it runs"), choice("choose.decided", "Help choosing"),
            *(ranking if choices.helped(answer) else []),
            choice("choose.language", "Your language", "Tech stack"),
            *(stack if answer("choose.language") != "other" else []),
            replace(built, prompt=BUILT_WHY) if choices.from_lists(answer) else built]


def waiting_for(what: str, stage: int, does: str, sample: str) -> Page:
    """Shown where a stage's pages come from steps or tests the user hasn't added yet."""
    return Page("empty", what, label=f"No {what} yet",
                note=f"Each {what[:-1]} from stage {stage} gets its own page here, {does}. Add your {what} in "
                     f"stage {stage} first.",
                placeholder=sample)


STEP_PSEUDO = waiting_for("steps", 2, "where you write it in plain words",
                          "Step 1 of 3: …\n\nASK…, IF…, SHOW…")
STEP_CODE = waiting_for("steps", 2, "where you write its code",
                        "Step 1 of 3: …\nYour pseudo-code\nWhich file does this step go in?\n"
                        "The file, live as you save it\n☐ It's written and saved")
TEST_PSEUDO = waiting_for("tests", 7, "where you write it in plain words",
                          "Test 1 of 2: …\n\nGIVEN…, WHEN…, THEN…")
TEST_CODE = waiting_for("tests", 7, "where you write its code",
                        "Test 1 of 2: …\nYour pseudo-code\nYour test file, live as you save it\n"
                        "☐ It's written and saved")


def pages(project: Project, stage: int) -> list[Page]:
    if stage > LAST_BUILT:
        return [Page("done", label="Done")]
    steps, tests = project.steps(), project.tests()
    if stage == 1:
        return [Page("answer", "intent", INTENT_QUESTION, "the opening line", label="Description"),
                Page("list", "resources", RESEARCH_PROMPT, "Further resources", label="Research"),
                question("research.notes", label="What I learned"),
                question("idea.use"), question("idea.why")]
    if stage == 2:
        return [Page("list", "steps", section="Build plan", label="Your steps"), question("steps.walk"), question("steps.later")]
    if stage == 3:
        return [Page("info", "pseudo", label="What is pseudocode?"),
                *([Page("answer", f"pseudo{n}", f"Step {n} of {len(steps)}: {step}", placeholder=PSEUDO_PLACEHOLDER,
                        label=f"Step {n}: {step}") for n, step in enumerate(steps, 1)] or [STEP_PSEUDO]),
                question("pseudo.state", note="Now look back over your pseudo-code."), question("pseudo.input")]
    if stage == 4:
        return [*choosing(project),
                Page("list", "files", FILES_QUESTION, "Project structure", label="Your files"),
                question("stack.tools"),
                question("lang.version", label="Language version"),
                Page("deps", section="Prerequisites", label="Dependency file"),
                question("setup.steps", label="Setting it up"),
                Page("check", "setup", section="Prerequisites", label="Check your setup"),
                question("run.command"), Page("readme", label="README draft")]
    if stage == 5:
        return [Page("code", "steps", f"Step {n} of {len(steps)}: {step}", "Build plan",
                     label=f"Step {n}: {step}", item=n) for n, step in enumerate(steps, 1)] or [STEP_CODE]
    if stage == 6:
        return [Page("check", "app", section="Prerequisites", label="Check prerequisites"),
                Page("run", "app", section="Getting started", label="Run it"), question("run.result"),
                question("run.limits", note="Look back: now that it runs, see how it holds up."),
                question("run.diff")]
    if stage == 7:
        return [Page("list", "tests", TESTS_QUESTION, "Testing", label="Your tests")]
    if stage == 8:
        return [Page("info", "tests", label="Writing tests in words"),
                *([Page("answer", f"test{n}.pseudo", f"Test {n} of {len(tests)}: {test}", placeholder=TEST_PLACEHOLDER,
                        label=f"Test {n}: {test}") for n, test in enumerate(tests, 1)] or [TEST_PSEUDO])]
    if stage == 9:
        return [question("tests.file", label="Your test file"),
                *([Page("code", "tests", f"Test {n} of {len(tests)}: {test}", "Testing", label=f"Test {n}: {test}",
                        item=n) for n, test in enumerate(tests, 1)] or [TEST_CODE]),
                question("tests.command"), Page("run", "tests", section="Testing", label="Run the tests")]
    return [question("review.critical"), question("review.hardest"), question("review.choice"),
            question("review.again"), Page("part2", label="README Part Two")]


def page_done(project: Project, page: Page) -> bool:
    """Whether the sidebar ticks this page."""
    return not page_missing(project, page)


def page_missing(project: Project, page: Page) -> str:
    """What's left to do on this page, or an empty string."""
    if page.kind == "empty":
        return page.note
    if page.kind == "answer" and not project.answer(page.key):
        return "Answer this one before moving on."
    if page.kind == "choice" and not choices.picked(page.key, project.answer):
        return "Pick one before moving on."
    if page.kind == "list" and not project.items(page.key):
        return {"resources": "Add at least one link from your research before moving on.",
                "steps": "Add at least one step before moving on.",
                "files": "List at least one file before moving on.",
                "tests": "Add at least one test before moving on."}[page.key]
    if page.kind == "answer" and page.line and "\n" in project.answer(page.key):
        return "Use one command on one line. Setup steps go in stage 4, under Setting it up."
    if page.kind == "deps" and (problem := deps_missing(project)):
        return problem
    if page.kind == "check" and project.get(check_state(page.key)) != "ok":
        return "Fix what the check found, then press Check again."
    if page.kind == "code":
        if page.key == "steps":
            name, done = project.step_file(page.item), project.answer(f"code{page.item}.done")
        else:
            name, done = project.answer("tests.file").strip(), project.answer(f"test{page.item}.done")
        path = project.code_path(name)
        if not name:
            return "Pick the file this step goes in." if page.key == "steps" else "Name your test file first."
        if path is None:
            return f"{name} is outside your project folder."
        if not path.exists():
            return f"Stepwise can't find {name}."
        if not path.read_text(encoding="utf-8", errors="replace").strip():
            return f"{name} is empty. Write the code and save it."
        if not done:
            return "Tick “It's written and saved” when it's done."
    if page.kind == "run" and project.outcome(page.key) != "ok":
        return ("Run your app and get it working before moving on." if page.key == "app"
                else "Run your tests and get them passing before moving on.")
    if page.kind == "readme" and not project.readme.is_file():
        return "Build your README draft before moving on."
    if page.kind == "readme" and project.readme_is_original():
        return ("Build your README draft before moving on." if not project.readme_draft.is_file() else
                "Bring your draft into README.md and save it before moving on.")
    if page.kind == "readme" and project.readme_is_draft():
        return "Edit your README draft and save it before moving on."
    if page.kind == "part2" and not project.part_two_added():
        return "Add Part Two to your README before moving on."
    if page.kind == "part2" and not project.part_two_written():
        return "Edit Part Two in your README and save it before moving on."
    return ""
