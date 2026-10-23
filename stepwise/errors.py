"""Help with a failed run, worked out from its output: the error, the line of the user's own code it
points at, and what that kind of error usually means. It says where to look and what the words mean,
never how to fix it. That part stays with the user."""

import re
from dataclasses import dataclass
from pathlib import Path

from .store import NOT_SOURCE, Project

# What each kind of error usually means, in plain words. Each one ends on where to look, not on a fix.
MEANINGS = {
    "name": "The code used a name that doesn't exist at that point. Usually it's a typo, a variable used "
            "before the line that sets it, or one used outside the block it belongs to.",
    "type": "A value was used in a way its type doesn't allow, like adding text to a number, or calling "
            "something that isn't a function. Which values are on that line, and what type is each one?",
    "attribute": "The code asked a value for something it doesn't have, like a method or field its type "
                 "doesn't offer. Often the value isn't what you think it is: what is it just before that line?",
    "none": "The code used a value that wasn't there (None, null, nil or undefined) where you expected "
            "something real. Which value on that line is empty, and where should it have been set?",
    "index": "The code asked for a position that a list or string doesn't have. How long is it at that point, "
             "and which position was asked for? Positions usually start at 0.",
    "key": "The code looked up a key that isn't in the dictionary or map. Which keys does it have at that "
           "point?",
    "number": "Text was turned into a number, but it isn't one, like \"abc\" or an empty answer. Where does "
              "that text come from, and what happens when someone types something unexpected?",
    "value": "A value had the right type but the wrong content for what was done with it. What was the "
             "value, and what did that line need?",
    "zero": "Something was divided by zero. Which value can be zero there?",
    "module": "A library the code imports can't be found. Is it installed, and is it in your dependency "
              "file? The check in stage 4 can tell you.",
    "file": "The code tried to open a file or folder that isn't there. A relative path starts from the "
            "folder your app runs in, shown above the output.",
    "syntax": "The code couldn't be read at all, so none of it ran. Look at that line and the one before it "
              "for a missing bracket, quote, colon or comma.",
    "indent": "The indentation doesn't line up. Python uses it to tell which lines belong inside an if, a "
              "loop or a function, so every line in a block needs the same indent.",
    "recursion": "A function kept calling itself and never stopped. What's meant to make it stop, and does "
                 "that ever happen?",
    "input": "The app tried to read what the user typed, but there was nothing to read. While it runs, type "
             "in the box under the output and press Enter.",
    "assert": "A check came out false: the code did something different from what was expected. Is the "
              "expectation wrong, or the code?",
    "unused": "Go won't build code with an import or variable that's never used. Is it left over, or did "
              "you mean to use it?",
    "unwrap": "unwrap() found an error or nothing (None) instead of a value, and stopped the app. Where can "
              "that value be missing, and what should happen then?",
    "borrow": "A value was used after it was moved or lent somewhere else. In Rust each value has one owner "
              "at a time: which line took it?",
}

# Error names, from every language Stepwise knows, mapped to what they mean.
NAMES = {
    "NameError": "name", "UnboundLocalError": "name", "ReferenceError": "name",
    "TypeError": "type", "ClassCastException": "type", "InvalidCastException": "type",
    "AttributeError": "attribute",
    "NullPointerException": "none", "NullReferenceException": "none", "ArgumentNullException": "none",
    "IndexError": "index", "IndexOutOfBoundsException": "index", "ArrayIndexOutOfBoundsException": "index",
    "StringIndexOutOfBoundsException": "index", "IndexOutOfRangeException": "index",
    "ArgumentOutOfRangeException": "index",
    "KeyError": "key", "KeyNotFoundException": "key",
    "NumberFormatException": "number", "FormatException": "number", "InputMismatchException": "number",
    "ValueError": "value", "RangeError": "value",
    "ZeroDivisionError": "zero", "ArithmeticException": "zero", "DivideByZeroException": "zero",
    "ModuleNotFoundError": "module", "ImportError": "module", "ClassNotFoundException": "module",
    "NoClassDefFoundError": "module",
    "FileNotFoundError": "file", "FileNotFoundException": "file", "DirectoryNotFoundException": "file",
    "NoSuchFileException": "file", "IsADirectoryError": "file",
    "SyntaxError": "syntax",
    "IndentationError": "indent", "TabError": "indent",
    "RecursionError": "recursion", "StackOverflowError": "recursion", "StackOverflowException": "recursion",
    "EOFError": "input", "NoSuchElementException": "input",
    "AssertionError": "assert", "AssertionFailedError": "assert",
}

