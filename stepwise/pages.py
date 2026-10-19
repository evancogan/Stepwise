"""The pages of each stage, and what each one needs before the user can move on."""

from dataclasses import dataclass

from .prereqs import deps_missing
from .stages import (FILES_QUESTION, INTENT_QUESTION, LAST_BUILT, PSEUDO_PLACEHOLDER, QUESTION, RESEARCH_PROMPT,
                     RESOURCES_QUESTION, TESTS_QUESTION, TEST_PLACEHOLDER)
from .store import Project


@dataclass(frozen=True)
class Page:
    """One screen within a stage. Each holds a single thing to do, so no page is a wall of fields.

    kind: "answer", "list" (key is the list: steps, files, tests or resources), "research" (the search button), "info" (key is the primer:
    pseudo or tests), "deps" (the dependency file), "code" (key is steps or tests, item is the
    position), "check" (the prerequisites check), "run" (key is app or tests), "readme", "part2",
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
                question("idea.use"), question("idea.why"),
                Page("research", prompt=RESEARCH_PROMPT, label="Research"),
                Page("list", "resources", RESOURCES_QUESTION, "Further resources", label="Your resources")]
    if stage == 2:
        return [Page("list", "steps", section="Build plan", label="Your steps"), question("steps.walk"), question("steps.later")]
    if stage == 3:
        return [Page("info", "pseudo", label="What is pseudocode?"),
                *([Page("answer", f"pseudo{n}", f"Step {n} of {len(steps)}: {step}", placeholder=PSEUDO_PLACEHOLDER,
                        label=f"Step {n}: {step}") for n, step in enumerate(steps, 1)] or [STEP_PSEUDO]),
                question("pseudo.state", note="Now look back over your pseudo-code."), question("pseudo.input")]
    if stage == 4:
        return [question("stack.runs"), question("stack.built"),
                Page("list", "files", FILES_QUESTION, "Project structure", label="Your files"),
                question("stack.tools"),
                question("lang.version", label="Language version"),
                Page("deps", section="Prerequisites", label="Dependency file"),
                question("setup.steps", label="Setting it up"), Page("readme", label="README draft")]
    if stage == 5:
        return [Page("code", "steps", f"Step {n} of {len(steps)}: {step}", "Build plan",
                     label=f"Step {n}: {step}", item=n) for n, step in enumerate(steps, 1)] or [STEP_CODE]
    if stage == 6:
        return [question("run.command"), Page("check", section="Prerequisites", label="Check prerequisites"),
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


def page_missing(project: Project, page: Page) -> str:
    """What's left to do on this page, or an empty string."""
    if page.kind == "empty":
        return page.note
    if page.kind == "answer" and not project.answer(page.key):
        return "Answer this one before moving on."
    if page.kind == "list" and page.key != "resources" and not project.items(page.key):
        return {"steps": "Add at least one step before moving on.",
                "files": "List at least one file before moving on.",
                "tests": "Add at least one test before moving on."}[page.key]
    if page.kind == "answer" and page.line and "\n" in project.answer(page.key):
        return "Use one command on one line. Setup steps go in stage 4, under Setting it up."
    if page.kind == "deps" and (problem := deps_missing(project)):
        return problem
    if page.kind == "check" and project.get("prereq_check") != "ok":
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
    if page.kind == "readme" and project.readme_is_draft():
        return "Edit your README draft and save it before moving on."
    if page.kind == "part2" and not project.part_two_added():
        return "Add Part Two to your README before moving on."
    if page.kind == "part2" and not project.part_two_written():
        return "Edit Part Two in your README and save it before moving on."
    return ""
