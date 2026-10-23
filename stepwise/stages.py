"""Stages, and the questions asked at each one.

Every answer becomes part of the app's README: each question names the README
section it feeds, and optionally a subheading it sits under there. Answers go
in as written, so subheadings are noun phrases that read right above any answer,
never sentence starters the answer has to finish.
"""

from dataclasses import dataclass

TITLES = [
    "Idea",
    "Step Breakdown",
    "Pseudo Implementation",
    "README Part One",
    "Syntax Implementation",
    "App Execution",
    "Test Steps",
    "Pseudo Test Implementation",
    "Syntax Test Implementation",
    "Review and README Part Two",
]

LAST_BUILT = len(TITLES)

INTROS = {
    1: "You came here with an app in mind. Pin it down before you build anything.",
    2: "Break your app into steps, in the order you'll build them. Each step should end in something you can run or see.",
    3: "For each step, write how it works in plain words: the logic, not the code.",
    4: "Before any code, decide what you're building it with. Research the choices you're unsure of.",
    5: "Now write the real code, one step at a time, in your editor. Stepwise shows the file beside your pseudo-code as you save it. Run your app as you go to see each step work.",
    6: "Time to run it. Stepwise runs your app and shows you what your terminal says.",
    7: "Decide what to test: the things that would hurt most if they quietly broke.",
    8: "Write each test in plain words first, the same way you wrote your steps.",
    9: "Now write the tests for real, then let Stepwise run them.",
    10: "Look back at what you built, then finish your README.",
}

INTENT_QUESTION = "Describe your app in a sentence or two. Who is it for, and what does it do for them?"

PSEUDOCODE_URL = "https://en.wikipedia.org/wiki/Pseudocode"
PSEUDO_WORDS = "ASK · SHOW · SET · IF / OTHERWISE · REPEAT · FOR EACH · STOP"
PSEUDO_PLACEHOLDER = "ASK…, IF…, SHOW…"
TEST_PLACEHOLDER = "GIVEN…, WHEN…, THEN…"

PSEUDO_PRIMER = f"""\
Pseudocode is your program written in plain words. No syntax to get right, and no computer will run it. \
It's for you: once the logic reads right in words, turning it into code is mostly translation.

There's no single standard. Some people write it like Python, some like maths, some in full sentences. \
Stepwise uses plain sentences with a few capital-letter words for the structure:

```
ASK the user for the total
IF the total is empty
    SHOW "Enter a total"
OTHERWISE
    SET the tip to total × percentage
    SHOW the tip
```

One line per action. Indent whatever belongs inside an IF or a REPEAT. The words to lean on: {PSEUDO_WORDS}.

Want more? Wikipedia compares the common styles:
"""

TEST_PRIMER = f"""\
A test is a small promise about your app, checked by code. Write each one in plain words first, \
using three capital-letter words: what's true before, what happens, and what should be true after.

```
GIVEN the total is 0
WHEN the tip is worked out
THEN the tip is 0
```

It's the same kind of pseudocode as your steps, so the same words still work inside it: {PSEUDO_WORDS}.

Want more? Wikipedia compares the common pseudocode styles:
"""

FILES_QUESTION = (
    "What files will your app need? Start with one; most small apps only need one or two. Give a part its own "
    "file when it starts doing a second job, gets hard to read, or has code you'd want to use somewhere else. "
    "One per line: the file name, a colon, and what it's for, like tip.py: works out the tip"
)
TESTS_QUESTION = "What should you test? One thing per line, in plain words, like: the tip is 0 when the total is 0"

RESEARCH_PROMPT = (
    "Before you plan anything, see how others have built something like it. Search, read a few pages, and "
    "come back with what you found."
)
RESEARCH_NOTES_PROMPT = "Your notes: what did you learn? Anything that surprised you or changed your plan."
RESOURCES_QUESTION = (
    "Which pages helped? Add each link, one at a time. They become your README's Further resources, and "
    "you can come back to them while you build."
)
SEARCH_URL = "https://www.google.com/search?q="


def search_query(name: str) -> str:
    return f"how to build your own {name}"

RUN_FAILED ="It didn't run. Read the error above. In your own words, what went wrong, and which step's code is it in?"
TESTS_FAILED = "Some tests failed. Which one, and is the test wrong or the app?"

