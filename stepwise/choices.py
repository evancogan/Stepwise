"""The multiple-choice questions at the start of stage 4: a few about the app and how the user likes
to work, which rank Stepwise's six languages, then a few that pick a full stack for the chosen one.

Answers are stored as option keys, like any other answer. This module imports nothing else from
Stepwise (store imports it, and languages imports store), so functions take `answer`, a function
from an answer's key to its text, usually `project.answer`.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

Answer = Callable[[str], str]

# Same keys and order as languages.LANGUAGES, which also breaks ties in the ranking.
LANGUAGES = {"python": "Python", "javascript": "JavaScript", "go": "Go", "rust": "Rust", "java": "Java",
             "csharp": "C#"}

BLURBS = {
    "python": "Dynamic and strongly typed, garbage collected, with the biggest library ecosystem for data "
              "and scripting.",
    "javascript": "The browser's own language. Dynamic and weakly typed (TypeScript adds static types), async "
                  "on an event loop.",
    "go": "Static types, garbage collected, goroutines for concurrency. Builds one file with nothing to install.",
    "rust": "Static types and no garbage collector: the compiler checks who owns each piece of memory. As fast "
            "as C.",
    "java": "Static types on the JVM, garbage collected, with a huge and mature ecosystem.",
    "csharp": "Static types on .NET, garbage collected, with async/await. Strong for desktop, web and games.",
}


@dataclass(frozen=True)
class Option:
    key: str
    label: str
    hint: str = ""
    points: dict[str, tuple[int, str]] = field(default_factory=dict)  # language -> (points, reason)


def same(points: int, reason: str, *languages: str) -> dict[str, tuple[int, str]]:
    return {lang: (points, reason) for lang in languages}


UNSURE = "Not sure yet"

# Shared by "In a browser" and "On a phone": Stepwise can't run phone apps, so a phone app is
# built as a browser app that works on a small screen.
WEB_POINTS = {"javascript": (3, "it's the language browsers run"),
              "python": (1, "Flask or Django can serve the pages"),
              "go": (1, "its standard library includes a web server"),
              "rust": (1, "Axum serves pages fast"),
              "java": (1, "Javalin or Spring Boot can serve the pages"),
              "csharp": (1, "ASP.NET Core can serve the pages")}

OPTIONS: dict[str, list[Option]] = {
    "choose.runs": [
        Option("browser", "In a browser", "A website or web app, opened from a link.", WEB_POINTS),
        Option("desktop", "On a desktop, in its own window", "Windows and buttons, on Windows, macOS or Linux.",
               {"python": (2, "Tkinter comes with it"), "csharp": (2, "WinForms and Avalonia make desktop apps"),
                "java": (2, "Swing comes with it and runs on every desktop"),
                "javascript": (1, "Electron wraps a web page in a window"),
                "go": (1, "Fyne draws windows from Go"), "rust": (1, "egui draws fast windows")}),
        Option("terminal", "In a terminal", "Text in, text out: a command-line tool or a text game.",
               {"python": (2, "a terminal app needs nothing installed"),
                "go": (2, "builds command-line tools that start instantly"),
                "rust": (2, "builds fast command-line tools"),
                **same(1, "runs fine in a terminal", "javascript", "java", "csharp")}),
        Option("phone", "On a phone", "Stepwise can't run phone apps yet, so this becomes a browser app that "
               "works well on a phone.", WEB_POINTS),
    ],
    "choose.decided": [
        Option("help", "Help me choose", "A few questions about your app and how you like to work, then the six "
               "languages Stepwise knows, ranked."),
        Option("decided", "I've already decided, or I have to use one",
               "For a class, a job or a codebase that already exists. Go straight to the list."),
    ],
    "choose.work": [
        Option("interactive", "Waiting for someone to type or click",
               "Most apps. Any of the six is quick enough for this, so it doesn't change the ranking."),
        Option("data", "Working through data: tables, numbers, statistics",
               "Python's data libraries (pandas, NumPy) do the heavy lifting in fast C underneath.",
               {"python": (3, "pandas and NumPy make data work short"), "rust": (2, "processes large data fast"),
                "go": (1, "streams large files steadily"), "java": (1, "has mature data libraries"),
                "csharp": (1, "LINQ makes querying data short")}),
        Option("network", "Talking to websites, APIs or other services",
               "Lots of requests going out or coming in, often at the same time.",
               {"go": (3, "built for network services"), "javascript": (2, "its event loop juggles many requests"),
                "python": (1, "requests and httpx keep it simple"), "rust": (1, "tokio and reqwest are fast"),
                "java": (1, "has mature HTTP libraries"), "csharp": (1, "HttpClient and async/await are built in")}),
        Option("compute", "Heavy computing: simulations, parsing, crunching",
               "The processor is the bottleneck, so the language's raw speed matters.",
               {"rust": (3, "runs as fast as C"), "go": (2, "compiles to fast native code"),
                "java": (2, "the JVM's JIT makes hot code fast"), "csharp": (2, ".NET's JIT makes hot code fast")}),
        Option("realtime", "Drawing things that move, like a game", "Smooth animation needs steady frame times.",
               {"rust": (2, "no garbage-collector pauses"), "csharp": (2, "it's the language of most indie games"),
                "java": (1, "LibGDX and Swing can draw games")}),
        Option("unsure", UNSURE, "This one won't count."),
    ],
    "choose.ship": [
        Option("interpreter", "As a script: people need the language installed",
               "They run your source code with the language's interpreter, like python app.py or node app.js.",
               {"python": (2, "runs straight from source"), "javascript": (2, "runs straight from source with Node")}),
        Option("vm", "On a runtime that works the same everywhere",
               "Compiled once to bytecode, which the JVM or .NET runs on any system.",
               {"java": (2, "the JVM runs the same jar anywhere"), "csharp": (2, ".NET runs the same build anywhere")}),
        Option("binary", "As one file with nothing else to install",
               "Compiled to native code for each system: send the file and it runs.",
               {"go": (3, "builds one file with nothing to install"),
                "rust": (3, "builds one file with nothing to install"),
                "csharp": (1, "can publish a single file")}),
        Option("unsure", UNSURE, "This one won't count. It matters most once other people run your app."),
    ],
    "choose.types": [
        Option("static", "Checked before it runs",
               "The compiler refuses code where the types don't fit, so mistakes show up as you write.",
               {**same(2, "checks types before it runs", "go", "rust", "java", "csharp"),
                "javascript": (1, "TypeScript adds checked types")}),
        Option("strong", "Checked while it runs, strictly",
               'No type declarations, but "1" + 1 is an error: values never quietly change type.',
               {"python": (3, "dynamic but strongly typed")}),
        Option("weak", "Flexible: values convert when they need to",
               '"1" + 1 gives "11". Quick to write, but surprises turn up when it runs.',
               {"javascript": (3, "values convert freely")}),
        Option("gradual", "Loose to start, stricter later",
               "Add type hints as the code settles, and a type checker reads them.",
               {"python": (2, "type hints and mypy add checking later"),
                "javascript": (2, "TypeScript adds types as you go")}),
        Option("unsure", UNSURE, "This one won't count. Static types catch more mistakes early; dynamic types "
               "let you try things faster."),
    ],
    "choose.memory": [
        Option("managed", "Fast enough, and the language looks after memory",
               "Garbage collected and interpreted or JIT-compiled. Heavy number work runs in libraries written in C.",
               {"python": (2, "looks after memory for you"), "javascript": (2, "looks after memory, with a fast JIT")}),
        Option("gc", "Compiled and quick, with a garbage collector",
               "Close to native speed without managing memory yourself.",
               {"go": (2, "compiled, with a garbage collector"),
                **same(2, "JIT-compiled, with a garbage collector", "java", "csharp")}),
        Option("control", "Full control: no garbage collector, as fast as C",
               "The compiler checks who owns each piece of memory, so it's safe and fast, with more rules to learn.",
               {"rust": (3, "no garbage collector, with memory ownership checked")}),
        Option("unsure", UNSURE, "This one won't count."),
    ],
    "choose.conc": [
        Option("none", "No, one thing at a time", "Most first apps. It doesn't change the ranking."),
        Option("eventloop", "Wait on many things at once, on one thread",
               "async/await on an event loop: good for network calls and files, with no locks to get wrong.",
               {"javascript": (3, "everything is async on an event loop"), "python": (1, "asyncio does the same")}),
        Option("green", "Thousands of lightweight tasks, built into the language",
               "Goroutines and channels: start a task per job and pass messages between them.",
               {"go": (3, "goroutines and channels are built in"), "java": (1, "virtual threads work the same way")}),
        Option("threads", "Real threads, with async/await",
               "Work runs in parallel across processor cores. (Python's GIL lets only one thread run Python at a "
               "time.)",
               {"csharp": (2, "threads and async/await are built in"), "java": (2, "has mature threads and executors"),
                "rust": (1, "threads plus async with tokio")}),
        Option("safe", "Real threads, with the compiler preventing data races",
               "Code that could let two threads clash over the same data won't compile.",
               {"rust": (3, "the compiler rules out data races")}),
        Option("unsure", UNSURE, "This one won't count."),
    ],
    "choose.errors": [
        Option("exceptions", "Exceptions: errors jump to whoever catches them",
               "try/except or try/catch. The main code stays clean, but any call might throw.",
               same(2, "uses exceptions", "python", "javascript", "java", "csharp")),
        Option("values", "Errors as values you check after each call",
               "if err != nil after each call, so every error is handled where it happens.",
               {"go": (3, "errors are values you check")}),
        Option("result", "A Result type the compiler makes you handle",
               "Result<T, E> and the ? operator: code that ignores an error won't compile.",
               {"rust": (3, "the compiler makes you handle every error")}),
        Option("unsure", UNSURE, "This one won't count."),
    ],
    "choose.data": [
        Option("none", "No, it starts fresh every time", "Nothing to save, so no database."),
        Option("local", "Yes, for the person using it", "Their scores, settings or lists, in a file or a small "
               "database."),
        Option("shared", "Yes, shared between everyone who uses it", "Accounts, posts, a leaderboard. That needs "
               "a server and a database."),
    ],
    "choose.effort": [
        Option("minimal", "Minimal: the language and its standard library",
               "Fewer installs, and you see every piece working."),
        Option("framework", "A framework: conventions and batteries included",
               "More to learn up front, then it handles the repetitive parts for you."),
    ],
}

# The questions that rank the languages, in page order.
RANKING = ["choose.runs", "choose.work", "choose.ship", "choose.types", "choose.memory", "choose.conc",
           "choose.errors"]

# The answers the README's Built with lines come from.
STACK_KEYS = ("choose.language", "choose.data", "choose.effort", "choose.stack")


@dataclass(frozen=True)
class Stack:
    """A frontend for one language and platform. Its backend and data come from choose.data: a
    browser stack's backend is its own (Flask, Express…), and any other app gets the language's
    server only when its data is shared."""
    key: str
    runs: str
    language: str
    effort: str  # "minimal" or "framework"
    frontend: str
    hint: str
    backend: str = ""
    local: str = ""  # where it keeps one person's data, if not the language's usual place


SERVERS = {"python": "Flask", "javascript": "Express", "go": "net/http", "rust": "Axum", "java": "Javalin",
           "csharp": "ASP.NET Core"}
LOCAL = {"python": "SQLite (built into Python)", "javascript": "A JSON file", "go": "A JSON file",
         "rust": "A JSON file (serde)", "java": "A text file", "csharp": "A JSON file (System.Text.Json)"}
SHARED = "PostgreSQL"

STACKS = [
    Stack("py-plain", "terminal", "python", "minimal", "print and input",
          "Nothing to install: Python's built-ins are all a terminal app needs."),
    Stack("py-rich", "terminal", "python", "framework", "Rich",
          "Colour, tables, progress bars and prompts, on top of plain print."),
    Stack("js-node", "terminal", "javascript", "minimal", "console.log and readline",
          "Node's own modules, nothing to install."),
    Stack("go-plain", "terminal", "go", "minimal", "fmt and bufio",
          "Go's standard library, built into one file."),
    Stack("rust-plain", "terminal", "rust", "minimal", "println! and std::io",
          "Rust's standard library, built into one file."),
    Stack("java-plain", "terminal", "java", "minimal", "System.out and Scanner",
          "Java's standard library, nothing to install."),
    Stack("cs-console", "terminal", "csharp", "minimal", "Console",
          ".NET's own Console class, nothing to install."),
    Stack("cs-spectre", "terminal", "csharp", "framework", "Spectre.Console",
          "Colour, tables, prompts and progress bars for .NET."),

    Stack("py-tkinter", "desktop", "python", "minimal", "Tkinter",
          "Comes with Python. Plain-looking windows, quick to build."),
    Stack("py-pyside", "desktop", "python", "framework", "PySide6 (Qt)",
          "Looks like a real app on every system. Bigger to learn."),
    Stack("js-electron", "desktop", "javascript", "framework", "Electron",
          "Your app is a web page in its own window, with Node behind it. Big downloads."),
    Stack("go-fyne", "desktop", "go", "framework", "Fyne",
          "Windows and widgets drawn by Go, the same on every system."),
    Stack("rust-egui", "desktop", "rust", "framework", "egui (eframe)",
          "Redraws the whole window each frame: simple to reason about, and fast."),
    Stack("java-swing", "desktop", "java", "minimal", "Swing",
          "Comes with Java and runs on every desktop."),
    Stack("java-javafx", "desktop", "java", "framework", "JavaFX",
          "Newer than Swing, with styling and animation."),
    Stack("cs-winforms", "desktop", "csharp", "minimal", "Windows Forms",
          "Drag-and-drop simple, but Windows only."),
    Stack("cs-avalonia", "desktop", "csharp", "framework", "Avalonia",
          "XAML layouts that run on Windows, macOS and Linux."),

    Stack("py-flask", "browser", "python", "minimal", "HTML pages (Jinja templates)",
          "Small and readable: you write each page and route yourself.", "Flask", "SQLite"),
    Stack("py-fastapi", "browser", "python", "framework", "HTML, CSS and JavaScript",
          "Your pages call a typed Python API, with docs generated for you.", "FastAPI", "SQLite"),
    Stack("py-django", "browser", "python", "framework", "Django templates",
          "Logins, an admin page and a database layer come built in.", "Django", "SQLite (built into Django)"),
    Stack("js-plain", "browser", "javascript", "minimal", "HTML, CSS and JavaScript",
          "Open the file in a browser and it runs. No server, nothing to install.", "",
          "localStorage, in the browser"),
    Stack("js-react", "browser", "javascript", "framework", "React (with Vite)",
          "One language on both ends, and more tutorials than any other stack.", "Express", "SQLite"),
    Stack("go-nethttp", "browser", "go", "minimal", "HTML pages (html/template)",
          "All from Go's standard library: no framework to learn.", "net/http", "SQLite"),
    Stack("go-gin", "browser", "go", "framework", "HTML pages (Gin templates)",
          "Routing, middleware and JSON handled for you.", "Gin", "SQLite"),
    Stack("rust-axum", "browser", "rust", "minimal", "HTML, CSS and JavaScript",
          "A small, fast web framework on tokio.", "Axum", "SQLite (sqlx)"),
    Stack("java-javalin", "browser", "java", "minimal", "HTML, CSS and JavaScript",
          "A small web framework: a route is a few lines.", "Javalin", "SQLite"),
    Stack("java-spring", "browser", "java", "framework", "Thymeleaf templates",
          "The framework most Java jobs use. Lots of conventions.", "Spring Boot", "H2 (an embedded database)"),
    Stack("cs-minimal", "browser", "csharp", "minimal", "HTML, CSS and JavaScript",
          "A route is one line of C#.", "ASP.NET Core minimal API", "SQLite"),
    Stack("cs-razor", "browser", "csharp", "framework", "Razor Pages",
          "Each page is HTML with C# mixed in.", "ASP.NET Core", "SQLite (EF Core)"),
]
STACK = {s.key: s for s in STACKS}


def platform(answer: Answer) -> str:
    """Where the app runs, for picking stacks. A phone app is built as a browser app."""
    runs = answer("choose.runs")
    return "browser" if runs == "phone" else runs


def helped(answer: Answer) -> bool:
    return answer("choose.decided") != "decided"


def asks_ship(answer: Answer) -> bool:
    """A browser app is shipped as a link, so how it's installed doesn't come up."""
    return platform(answer) != "browser"


def rank(answer: Answer) -> list[tuple[str, int, list[str]]]:
    """(language, score, reasons) for each language, best first. Ties keep LANGUAGES order."""
    scores = {lang: [] for lang in LANGUAGES}
    for key in RANKING:
        if key == "choose.ship" and not asks_ship(answer):
            continue
        option = next((o for o in OPTIONS[key] if o.key == answer(key)), None)
        for lang, (points, reason) in (option.points if option else {}).items():
            scores[lang].append((points, reason))
    ranked = [(lang, sum(p for p, _ in found), [r for _, r in sorted(found, key=lambda f: -f[0])])
              for lang, found in scores.items()]
    return sorted(ranked, key=lambda r: -r[1])


def stacks_for(answer: Answer) -> list[Stack]:
    """The stacks for the chosen language and platform, the chosen effort first."""
    lang, runs, effort = answer("choose.language"), platform(answer), answer("choose.effort")
    fitting = [s for s in STACKS if s.language == lang and s.runs == runs]
    return sorted(fitting, key=lambda s: s.effort != effort)[:3]


def parts(stack: Stack, data: str) -> tuple[str, str]:
    """(backend, data) for a stack, given how the app keeps its data. Either can be empty."""
    backend = stack.backend or (f"{SERVERS[stack.language]} server" if data == "shared" else "")
    store = {"local": stack.local or LOCAL[stack.language], "shared": SHARED}.get(data, "")
    return backend, store


def stack_name(stack: Stack, data: str) -> str:
    backend, _ = parts(stack, data)
    return f"{stack.frontend} + {backend}" if backend else stack.frontend


OTHER_LANGUAGE = Option("other", "Something else",
                        "Stepwise can't make its dependency file or check its setup, but you can still build with it.")
OTHER_STACK = Option("other", "Something else", "Name it on the next page, in your own words.")


def options(key: str, answer: Answer) -> list[Option]:
    """The options a choice page shows now. The language and stack pages depend on earlier answers."""
    if key == "choose.language":
        if not helped(answer):
            return [*(Option(lang, name, BLURBS[lang]) for lang, name in LANGUAGES.items()), OTHER_LANGUAGE]
        ranked = rank(answer)
        best = ranked[0][1]
        found = []
        for lang, score, reasons in ranked:
            why = "; ".join(reasons[:2]) or "None of your answers point to it"
            why = why[0].upper() + why[1:]
            if score and score == best:
                why = f"Best match · {why}"
            found.append(Option(lang, LANGUAGES[lang], f"{why}.\n{BLURBS[lang]}"))
        return [*found, OTHER_LANGUAGE]
    if key == "choose.stack":
        data = answer("choose.data")
        found = []
        for stack in stacks_for(answer):
            backend, store = parts(stack, data)
            layers = [f"Frontend: {stack.frontend}", f"Backend: {backend or 'none, it all runs in the app'}"]
            if store:
                layers.append(f"Data: {store}")
            found.append(Option(stack.key, stack_name(stack, data), " · ".join(layers) + "\n" + stack.hint))
        return [*found, OTHER_STACK]
    return OPTIONS.get(key, [])


def picked(key: str, answer: Answer) -> bool:
    """Whether the stored answer is one of the options shown now. A stack picked for another
    language stops counting, so changing the language asks for the stack again."""
    return answer(key) in {o.key for o in options(key, answer)}


def shown(key: str, value: str) -> str:
    """How a stored answer reads: an option's label, or the text as it is for anything else."""
    if key == "choose.language":
        return LANGUAGES.get(value, OTHER_LANGUAGE.label if value == "other" else value)
    if key == "choose.stack":
        return STACK[value].frontend if value in STACK else OTHER_STACK.label if value == "other" else value
    return next((o.label for o in OPTIONS.get(key, []) if o.key == value), value)


def built_with(answer: Answer) -> list[str]:
    """The README's Built with lines: the language and stack the user picked, as a list."""
    lang = answer("choose.language")
    if lang not in LANGUAGES:
        return []
    lines = [f"- Language: {LANGUAGES[lang]}"]
    if picked("choose.stack", answer) and (stack := STACK.get(answer("choose.stack"))):
        backend, store = parts(stack, answer("choose.data"))
        lines.append(f"- Frontend: {stack.frontend}")
        if backend:
            lines.append(f"- Backend: {backend}")
        if store:
            lines.append(f"- Data: {store}")
    return lines


def from_lists(answer: Answer) -> bool:
    """Whether both the language and the stack were picked from Stepwise's lists."""
    return answer("choose.language") in LANGUAGES and answer("choose.stack") in STACK and picked("choose.stack", answer)
