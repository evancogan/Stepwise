# Stepwise
An interactive learning tool in bash

# Why Stepwise?

Stepwise is designed to make you, the human, the vibecoder. It asks you leading questions about your app idea, and then forces you to break it down into 'steps' which you can then tackle one by one. This approach helps you to feel like you're making progress, as well as bring the joy back into problem-solving programming. 

# AI Use

Stepwise does not use any form of AI or AI tooling to help you achieve your goals. The only person writing code is you. The app merely pushes its users to think about their app in an actionable way.

# Quick start

**1. Install it.** Stepwise needs Python 3.11 or newer. [uv](https://docs.astral.sh/uv/) installs it as a command you can run from any folder, and downloads a suitable Python first if you don't have one:

```bash
uv tool install git+https://github.com/evancogan/Stepwise
```

To try it without installing, run `uvx --from git+https://github.com/evancogan/Stepwise stepwise`. Later, `uv tool upgrade stepwise` gets the latest version and `uv tool uninstall stepwise` removes it.

**2. Start a project.** Run `stepwise` and type your app's name. The project goes in `~/Stepwise/<name>`, or under `STEPWISE_HOME` if you set it. To build inside a repo you already have, run `stepwise` there and choose Start here (see [Using it in a repo](#using-it-in-a-repo)).

**3. Answer one page at a time.** Each page asks one thing. Type your answer, then press Tab and Enter to move on. The sidebar opens any stage, and the README preview beside the questions shows where each answer will go.

| Key | Does |
| --- | --- |
| Tab, then Enter | Next page |
| Ctrl+N / Ctrl+B | Next / back |
| Ctrl+R | Show or hide the README preview |
| Ctrl+Q | Quit |

**4. Keep your editor open beside it.** From stage 5 you write the code yourself, in your own editor. Stepwise creates the files you list in stage 4, shows each one beside its pseudo-code as you save, and runs your app and tests for you. If VS Code's `code` command is installed, Stepwise opens files in it for you.

**5. Stop whenever you like.** Answers save after 5 seconds without typing, and whenever you leave a field or quit. To carry on, run `stepwise` in the project folder or any folder inside it, run `stepwise ~/Stepwise/<name>` from anywhere, or type the same name on the start screen.

Everything lives in the project folder: your code, `README.md`, `notes.md` (every answer, by stage) and `.stepwise/`, where Stepwise keeps its own records.

# Using it in a repo

Run `stepwise` inside any git repo and it offers to build your app there. It adds a `.stepwise` folder for your answers and never writes over a file it didn't make:

- If the repo already has a `README.md`, your draft goes to `README.draft.md`, and stage 4 is done once you've brought what you want from it into `README.md`.
- If the repo already has a `notes.md`, Stepwise keeps its notes in `.stepwise/notes.md` instead.
- The usage log stays out of git, so you can commit `.stepwise` to keep your answers with your code.

Run `stepwise` from any subfolder and it finds the project, the way git finds the repo. Outside a repo, new projects go to `~/Stepwise` (or `STEPWISE_HOME`), and `stepwise <folder>` opens or creates a project in any folder.

# Flow

Stepwise has ten stages. Each page asks one thing, and the answers build your README and `notes.md`. The sidebar opens any stage at any time, but only finishing your furthest stage moves you on.

1. **Idea.** Pin your app down before you build anything.
   - Describe your app in a sentence or two. Who is it for, and what does it do for them?
   - Research: a button searches for "how to build your own" plus your app's name, and you add the links that helped. They become the README's Further resources.
   - Your notes: what did you learn? Anything that surprised you or changed your plan.
   - Walk through using your app once, start to finish. What does the user see, and what do they do?
   - Why are you building this, and why build it yourself?
2. **Step Breakdown.** Break the app into steps, in the order you'll build them. Each step should end in something you can run or see.
   - Your steps, one per line.
   - Walk through your app once more using your steps. If a moment isn't covered by any step, go back and add one.
   - Once the first version works, what would you add next?
3. **Pseudo Implementation.** Write how each step works in plain words: the logic, not the code.
   - A short primer on the pseudocode style Stepwise uses (ASK, SHOW, SET, IF / OTHERWISE, REPEAT, FOR EACH, STOP).
   - One page per step, for its pseudocode.
   - What does your app need to keep track of while it runs?
   - What does the user give your app, and what should happen if it's missing or wrong?
4. **README Part One.** Decide what you're building it with, and get it set up, before any code.
   - Where will people use your app: in a browser, on a phone, on a desktop, or in a terminal? (Multiple choice, like the questions below. Phone apps become browser apps, since Stepwise can't run phone apps yet.)
   - Do you already know which language you'll use? If not, six questions about the app and how you like to work rank Stepwise's six languages: what the app mostly does, how it ships (not asked for browser apps), how types are checked, speed and memory, doing things at once, and how errors are handled. Each answer explains the idea behind it, and "Not sure yet" doesn't count.
   - Pick your language from the ranked list, each with the reasons behind its place, or Something else.
   - Does your app need to remember anything, and for whom? How much should your tools do for you? Then pick from a few full stacks for your language and platform, each with a frontend, a backend and where its data lives.
   - Why these? In your own words. The README's Built with lists the language and stack you picked, then your reasons.
   - Your files, each with what it's for. Stepwise creates them for you.
   - What will you write, run and debug it with?
   - Which version of your language does the app need?
   - Your dependency file (requirements.txt, package.json, go.mod, Cargo.toml, pom.xml or a .csproj), shown as you edit it.
   - How does someone get those installed? The steps you'd give a friend.
   - Check your setup: Stepwise checks that your language and the libraries you listed are installed.
   - What one command will start your app?
   - README draft: Stepwise builds Part One from your answers, and you edit it until it reads well.
5. **Syntax Implementation.** Write the real code, one step at a time, in your own editor. Each step's page shows its pseudocode beside the file as you save it, with a Run button for trying your app as you go. A step can only be ticked done once its file has changed since the last step in it was ticked.
6. **App Execution.** Stepwise checks your prerequisites again, this time against what your code imports, then runs your app. If it asks for input, you type it under the output. A failed run shows where the error points in your code, what that kind of error usually means, and a button to search for it, then asks you to explain it in your own words before trying again.
   - It ran! What did you see, and how does it compare to what you described back in stage 1?
   - Try to break it: leave something blank, type something wrong, use a huge number. What happens?
   - Where did your code end up different from your pseudo-code?
7. **Test Steps.** Decide what to test, one thing per line in plain words: the things that would hurt most if they quietly broke.
8. **Pseudo Test Implementation.** A short primer on writing a test as GIVEN, WHEN and THEN, then one page per test to write it that way.
9. **Syntax Test Implementation.** Name your test file, write each test in it, then give the command that runs them. Stepwise runs your tests, and a failure asks which test failed and whether the test or the app is wrong.
10. **Review and README Part Two.** Look back at what you built, then finish your README.
    - Which step did everything else depend on, and how did that play out?
    - Which part was hardest to build, and what made it hard? Your notes from building it are shown beside the question.
    - Which choice from stage 4 would you make differently now, and why?
    - If you started this app over tomorrow, what would you do differently?
    - README Part Two: Stepwise adds the sections your app has earned since Part One, and you edit them.

After stage 10, a Finish page sums up what you built, from your own record.

# What We Learned

- **Saving on every keystroke is a bad idea.** The first version wrote each answer to disk, and rebuilt the notes file, every time a key was pressed. Besides being wasteful, it crashed on Windows: when another program (an editor or sync client) briefly held the notes file open, the save failed and took the app down with it. Answers now save after 5 seconds without typing, or when you leave a field, change stage or quit, and a save that hits a locked file retries instead of crashing.
- **Surprise follow-up questions backfire.** Some questions used to reveal a second prompt, usually "Why?", only after the first was answered. The usage log showed people had often already explained why, so they moved their answer into the new box and wrote a shorter one, or replied "see above." Any "why" is now part of the question itself, so there are no surprises.
- **People can't write for a README they can't see.** Each answer was slotted into the README under a label the user never saw, such as "Built with:" or "What it adds:". Answers that were fine for their question read strangely there, like "Built with: The user sees the gui…". Stepwise now shows a live README preview beside the questions (Ctrl+R toggles it), updated as you type, with a placeholder showing where the current answer will land. README subheadings are now short noun phrases that read right above any answer, not sentence starters the answer has to finish.
- **Too many questions on one screen feels like filling in a tax form.** Stages showed every question at once. Now each page asks one thing, with Next and Back to move between them, and Tab then Enter moves forward.
- **Narrow or vague wording gets misread.** "If you had half the time, which steps would you cut?" read as trimming the app, not planning its future, so the Roadmap question is now "Once the first version works, what would you add next?" "Where does your app run?" sat unanswered through several visits before getting "PyQt6 (Python)", so it now lists the options (browser, phone, desktop, terminal). Questions that asked about "each one" when only one thing had been named were rewritten.
- **Bold isn't a highlight in a terminal.** The README preview first marked the answer being edited in bold. It was technically there, but in the VS Code terminal font bold looks almost the same as normal text, so it seemed broken. The preview now shows that answer in the accent colour on a tinted background, like a highlighter, and doesn't use bold at all. In a terminal, colour and background stand out where font weight doesn't.
- **You can't write about challenges before you've built anything.** Questions about the hardest step or the least certain choice were asked during planning, so the answers were guesses. They now come in stage 10, looking back, where they can draw on what actually happened.
- **A coach can only help with what it can see.** Stepwise used to stop at the plan and leave the user alone in their editor. Now it creates the files the user names, shows each one live beside the step's pseudo-code, and runs the app and the tests itself. Seeing the real output lets it respond to what happened: a failed run asks the user to explain the error in their own words before trying again.
- **Exit codes aren't as reliable as they look.** An unknown command should exit with code 9009 on Windows, but run through Python it exits with 1, the same as any other failure. Stepwise also checks the terminal's own "not recognized" message to tell the two apart.
- **Defaults carry opinions.** The README preview underlined some headings and not others. That was Textual's default Markdown theme, which underlines one heading level and not the next. Overriding it made the headings consistent.
- **There's no single way to write pseudocode.** People write it like Python, like maths, or as plain sentences, which can leave a newcomer unsure what's expected. Stage 3 now opens with a short primer showing the one style Stepwise uses, and links to a comparison of the others.
- **One question can't feed both a README and a terminal.** "How do you start your app?" was meant to be a command Stepwise could run, but it also filled the README's Getting started section. The answer, reasonably, was 13 lines of setup instructions, and running them as one command failed on the first word. Setup steps now have their own question in stage 4 for the README, and the run command is a one-line box, shown with the folder it runs in.
- **Plans drift once real code exists.** The tech stack said PyQt6, but the code ended up importing PySide6, after the official docs pointed that way, and nothing noticed. A new prerequisites list names the language and each library by its import name. Before running the app, Stepwise checks that each one is installed and compares the list with the imports in the code, so a mismatch is caught before it reaches the README.
- **A checkbox alone proves nothing.** Five coding steps were ticked done in seven seconds, because they all lived in one file that already had code in it. A step can now only be ticked once its file has changed since the last step in that file was ticked.
- **"The name you import" isn't the same as "the thing you install".** Asked to list libraries by their import names, the user copied their import lines: sys, PySide6, QtCore, QtWidgets and QtGui. The check then said QtCore wasn't installed, which led to `pip install QtCore`, a package that doesn't exist. QtCore comes inside PySide6, and sys comes with Python. The question now asks only for what you had to install, and the check reads the code to tell a library apart from a part of one or a built-in. Instead of an error, it explains why those don't need their own line.
- **Use the file the language already has.** Patching the hand-typed prerequisites list for Python didn't help any other language, and the list kept mixing up what you import with what you install. Every language already has a file for this job (requirements.txt, package.json, go.mod, Cargo.toml, pom.xml, .csproj), and anyone downloading the app will need it anyway. Stepwise now has the user write that file, reads it, and compares it with the imports in their code, for Python, JavaScript, Go, Rust, Java and C#.
- **Ask the installed tool before trusting a saved list.** What counts as built in changes between versions, so Stepwise asks the user's own Python, Node or Go for its list, and falls back to lists fetched from each language's official docs only when the tool isn't installed. Java, Rust and C# have no command that lists them, so they always use the saved list. The check says which source it used. C# has no clean public list at all, so it uses Microsoft's documented roots, and Java and C# report unlisted imports as notes, not errors, because their import names don't map reliably to package names.
- **Let people look ahead.** Locking every stage until the one before was finished made Stepwise hard to show anyone, and hard to check a new feature that lives at a later stage. Every stage can now be opened from the sidebar. Stages you haven't reached are dimmed, and any panel that needs something you haven't made yet (steps, files, a command) is greyed out with a line saying what it's waiting for. Looking ahead never counts as progress: only finishing your furthest stage moves you on. Opening stages early also exposed three bugs: a crash on stage 5 with no steps, an empty run command that counted as a successful run, and README Part Two being added before Part One existed. All three are guarded now.
- **Finishing should feel like finishing.** The end of stage 10 used to be a plain "You built it" page. It's now a congratulations page that uses the user's own record: how many steps they built, how many runs it took to get working (and that they explained every error), their tests, the advice they'd give themselves next time, and what they said they'd add next. Like every other stage, it can be opened at any time from the sidebar's Finish row, so it can be shown to people before a project is done. Nothing is locked; it just shows whatever has been done so far.
- **A checkmark should mean the user did something.** New projects showed ticks beside pages nobody had touched: a dependency check with no files to fail on, read-only primers, and optional pages with no input. Each page's tick now comes from real input: the dependency file needs files listed first, research needs a link added, and pages on stages you haven't reached never show a tick.
- **Research is where a lot of the learning happens, so give it somewhere to go.** The research page had only a search button, so what a user found had no place to be written down. It now has a notes box that feeds a "What I learned from research" README section. A new section was needed because putting the notes under "Challenges and what I learned" would have made that section exist at stage 4, and Part Two skips sections the README already has. Notes also went stale while the same fix was being made: only leaving a field rebuilt `notes.md`, not the 5-second idle save, so the idle save now rebuilds it too.
- **Search, collect and reflect are three different jobs, so don't crowd them.** The research page was a lone search button, with the links on the next page and the notes box squeezed in beside the search. Search and link entry now share one page (search first, links below, so the links come from what was just found), and the notes get a page to themselves so a longer "what I learned" has room. The notes keep the same answer key, so they still feed the "What I learned from research" README section.
- **Let people see what they're biting into.** Next used to refuse to leave a page with a missing answer, and then a "Not done yet" check stopped you at the end of a stage, even though the sidebar let you jump anywhere. A lock that can be walked around only gets in the way, and someone sizing up the whole process should be able to click straight through it with nothing filled in. Nothing blocks Next now. The sidebar ticks and the generated README still show exactly what's missing.
- **Don't let the tool's data live in the tool's own repo.** Projects were created in whatever folder Stepwise was launched from, so running it from its own source folder filled the repo with sample projects. New projects now go to `~/Stepwise` (or `STEPWISE_HOME`), and the old samples were moved there. Nothing broke on the move because every run, file check and dependency lookup works from the project's own folder, not from where Stepwise was started.
- **A tool dropped into someone's repo can't assume the folder is empty.** Stepwise only ever ran in folders it had made, so it rebuilt `notes.md` on every save without looking at what was there, counted a repo's existing README as the user's README Part One, and searched every folder for the user's own modules, `node_modules` and `target` included. It now leaves a `notes.md` or README it didn't write alone, skips folders of installed libraries and build output, finds its project from any subfolder, and offers to start in the repo it's run from.
- **A plan that says "run each step" needs a way to run each step.** Stage 2 asks for steps that each end in something you can run or see, but nothing could run until stage 6, after every step was written, and the libraries weren't checked until then either. The run command and a first setup check now come in stage 4, and every stage 5 step has a Run button for trying the app as it grows. Those runs are only for trying it out: stage 6 is still the run that counts.
- **An app that asks a question needs somewhere to answer it.** The run panel read the app's output a whole line at a time and never connected its input, so a terminal app's `input("Total: ")` never showed its prompt and nothing typed could reach it, even though the pseudocode primer's own example starts with ASK. Output now shows as it's printed, so a prompt appears straight away, and a box under it sends what you type to the app. Full-screen terminal apps still need a real terminal.
- **Asking someone to explain an error helps more once they can read it.** A failed run asked the user to explain the error in their own words, but a beginner faced with a traceback often can't tell which line is theirs. Stepwise now picks out the error, points at the line of the user's own code it came from (skipping library code), and says in plain words what that kind of error usually means, without saying how to fix it. A search button looks the error up, leaving out the paths and quoted names that only the user's code has, so it finds other people asking about the same error. For an error Stepwise doesn't recognise, it searches for the last line the app printed.
