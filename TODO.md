# To do

What's left to make Stepwise make sense for developers, from a review of how it installs and how its stages match real development. Tick items off as they land.

## Installing it

- [ ] **Make the GitHub repo public.** Everything below depends on it: until then `uv tool install git+…` and `uvx --from git+…` only work for the owner.
- [ ] **Publish to PyPI.** The name `stepwise` is taken by an unrelated project, so publish as something like `stepwise-coach` and keep the command `stepwise`. Then `uvx --from stepwise-coach stepwise`, `pipx install stepwise-coach` and `pip install stepwise-coach` all work. A GitHub Action can publish each tagged version.
- [ ] **A Codespaces template.** A template repo with a `.devcontainer` that installs Stepwise and the common languages, so a learner can click "Open in Codespaces" and run `stepwise` in the browser with nothing installed locally.
- [ ] **Standalone executables.** PyInstaller builds on GitHub Releases for people without Python, such as someone building in JavaScript or Go. They still need their own app's language, which Stepwise already checks for.
- [ ] **Contributor setup.** Add a `uv.lock`, use `uv run stepwise` as the dev loop, and add a `tests/` suite. The repo's `.venv` currently has PySide6 from a sample app but not Textual, so it can't run Stepwise.
- [x] **Safe to drop into an existing repo.** Never writes over a `notes.md` or README it didn't make, skips library and build folders when scanning, finds the project from subfolders, and offers "Start here" in a git repo.
- [x] **Quick start in the README.**

## The stages

- [x] **Run as you build.** Stage 2 says each step should end in something you can run, but the first run was in stage 6, after every step was written.
  - [x] Ask the run command in stage 4, so it's known before any code is written.
  - [x] Check prerequisites at the end of stage 4, so the language and libraries are installed before coding starts. Stage 6 still checks again, against the imports in the finished code.
  - [x] A Run button on each stage 5 step, for trying the app while building it. These runs don't count as the stage 6 run.
- [ ] **Terminal apps that ask for input.** The run panel didn't connect the app's input, and only showed output a whole line at a time, so `input("Total: ")` never showed its prompt and nothing typed reached the app. Yet the pseudocode primer's own example starts with `ASK the user for the total`.
  - [x] Show a prompt as soon as it's printed, and add a box that sends a line to the running app.
  - [ ] Full-screen terminal apps (curses, a terminal game) need a real terminal. Suspend Stepwise and run them there.
- [x] **Help with runtime errors.** A failed run only asked the user to explain the error. Without giving the fix, Stepwise now points at the line in the user's own file, says in plain words what that kind of error usually means, and offers to search for it.
  - [ ] Grow the list from real use. Every failed run logs an `error_help` event to `.stepwise/usage.jsonl`, and one with no `kind` is an error Stepwise couldn't explain yet.
- [ ] **Version control.** Git appears nowhere in the stages. Suggest committing after each finished step and check `git log` that it happened, the way a tick already checks that the file changed. Add `git init` to stage 4's setup for new projects.
- [ ] **Draft tests alongside the steps.** Testing is completely separate from building. Writing each step's GIVEN/WHEN/THEN beside its pseudocode in stage 3 would mean stage 7 starts with tests already drafted. Allow more than one test file.
- [ ] **Shipping it.** Stage 4 asks where people will use the app, but nothing gets it there: pushing to GitHub, hosting it, building an executable. Add a stage or page for it, and for having someone else try it.
- [ ] **A second round.** "What would you add next" is collected in stage 2, but the finish page is a dead end. "Start version 2" should turn the roadmap into new steps and loop through stages 2–10 again, keeping the project.
- [x] **Keep the README's Flow section in step with the code.** It listed questions Stepwise no longer asks.
