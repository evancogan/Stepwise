"""Stage names and the leading questions asked at each one, matching the README's Flow section."""

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

QUESTIONS = {
    1: [
        "If you could only ship one screen, what would be on that screen?",
        "What's the one thing this app does that nothing else you've used does?",
    ],
    2: [
        "Which step, if you got it wrong, would break everything after it?",
        "Which steps depend on something you haven't built yet, and which could you start today?",
        "If you had half the time, what would you cut, and what would the app lose?",
    ],
    3: [
        "For each step, what goes in, what comes out, and what does the app have to remember between runs?",
        "Where does your logic depend on outside input, and what happens when that input is missing or wrong?",
        "Which part of your pseudo-code would be hardest to explain to someone who doesn't know your app?",
    ],
    4: [
        "Where does this app run, and who needs to open it there?",
        "What does the user see, what handles the logic, and where does the data live? Name one tool for each and say why you chose it.",
        "Which of your choices would be expensive to change in six months? Research those first.",
        "For each library, what problem does it solve that you couldn't solve in a few hundred lines? What does it cost you?",
        "Which part of the system must talk to which other part, and what breaks if one side is slow?",
        "Which choice are you least sure about, and what's the cheapest way to test it before you commit?",
    ],
}