# Messages that say more than the error's name does, checked first. "'NoneType' object is not
# subscriptable" is a TypeError by name, but the real problem is a missing value.
MESSAGES = [(re.compile(pattern, re.I), meaning) for pattern, meaning in [
    (r"NoneType|of undefined|of null|is undefined|is null|nil pointer|null reference", "none"),
    (r"invalid literal for int|could not convert string to float|for input string|not in a correct format",
     "number"),
    (r"index out of range|index out of bounds", "index"),
    (r"divide by zero|division by zero|/ by zero", "zero"),
    (r"cannot find module|cannot find package|no required module provides|unresolved import|can't find crate",
     "module"),
    (r"maximum call stack|maximum recursion depth|stack overflow", "recursion"),
    (r"declared and not used|imported and not used", "unused"),
    (r"called `(?:Option|Result)::unwrap\(\)`", "unwrap"),
    (r"borrow of moved value|use of moved value|cannot borrow", "borrow"),
    (r"undefined: |cannot find (?:value|function)|not found in this scope|cannot find symbol|"
     r"does not exist in the current context", "name"),
    (r"mismatched types|incompatible types|is not a function|is not iterable|is not callable", "type"),
]]

ERROR_LINES = [
    # Python and JavaScript: "NameError: name 'x' is not defined", "Uncaught TypeError: x is not a function"
    re.compile(r"^(?:Uncaught )?(?P<name>(?:[A-Z]\w*)?(?:Error|Exception))(?: \[\w+\])?(?::\s*(?P<msg>.*))?$"),
    # Java and C#: 'Exception in thread "main" java.lang.NullPointerException: …',
    # "Unhandled exception. System.FormatException: …"
    re.compile(r"^(?:Exception in thread \"[^\"]*\" |Unhandled exception\. )(?:[\w$]+\.)*(?P<name>\w+)"
               r"(?::\s*(?P<msg>.*))?$"),
    # Go: "panic: runtime error: index out of range [3] with length 3"
    re.compile(r"^(?P<name>panic): (?P<msg>.*)$"),
    # Rust: "thread 'main' panicked at src/main.rs:4:5:", with the message on the next line
    re.compile(r"^thread '[^']*' (?P<name>panic)ked at (?P<msg>.*)$"),
    # Compilers: "error[E0425]: cannot find value `x` in this scope", "./main.go:5:2: undefined: x"
    re.compile(r"^(?P<name>error)(?:\[E\d+\])?: (?P<msg>.*)$"),
    re.compile(r"^\S+\.(?:go|ts|java):\d+(?::\d+)?: (?:(?P<name>error): )?(?P<msg>.+)$"),
    # pytest: "E       assert 0 == 1"
    re.compile(r"^(?P<name>assert) (?P<msg>.*)$"),
]

LOCATIONS = [
    re.compile(r'File "(?P<file>[^"]+)", line (?P<line>\d+)'),  # Python
    re.compile(r"\bin (?P<file>.+?\.cs):line (?P<line>\d+)"),  # C#: "in C:\app\Program.cs:line 12"
    re.compile(r"(?P<file>[^\s()]+?\.cs)\((?P<line>\d+),\d+\)"),  # the C# compiler: "Program.cs(12,5)"
    # The rest: "src/main.rs:4:5". A Windows path can have spaces, like C:\Users\Jane Doe\app.js:3
    re.compile(r"(?P<file>(?:[A-Za-z]:[\\/][^:()'\"]+?|[^\s:()'\"]+)\.\w+):(?P<line>\d+)"),
]


