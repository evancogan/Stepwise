"""Stages, and the questions asked at each one.

Every answer becomes part of the app's README: each question names the README
section it feeds and the label its answer appears under there. That's why the
questions are broad and about decisions, not checks.
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

LAST_BUILT = 4

INTROS = {
    1: "You came here with an app in mind. Pin it down before you build anything.",
    2: "Break your app into steps, in the order you'll build them. Each step should end in something you can run or see.",
    3: "For each step, write how it works in plain words: the logic, not the code.",
    4: "Before any code, decide what you're building it with: where it runs, frontend, backend, data, libraries and tools. Research the choices you're unsure of.",
}

INTENT_QUESTION = "Describe your app in a sentence or two. Who is it for, and what does it do for them?"
PSEUDO_HINT = "What does this step check, and what does it change?"

# README sections in the order they appear. "Build steps" is the step list itself.
SECTIONS = [
    "About",
    "Why I built this",
    "Build steps",
    "How it works",
    "Getting started",
    "Tech stack",
    "Development",
    "Challenges and what I learned",
    "Roadmap",
]


@dataclass(frozen=True)
class Question:
    key: str
    prompt: str
    section: str
    label: str = ""          # README lead-in; empty means the answer stands as its own paragraph
    follow: str = ""         # asked once the main answer is in
    follow_label: str = ""

    @property
    def follow_key(self) -> str:
        return f"{self.key}.follow"


QUESTIONS: dict[int, list[Question]] = {
    1: [
        Question("idea.use", "Walk through using your app once, start to finish. What does the user see, and what do they do?",
                 "About"),
        Question("idea.why", "Why are you building this?", "Why I built this",
                 follow="What will building it yourself give you that an existing app wouldn't?"),
    ],
    2: [
        Question("steps.walk", "Walk through one use of your app again. Which step handles each moment? Add a step for any moment none of them covers.",
                 "How it works"),
        Question("steps.critical", "Which step, if you got it wrong, would break everything after it?",
                 "Challenges and what I learned", "Everything else depends on",
                 follow="Why?", follow_label="Why"),
        Question("steps.cut", "If you had half the time, which steps would you cut?",
                 "Roadmap", "Could come later",
                 follow="What would the app lose without them?", follow_label="What it adds"),
    ],
    3: [
        Question("pseudo.state", "What does your app have to keep track of while it runs, or between runs?",
                 "How it works", "Keeps track of"),
        Question("pseudo.input", "What input does your app take?",
                 "How it works", "Input",
                 follow="What happens when that input is missing or wrong?", follow_label="When input goes wrong"),
        Question("pseudo.hardest", "Which step's logic was hardest to put into words?",
                 "Challenges and what I learned", "Hardest to pin down",
                 follow="Why?", follow_label="Why"),
    ],
    4: [
        Question("stack.runs", "Where does your app run, and what does someone need to open it?",
                 "Getting started", "Requirements"),
        Question("stack.parts", "What does the user see, what handles the logic, and where does the data live? Name the tool for each.",
                 "Tech stack", "Built with",
                 follow="Why each one, over the alternatives you looked at?", follow_label="Why these"),
        Question("stack.libs", "Which libraries will you use, and what does each one do for you?",
                 "Tech stack", "Libraries",
                 follow="What does each one cost you: learning time, size, or control?", follow_label="Trade-offs"),
        Question("stack.connect", "How do the parts of your app talk to each other?",
                 "How it works", "How the parts connect"),
        Question("stack.tools", "What will you write, run and debug it with? Editor, runtime, package manager, build tools.",
                 "Development"),
        Question("stack.unsure", "Which choice are you least sure about?",
                 "Challenges and what I learned", "Least sure about",
                 follow="What's the cheapest way to test it before you commit?", follow_label="How I'll find out"),
    ],
}