# README sections in the order they appear. Build plan, Project structure and Testing are built
# from lists (steps, files, tests) as well as answers.
SECTIONS = [
    "About",
    "Why I built this",
    "Build plan",
    "How it works",
    "Project structure",
    "Prerequisites",
    "Getting started",
    "Tech stack",
    "Development",
    "Status",
    "Known issues",
    "Testing",
    "Challenges and what I learned",
    "Roadmap",
    "What I learned from research",
    "Further resources",
]

# Sections that only exist once the app is built; README Part Two appends whichever are missing.
# Prerequisites is written in Part One, and listed here for READMEs drafted before it existed.
PART_TWO_SECTIONS = [
    "Project structure",
    "Prerequisites",
    "Getting started",
    "Status",
    "Known issues",
    "Testing",
    "Challenges and what I learned",
]


@dataclass(frozen=True)
class Question:
    key: str
    prompt: str
    section: str = ""   # README section; empty means the answer isn't part of the README
    heading: str = ""   # subheading in the README; empty means the answer is the section's text
    code: bool = False  # shown as a code block in the README, for commands
    line: bool = False  # answered on one line, like a version or a command


QUESTIONS: dict[int, list[Question]] = {
    1: [
        Question("research.notes", RESEARCH_NOTES_PROMPT, "What I learned from research"),
        Question("idea.use", "Walk through using your app once, start to finish. What does the user see, and what do they do?",
                 "About"),
        Question("idea.why", "Why are you building this, and why build it yourself?",
                 "Why I built this"),
    ],
    2: [
        Question("steps.walk", "Walk through your app once more using your steps. Describe the flow from start to finish. "
                 "If a moment isn't covered by any step, go back and add one.",
                 "How it works"),
        Question("steps.later", "Once the first version works, what would you add next?",
                 "Roadmap"),
    ],
    3: [
        Question("pseudo.state", "What does your app need to keep track of while it runs?",
                 "How it works", "What it keeps track of"),
        Question("pseudo.input", "What does the user give your app, and what should happen if it's missing or wrong?",
                 "How it works", "Input"),
    ],
    4: [
        Question("stack.runs", "Where will people use your app: in a browser, on a phone, on a desktop, or in a terminal?",
                 "Tech stack", "Where it runs"),
        Question("stack.built", "What are you building it with? Name the language, framework and libraries, and say why you picked them.",
                 "Tech stack", "Built with"),
        Question("stack.tools", "What will you write, run and debug it with? Your editor, runtime and package manager.",
                 "Development"),
        Question("lang.version", "Which version of your language does the app need? Like: Python 3.14",
                 "Prerequisites", line=True),
        Question("setup.steps", "How does someone get those installed? Write the steps you'd give a friend: making a "
                 "virtual environment, installing the libraries, anything else. Stepwise won't run these.",
                 "Prerequisites", "Setting it up"),
        Question("run.command", "What one command will start your app? Stepwise runs it inside your project "
                 "folder, just like typing it into a terminal there, so you can try your app as you build it. "
                 "Like: python main.py",
                 "Getting started", "Running it", code=True),
    ],
    6: [
        Question("run.result", "It ran! What did you see, and how does it compare to what you described back in stage 1?",
                 "Status"),
        Question("run.limits", "Try to break it: leave something blank, type something wrong, use a huge number. What happens?",
                 "Known issues"),
        Question("run.diff", "Where did your code end up different from your pseudo-code?",
                 "How it works", "Changes from the plan"),
    ],
    9: [
        Question("tests.file", "What file will your tests live in? Something like: test_tip.py"),
        Question("tests.command", "How do you run your tests? Something like: python -m pytest",
                 "Testing", "Running the tests", code=True),
    ],
    10: [
        Question("review.critical", "Which step did everything else depend on, and how did that play out?",
                 "Challenges and what I learned", "The step everything depended on"),
        Question("review.hardest", "Which part was hardest to build, and what made it hard?",
                 "Challenges and what I learned", "The hardest part"),
        Question("review.choice", "Which choice from stage 4 would you make differently now, and why?",
                 "Challenges and what I learned", "What I'd choose differently"),
        Question("review.again", "If you started this app over tomorrow, what would you do differently?",
                 "Challenges and what I learned", "If I started over"),
    ],
}

QUESTION = {q.key: q for qs in QUESTIONS.values() for q in qs}
