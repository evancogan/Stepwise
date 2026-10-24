# Mock-user testing: handoff (paused 2026-10-23)

Test tooling only. Stepwise never uses AI and nothing in `stepwise/` imports anything here.

## What's here

- `mock_user.py` drives the real Stepwise app headlessly (Textual's Pilot), in two modes:
  - `run`: the harness drives and asks a local model (LM Studio / Bionic, OpenAI-compatible API) to
    answer each page as a persona. Works, but on this laptop (CPU inference, Qwen 3.6 35B-A3B with
    thinking on) it takes about 3.5 minutes a page.
  - Turn commands (`start`, `screen`, `type`, `pick`, `press`, `next`, `back`, `open`, `edit`): an agent
    drives, one action per call. Each call reopens the project where the agent left off
    (`.stepwise/mock-at`), acts, and prints the stage pane in Stepwise's own words. VS Code, the
    browser and notifications come back as text lines. Runs stop after stage 4 (`END_STAGE`).
- `personas.json`: seven personas (maya, dev, sam, priya, leo, ana, tomas).
- `../.claude/agents/mock-user.md`: the Haiku agent definition (Bash, WebSearch, WebFetch). Agents
  load at session start, so in the session that made it the run used a general-purpose Haiku agent
  with the same instructions pasted into its prompt.

Mock projects live in `~/Stepwise-mock/<app-slug>/`. Each has `.stepwise/mock.jsonl` (every action,
with the persona's `--why`, plus `picked` / `offered` / `best` on choice pages) and
`.stepwise/mock-shots/` (an SVG per turn, `latest.svg`, `latest.json` and a live `index.html`).

## Watching a run live

Serve `~/Stepwise-mock` and open `/<app-slug>/.stepwise/mock-shots/index.html`; it reloads the
newest screenshot every second. In the desktop app that was a local `.claude/launch.json` (not
committed, since it holds a home-folder path):

    {"version": "0.0.1", "configurations": [{"name": "mock-live", "runtimeExecutable": "python",
      "runtimeArgs": ["-m", "http.server", "8765", "--directory", "C:/Users/<you>/Stepwise-mock"],
      "port": 8765}]}

## Results so far

- **Maya, Haiku agent: done, stages 1-4, nothing stuck.** About 10 minutes for 33 pages. Real
  research links (both checked, both load), in-character answers, valid pseudocode, Python picked as
  the Best match, plain print/input stack, setup check passed, README draft properly edited.
  Project: `~/Stepwise-mock/tip-splitter`.
- **Maya, Qwen (local): stopped partway into stage 4** (killed to save battery). Its research links
  were invented. Kept at `~/Stepwise-mock/tip-splitter-qwen` for comparison.
- No other persona has been run with the agent yet.

## Findings to act on

1. **Stage 4's language questions are full of jargon for beginners.** The hints in
   `stepwise/choices.py` mention GIL, JIT, `Result<T, E>`, goroutines and garbage collectors. Maya
   answered "Not sure yet" or picked what sounded familiar, and "Help me choose" asks all seven
   questions regardless. Earlier design goal to keep: experienced programmers should still find
   them useful. Ideas: a plain-words first line per option with the technical detail after, or an
   early "I'm new to this" path that skips to a sensible default.
2. **The language version page (`lang.version` in `stepwise/stages.py`) doesn't say how to find
   your version.** Maya wrote "Python 3, probably the newest". The setup check still handled it.
3. Smaller: the stage 3 pseudocode intro is long for a 16-year-old, and the optional Wikipedia link
   reads as required.

## Next steps

- Decide on finding 1, then rerun Maya to see whether it reads better.
- Run the other personas one at a time (Dev and Tomás test the "already decided" path; Sam and
  Leo test vague answers).
- Known gaps: an agent can't install anything, so a persona whose stack needs libraries will stop
  at the stage 4 setup check, and runs end at stage 4 until stages 5+ get turn support (running
  code).

## Gotchas

- `lms` can't reach Bionic's server from this machine (it times out starting its own daemon);
  load and eject models in Bionic itself.
- Textual passes `print` through to stdout while running but never flushes, so `main()` makes stdout
  line-buffered; otherwise piped logs only appear when the app exits.
- With thinking on, a local model's reasoning counts toward `max_tokens`; 8000 is the floor that
  worked (16000 for the README edit).
