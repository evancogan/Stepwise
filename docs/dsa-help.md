# DSA help: design

The design for [#2](https://github.com/evancogan/Stepwise/issues/2), the first part of [#1](https://github.com/evancogan/Stepwise/issues/1). Issues #3 to #7 build on it, so each section below says which issue uses it. Nothing here is built yet.

The idea comes from the Python LeetCode Cheat Sheet artifact: a pattern finder that asks yes/no questions and ends on a pattern, with a short code template for it.

## Rules it keeps

- **Stepwise never uses AI.** The tree, the type map and the templates are data files in the package. Templates may be drafted with AI while working on Stepwise, but each is reviewed and tested before it's committed.
- **The user writes every line.** A template is shown read-only in the help screen, like a docs page. Nothing is ever written into the user's files. Template names stay generic (`nums`, `target`), so fitting it to their step is still their job.
- **It adds nothing for anyone who doesn't need it.** No new stage and no new required page. The help is only behind a button.
- **The wording is original.** As the artifact's notes say, nothing is copied from AlgoMonster's flowchart or anywhere else.

## Where the button goes (#7)

An **I need help** button, with one line beside it that says what it's for: *Not sure how this step should store or find what it works with?*

It shows on two kinds of page, and nowhere else:

| Page | Why there |
|---|---|
| Stage 3, each step's pseudo-code page (`pseudoN`) | This is where the decision is made: writing pseudo-code means deciding what the step keeps track of. |
| Stage 5, each step's code page (`code` pages for steps) | Where someone gets stuck turning the plan into code. It sits next to the existing *Stuck?* box. |

Not on test pages (stages 8 and 9): tests don't choose data structures.

## The help screen (#7)

A `ModalScreen` pushed over the current page, so closing it (Esc, or a Close button) returns to the same page with nothing lost. Before it opens, the app calls `save_all()`, so it sees the latest pseudo-code.

From top to bottom:

1. **The step it's about.** "Step 2 of 4: Add a task", and that step's pseudo-code (`pseudoN`), quoted. This is what makes the questions mean something: they're about this step, not about DSA in general. If the pseudo-code is empty, it says so and still works.
2. **The question,** with its hint, and Yes / No buttons.
3. **The trail** of answers so far, with **Back** and **Start over**.
4. **The result,** once the tree reaches one (below).

Picking a single line of pseudo-code to pin at the top is left for later.

### What the result shows

- The pattern's name, when it applies, and what it costs (time and space).
- The tool to use **in the project's language**, from the pattern's `tool` entries (below). Python's `heapq` means nothing to someone writing Go.
- "Also consider", when the pattern has one.
- **The template**, picked by stage and language:

| Situation | Template shown |
|---|---|
| Stage 3 (no language chosen yet), or the language is "Something else" | The pattern's pseudo-code, in Stepwise's pseudo-code words (`ASK · SHOW · SET · IF / OTHERWISE · REPEAT · FOR EACH · STOP`) |
| A full template exists for the project's language (#5) | That template |
| No full template for that language | The generated skeleton (#4): the signature in that language, with the pseudo-code as comments |
| The skeleton can't be generated for that language | The Python template, with a note saying so |

The language is the answer to `choose.language`: `python`, `javascript`, `go`, `rust`, `java`, `csharp` or `other`.

The template is a read-only, syntax-highlighted `TextArea`. Copying out of it is allowed, for now (see [Still open](#still-open)).

### What it remembers

The last result for each step is saved as an answer, `help{n}.pattern` (the pattern id). It's added to the per-step keys in `store.py` (`"steps": ["pseudo{n}", "code{n}.file", …]`), so it moves with the step when steps are reordered or removed. The step's pages show it as a short line, "Last help: Sliding window", which reopens the help screen on that result.

It doesn't go into the README or `notes.md`. Whether it should is still open.

### Logging

Like `error_help`, every use is logged to `.stepwise/usage.jsonl`, so real use shows which questions confuse people:

```
dsa_help  action=open    stage=3 step=2
dsa_help  action=answer  key=window_rule yes=true
dsa_help  action=back
dsa_help  action=result  pattern=sliding template=full language=go
dsa_help  action=close   pattern=sliding
```

`template` is one of `pseudo`, `full`, `skeleton` or `python`.

## Files

```
stepwise/
  help/
    tree.json                  questions and results (#3)
    types.json                 the type map (#4)
    patterns/
      sliding/
        pattern.json           signature, pseudo-code, tools (#4, #5)
        python.py              full templates, one per language (#5)
        go.go
        ...
  patterns.py                  loads the data, walks the tree (#3)
  skeleton.py                  writes a skeleton from a signature (#4)
  helpscreen.py                the help screen (#7)
tests/
  test_patterns.py             tree checks and routing (#3)
  routes.json                  known problems and where they should land (#3)
  test_skeleton.py             skeleton output (#4)
  templates/                   a test harness per pattern per language (#5)
  run_templates.py             compiles and runs the template tests (#5)
```

`pyproject.toml` adds `"help/**/*"` to `package-data`, so the data ships with the package.

Tests use the standard library's `unittest` (`python -m unittest`), so there's no new dependency. This starts the `tests/` folder the TODO asks for.

## The question tree (#3)

`tree.json` holds what the artifact keeps in its `Q` and `R` objects, minus the templates:

```json
{
  "start": "design",
  "questions": {
    "c_window": {
      "key": "window_rule",
      "text": "Can you grow a window and shrink it while a rule must hold?",
      "hint": "The longest or shortest stretch with no repeats, at most k distinct values, ...",
      "yes": "r:sliding",
      "no": "c_sum"
    }
  },
  "results": {
    "sliding": {
      "name": "Sliding window",
      "when": "Grow the right edge each step. When the window breaks the rule, shrink from the left.",
      "cost": "O(n) time",
      "also": "Prefix sums with a dict, if negative numbers are allowed."
    }
  }
}
```

- A target starting with `r:` is a result. Anything else is another question.
- A question's `id` can change freely. Its `key` must not: tests describe a problem by the keys it answers yes to, and #6 rewords questions without touching keys.
- Every result id matches a folder under `patterns/`.
- The first yes wins, so specific questions come before general ones, as in the artifact.

`patterns.py`, pure Python with no Textual:

```python
tree = load_tree()             # reads tree.json and checks it (below); raises if it's broken
walk = Walk(tree)              # starts at tree["start"]
walk.question                  # the current question, or None once there's a result
walk.result                    # the result, or None
walk.answer(yes=True)
walk.back()
walk.restart()
walk.trail                     # [(key, yes), ...]
route(tree, {"graph", "shortest"})   # follows the tree, answering yes only to these keys; returns a result id
```

`load_tree` checks, and the tests check again:

- every question is reachable from `start`
- every result is reached by something
- no target is misspelled
- every result has a pattern folder

`routes.json` lists known problems, each as the set of keys answered yes and the pattern it should land on. The artifact's notes mention about 165 from an earlier round. They weren't saved, so #3 writes them again.

## Patterns and skeletons (#4)

Each `pattern.json`:

```json
{
  "signature": {
    "name": "longest valid",
    "params": [["s", "text"], ["k", "int"]],
    "returns": "int"
  },
  "pseudo": "SET left TO the first position\nFOR EACH position, as right:\n    SET the count of the item at right TO one more\n    REPEAT while the window breaks the rule:\n        SET the count of the item at left TO one less\n        SET left TO the next position\n    SET best TO the bigger of best and the window's length\nSHOW best",
  "tool": {
    "any": "a map of counts",
    "python": "dict / Counter",
    "javascript": "Map",
    "go": "map[rune]int",
    "rust": "HashMap",
    "java": "HashMap",
    "csharp": "Dictionary"
  }
}
```

- **`name` is words, not code.** The generator applies each language's convention: `longest_valid` in Python and Rust, `longestValid` in JavaScript, Go and Java, `LongestValid` in C#.
- **Neutral types:** `int`, `float`, `text`, `bool`, `list[T]`, `set[T]`, `map[K, V]` and `grid[T]` (a list of lists). That covers the artifact's templates. Add a type only when a pattern needs it.
- **Patterns that are classes** (LRU cache, trie, union-find) use `"methods"`, a list of signatures, in place of a single signature, plus `"class": "union find"`.
- **`tool.any`** is shown in stage 3 and for "Something else". Any language missing from `tool` falls back to `any`.

`types.json` maps each neutral type to each language:

| Neutral | Python | JavaScript | Go | Rust | Java | C# |
|---|---|---|---|---|---|---|
| `int` | `int` | `number` | `int` | `i64` | `int` | `int` |
| `text` | `str` | `string` | `string` | `&str` | `String` | `string` |
| `bool` | `bool` | `boolean` | `bool` | `bool` | `boolean` | `bool` |
| `list[T]` | `list[T]` | `T[]` | `[]T` | `Vec<T>` | `List<T>` | `List<T>` |
| `set[T]` | `set[T]` | `Set<T>` | `map[T]bool` | `HashSet<T>` | `Set<T>` | `HashSet<T>` |
| `map[K, V]` | `dict[K, V]` | `Map<K, V>` | `map[K]V` | `HashMap<K, V>` | `Map<K, V>` | `Dictionary<K, V>` |

Java needs boxed types inside generics (`List<Integer>`, not `List<int>`), so `types.json` gives Java a `boxed` form for each primitive. JavaScript types go in a JSDoc comment, since the language has none. Imports each type needs (`java.util.*`, `std::collections::HashMap`, `System.Collections.Generic`) come from `types.json` too.

`skeleton.py`:

```python
skeleton(pattern_id, language) -> str   # the signature, any boilerplate, and the pseudo-code as comments
```

The body is the pseudo-code as comments, then whatever the language needs to compile (`return 0`, `todo!()`, `throw new UnsupportedOperationException()`), so the skeleton builds as-is.

## Full templates (#5)

`patterns/<id>/<language>.<ext>`: `python.py`, `javascript.js`, `go.go`, `rust.rs`, `java.java`, `csharp.cs`. Each is a complete, idiomatic function or class, short, with generic names. If the file exists, the help screen shows it. If it doesn't, the skeleton is shown.

Each one has a harness in `tests/templates/<id>/` that calls it on a tiny input and checks the output. `run_templates.py` compiles and runs every one in its own language. A template without a passing test isn't committed.

The cloud environment has Python, Node, Go, Java and Rust. It has no .NET, so C# can't be compiled there yet. Until it can, C# gets skeletons only.

## Still open

These don't block #3 to #5:

- Whether copying out of the template is allowed, or the user has to type it. Allowed for now.
- Pinning one line of pseudo-code at the top of the help screen.
- Whether the chosen pattern goes into `notes.md` or the README, as a small decision log.
- Which patterns get full templates first (#5). Heaps and BFS, where the standard libraries differ most, are the obvious start.
- The question wording (#6). Some questions are shaped around LeetCode and need rewording around the user's app.