@dataclass
class Help:
    message: str  # the error as printed, like "NameError: name 'totl' is not defined"
    meaning: str = ""
    kind: str = ""  # the MEANINGS key, for the usage log
    path: Path | None = None  # the user's own file the error points at
    line: int = 0
    code: str = ""  # that line of their code
    recognised: bool = True  # False when `message` is only the last line printed, for errors Stepwise doesn't know


def own_file(project: Project, name: str) -> Path | None:
    """The user's own file an error mentions. Libraries, installed packages and the language's own
    files are skipped, so the help points at code the user wrote."""
    path = project.code_path(name)
    if (path is None or not path.is_file()) and name.endswith(".java") and not re.search(r"[\\/]", name):
        # Java prints only the file name, like Main.java
        matches = [p for p in project.source_files(Path(name).suffix) if p.name == name]
        path = matches[0] if len(matches) == 1 else None
    if path is None or not path.is_file():
        return None
    folders = path.relative_to(project.root).parts[:-1]
    return None if any(f in NOT_SOURCE or f.startswith(".") for f in folders) else path


def error_line(lines: list[str]) -> tuple[str, str]:
    """(name, message) of the error. Python prints it last, under its traceback; the others print it first."""
    python = any(line.startswith("Traceback (most recent call last)") for line in lines)
    order = range(len(lines) - 1, -1, -1) if python else range(len(lines))
    for i in order:
        line = re.sub(r"^E\s+", "", lines[i].strip())  # pytest marks error lines with an E
        for pattern in ERROR_LINES:
            if m := pattern.match(line):
                name, msg = m["name"] or "error", (m["msg"] or "").strip()
                if name == "panic" and msg.endswith(":") and i + 1 < len(lines):
                    msg = lines[i + 1].strip()  # newer Rust puts the panic's message on the next line
                if name == "assert":
                    return "AssertionError", f"assert {msg}"
                return name, msg
    return "", ""


def explain(output: str, project: Project) -> Help | None:
    lines = output.splitlines()
    name, msg = error_line(lines)
    frames = []
    for line in lines:
        for pattern in LOCATIONS:
            if (m := pattern.search(line)) and (path := own_file(project, m["file"])):
                frames.append((path, int(m["line"])))
                break
    if not name and not frames:
        # An error Stepwise doesn't know still ends somewhere: its last line is usually the one to search for.
        last = next((line.strip() for line in reversed(lines)
                     if line.strip() and not re.fullmatch(r"exit(?: status)? \d+", line.strip())), "")
        return Help(last, recognised=False) if last else None
    found = Help(f"{name}: {msg}" if name and msg else name or msg)
    found.kind = next((kind for pattern, kind in MESSAGES if pattern.search(msg)), NAMES.get(name, ""))
    found.meaning = MEANINGS.get(found.kind, "")
    if frames:
        # A Python traceback runs from the outside in, so the deepest of the user's frames is last.
        python = any(line.startswith("Traceback (most recent call last)") for line in lines)
        found.path, found.line = frames[-1] if python else frames[0]
        code = found.path.read_text(encoding="utf-8", errors="replace").splitlines()
        found.code = code[found.line - 1].strip() if 0 < found.line <= len(code) else ""
    return found


def search_text(found: Help, language: str) -> str:
    """What to search for: the error without what only the user's code has (their paths, and the names
    and values in quotes), so it matches other people asking about the same error."""
    words = re.sub(r"\S*[\\/]\S*", "", found.message)
    # Quoted words go ('totl', "abc"), but quoted punctuation stays: "'(' was never closed" needs it.
    words = re.sub(r"Did you mean.*$|'[^']*\w[^']*'|\"[^\"]*\w[^\"]*\"", "", words)
    return " ".join(f"{language} {words}".split())[:200]
