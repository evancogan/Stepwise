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

LAST_BUILT = 4

INTROS = {
    1: "You came here with an app in mind. Pin it down before you build anything.",
    2: "Break your app into steps, in the order you'll build them. Each step should end in something you can run or see.",
    3: "For each step, write how it works in plain words: the logic, not the code.",
    4: "Before any code, decide what you're building it with. Research the choices you're unsure of.",
}

INTENT_QUESTION = "Describe your app in a sentence or two. Who is it for, and what does it do for them?"
PSEUDO_HINT = "What does this step check, and what does it change?"

# README sections in the order they appear. "Build plan" is the step list itself.
SECTIONS = [
    "About",
    "Why I built this",
    "Build plan",
    "How it works",
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
    heading: str = ""  # subheading in the README; empty means the answer is the section's text


QUESTIONS: dict[int, list[Question]] = {
    1: [
        Question("idea.use", "Walk through using your app once, start to finish. What does the user see, and what do they do?",
                 "About"),
        Question("idea.why", "Why are you building this, and why build it yourself?",
                 "Why I built this"),
    ],
    2: [
        Question("steps.walk", "Walk through your app once more using your steps. Describe the flow from start to finish. "
                 "If a moment isn't covered by any step, go back and add one.",
                 "How it works"),
        Question("steps.critical", "Which step does everything else depend on, and why?",
                 "Challenges and what I learned", "The step everything depends on"),
        Question("steps.later", "Once the first version works, what would you add next?",
                 "Roadmap"),
    ],
    3: [
        Question("pseudo.state", "What does your app need to keep track of while it runs?",
                 "How it works", "What it keeps track of"),
        Question("pseudo.input", "What does the user give your app, and what should happen if it's missing or wrong?",
                 "How it works", "Input"),
        Question("pseudo.hardest", "Which step was hardest to describe in plain words, and what made it hard?",
                 "Challenges and what I learned", "The hardest step to describe"),
    ],
    4: [
        Question("stack.runs", "Where will people use your app: in a browser, on a phone, on a desktop, or in a terminal?",
                 "Tech stack", "Where it runs"),
        Question("stack.built", "What are you building it with? Name the language, framework and libraries, and say why you picked them.",
                 "Tech stack", "Built with"),
        Question("stack.tools", "What will you write, run and debug it with? Your editor, runtime and package manager.",
                 "Development"),
        Question("stack.unsure", "Which of these choices are you least sure about, and how could you test it quickly?",
                 "Challenges and what I learned", "The choice I'm least sure about"),
    ],
}
