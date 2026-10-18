# Stepwise: design

Stepwise is a guided way to learn programming. You start with an idea, break it into steps, write each step
in plain-words pseudocode, and then turn that pseudocode into Python one line at a time, with help that
appears where you need it and fades as you learn.

## The need

Programming used to carry a heavy syntax tax: before you could build anything, you had to memorize colons,
brackets and keywords, and look things up in docs that never used your words. AI tools removed that tax, but
took ownership with it. When a model writes the program, the learner learns little and the result never
quite feels like theirs.

Stepwise sits in between. The learner does all of the thinking and writes every line. The tool takes away
the parts that are only friction: finding the right construct, remembering its shape, and decoding error
messages. The finished program is a record of the learner's own decisions, written in their own words
first.

## Principles

1. **The learner writes every line.** Nothing goes into their program that they did not type.
2. **Code judges and explains.** Whether a line is right, what it says, and why it fails are worked out by
   code (parsing, running, checking), so the answers are always correct and the same every time.
3. **Help fades.** The first time a construct comes up, the learner sees all of it; each time after, they
   see less, until they don't need it.
4. **Plain words first.** Every stage starts in the learner's language and only then moves to Python.
5. **Warm, friendly, very easy.** One clear screen at a time, short sentences, colors that help, arrow keys
   instead of commands.
6. **Works offline, anywhere.** No model, no account, no network. Python and a terminal are enough.

## The guided flow

Each stage is one clean screen, redrawn in place. Nothing is appended below old output.

1. **Idea.** "What do you want to build?" The learner types an idea in their own words.
2. **Steps.** "What are the steps to build it?" The learner lists them; each new line gets the next number
   on its own (1., 2., 3., ...). The steps can be reordered, edited or removed with the arrow keys.
3. **Pseudocode.** For each step in turn: "How would you do this step in pseudocode?" The learner writes a
   few plain lines. This repeats until every step has pseudocode.
4. **Syntax.** The learner turns each pseudocode line into Python, step by step, with the syntax layer
   (below) helping.
5. **Run and check.** The program runs as the learner writes it. Tests (written the same way: plain words,
   then Python) go red, then green. Errors come with plain explanations. At the end, a bug quiz changes one
   line of their code and asks whether a test notices; if none does, the learner writes one that does.

## The syntax layer

This is the heart of Stepwise: how a learner gets from a pseudocode line to working Python without a
manual.

### Side by side, with read-back

The learner's pseudocode is on the left and their Python on the right, lined up. An empty right-hand line
is the next thing to write.

```
 Step 2: the snake moves                    your Python
 ─────────────────────────────────────────  ─────────────────────────
 repeat for every part of the snake          for part in snake:
   move the part one cell to the right         part.x = part.x + 1
                                                ↳ part.x is set to part.x + 1   ✓
 if the head hits the wall                   ▌
   the game is over
```

As soon as a Python line is written, Stepwise reads it back in plain English under the line (the read-back
is done by code, not guessed). The learner compares the read-back with what they meant. If "move the part
one cell to the right" comes back as "part.y is set to part.y + 1", the mismatch is right there, and finding it
is the lesson.

When a step is done, its pseudocode stays in the program as comments above the code it became. The final
file shows the learner's thinking and their code together.

### Syntax cards

Stepwise recognizes the shape of a pseudocode line and offers the matching construct as a card, filled in
with the learner's own names:

| Pseudocode line | Card | Shown as |
|---|---|---|
| repeat for every part of the snake | for each | `for part in snake:` |
| repeat 3 times | for range | `for _ in range(3):` |
| if the head hits the wall | if | `if ___:` |
| set score to 0 | variable | `score = 0` |
| add 1 to score | change a variable | `score = score + 1` |
| show the score | print | `print(score)` |
| ask for their name | input | `name = input("___")` |

The catalog covers the constructs beginners use most, about 25 in all: variables, print, input, if / elif /
else, comparisons, and / or / not, while, for range, for each, lists, append, indexing, dictionaries,
functions, return, calling a function, classes, `__init__` and `self`, attributes, methods, import, f-strings,
string methods, try / except, and random.

Each card holds:

- the pseudocode phrases that point to it;
- a template with holes (`for ___ in ___:`);
- a tiny example the learner can run on the spot and change;
- its common mistakes, written as friendly explanations (a missing colon, `=` instead of `==`, wrong
  indentation);
- a one-line description of when to use it.

### Help that fades

Help is tracked per construct, per learner:

| Time seen | What the card shows |
|---|---|
| First | The whole line with the learner's names. They type it out (no paste); typing is how it sticks. |
| Second | The template with holes: `for ___ in ___:` |
| Third | Only the construct's name: "this is a for-each loop" |
| After that | Nothing, unless the learner asks (key `h`) |

A construct the learner gets wrong moves back one level. A construct they write correctly without help
moves forward.

### Other exercises

- **Parsons problems.** The first time a construct appears, the learner can arrange its lines (shuffled)
  into the right order with the arrow keys. Recognizing the right shape comes before writing it from
  nothing.
- **Reverse exercises.** Show a Python line and ask the learner to say it in pseudocode; the read-back
  checks the answer.
- **Errors in context.** A `SyntaxError` on `for part in snake` becomes "a `for` line ends with a colon:
  `for part in snake:`", shown with the card it belongs to.

## Recognizing constructs from pseudocode

Stepwise suggests a small set of sentence starters, each mapping to a card:

| Starter | Card |
|---|---|
| repeat ... times / repeat for every ... / repeat while ... | for range / for each / while |
| if ... / otherwise if ... / otherwise | if / elif / else |
| set ... to ... / add ... to ... | variable / change a variable |
| ask for ... | input |
| show ... | print |
| make a ... that has ... | class / `__init__` |
| to ... (a named action) | function |
| give back ... | return |
| a list of ... / add ... to the list | list / append |

Learners can write freely; when a line matches no starter, Stepwise says which starters come close and lets
the learner pick the card themselves. Matching is done by code (phrase patterns), never by a model.

## Screens and interaction

- **One screen per stage**, cleared and redrawn, so choosing an option shows only its result. A header
  says where the learner is (stage, step k of n).
- **Arrow-key picker** for every choice, with a typed-number fallback when the input isn't a terminal.
- **Keys:** `h` hint, `t` switch the read-back between Given / When / Then and Arrange / Act / Assert (for
  tests), `n` next, `q` quit.
- **Glossary.** A panel of the names the learner has introduced (classes, attributes, variables), taken
  from their own code and pseudocode, so "what is `game.bird`?" is answered by their own design.
- **Where code is typed:** either in the learner's own editor (VS Code) while Stepwise watches the files and
  reacts on each save, or in the TUI itself. See open questions.

## What carries over from Loop

Stepwise starts from parts of the Loop app builder (`C:\Repos\Loop\appbuilder`), copied in and trimmed:

| Loop file | Use in Stepwise |
|---|---|
| `explain.py` | Read-back of code into plain English, in both styles. Today it reads test code; it needs to grow to cover app code (def, class, return, while, comparisons, print, input). |
| `testlint.py` | Explains weak tests: ones that can never fail, contradict others, or add nothing new. |
| `testrun.py`, `_run_unittests.py`, `sandbox.py` | Runs the learner's tests safely, with per-test results and repeated errors grouped. |
| `safety.py` | Blocks file and system calls in code the tool runs. |
| `quality.py` | Mutation testing for the bug quiz, and coverage for "these lines are never tested". |
| `invariants.py`, `_probe_game.py` | Sanity checks for game projects (Game, step(), game_over). |
| `ui.py` | Colors and the arrow-key picker. |

Left behind: the model client, prompts, the AI code writer, the model capability check, and the AI parts of
the review screens. Stepwise has no model in its core.

## Data

- **Card catalog:** one file per card (JSON), holding phrases, template, example, common mistakes and
  description. Adding a construct means adding a file.
- **A project folder** per idea: `idea.txt`, `steps.txt`, the pseudocode for each step, the learner's
  Python (pseudocode kept as comments) and their tests.
- **Progress:** per construct, the current help level; plus hints used and bug quizzes caught. Stored
  locally, never sent anywhere.

## AI's place (open)

The core works with no model at all, and the MVP is built that way. A small local model could later be added
as an option, for narrow jobs only, under one rule: **it may suggest, never commit, and every line is read
back by code.** Candidates:

- picking a card for a free-form pseudocode line that matches no starter;
- the "point at a line and say what it should be" fix, applied to the learner's pseudocode rather than to
  their code.

## MVP

- The full flow, idea to bug quiz, for small text and logic apps and for Snake logic (no window).
- About 12 cards: variables, change a variable, print, input, if / else, comparisons, for range, for each,
  lists, functions, return, classes with `__init__`.
- Side-by-side view with read-back, fading help, and errors explained in context.
- Parsons problems and reverse exercises can follow right after.

## Open questions

- Python only, or other languages later?
- Who is the first learner: total beginners, early students, or self-taught hobbyists?
- Learner's own editor with a file watcher, or typing inside the TUI?
- Voice input, so "say what it should be" is literal?
- Ready-made projects (Snake, a to-do list) alongside the learner's own ideas, or only their own ideas?
