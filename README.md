# Stepwise
An interactive learning tool in bash

# Why Stepwise?

Stepwise is designed to make you, the human, the vibecoder. It asks you leading questions about your app idea, and then forces you to break it down into 'steps' which you can then tackle one by one. This approach helps you to feel like you're making progress, as well as bring the joy back into problem-solving programming. 

# AI Use

Stepwise does not use any form of AI or AI tooling to help you achieve your goals. The only person writing code is you. The app merely pushes its users to think about their app in an actionable way.

# Flow

The steps in stepwise are as follows:

1. **Idea Generation**: You start by coming up with an app idea. This is saved as your intent.
Questions: 
- If you could only ship one screen, what would be on that screen?
- What's the one thing this app does that nothing else you've used does?

   This stage ends with a research page: a button opens a Google search for "how to build" plus your idea, and you list the links that helped. They become the README's Further resources.


2. **Step Breakdown**: The app then prompts you to break down your idea into smaller, manageable steps.
Questions:
- Which step, if you got it wrong, would break everything after it?
- Which steps depend on something you haven't built yet, and which could you start today?
- If you had half the time, what would you cut, and what would the app lose?
3. **Pseudo Implementation**: You then attempt to implement each step in a pseudo manner, focusing on the logic rather than the actual code.
Questions:
- For each step, what goes in, what comes out, and what does the app have to remember between runs?
- Where does your logic depend on outside input, and what happens when that input is missing or wrong?
- Which part of your pseudo-code would be hardest to explain to someone who doesn't know your app?
4. **README Part One**: You start drafting the README for your app, capturing the initial idea, steps, and most importantly, stack and frameworks, dependencies, and any other relevant information. This is effectively a research step, but the user must have a clear idea of what stack they will need, as the syntax is relevant for the next step.
Questions:
- Where does this app run, and who needs to open it there?
- What does the user see, what handles the logic, and where does the data live? Name one tool for each and say why you chose it.
- Which of your choices would be expensive to change in six months? Research those first.
- For each library, what problem does it solve that you couldn't solve in a few hundred lines? What does it cost you?
- Which part of the system must talk to which other part, and what breaks if one side is slow?
- Which choice are you least sure about, and what's the cheapest way to test it before you commit?
5. **Syntax Implementation**: You then translate your pseudo implementation into actual code, ensuring that the syntax is correct and the program functions as intended.
Questions:
- Before you write a function, what does it promise its callers, and what does it not promise?
- Where does state live, and which code is allowed to change it?
- When something breaks, can you say what you expected and what you got? If not, that's what you need to learn next.
6. **App Execution**: Finally, you run your app to see it in action, rewarding you with the fruit of your own work and progress.
Questions:
- What's the smallest path through the app that runs end to end, touching every layer?
- What would someone who didn't build it try first, and what would they expect to happen?
- What did running it teach you about your design that you didn't expect?
7. **Test Steps**: After completing execution, you write tests in steps to make sure each part of your app works correctly and as intended.
Questions:
- Which part of the app, if it broke silently, would do the most damage?
- What's the simplest check that would tell you that part still works after a change?
- If this test passes, what has been proven, and what hasn't?
8. **Pseudo Test Implementation**: You then attempt to write tests in a pseudo manner, focusing on the logic and structure of the tests rather than the actual code.
Questions:
- For each test, what's the setup, the action, and the expected result?
- What input would most likely break your logic, and is there a test for it?
- If you rewrote the internals, would your tests still be valid? Are you testing behavior or implementation?
9. **Syntax Test Implementation**: Finally, you translate your pseudo tests into actual test code, ensuring that the tests are correctly implemented and effectively validate your app's functionality.
Questions:
- Does your testing framework fit how you structured your modules, or do you need to change one?
- When a test fails, can you tell from the message alone what went wrong?
- Which test would you trust least, and why?
10. **Review and README Part Two**: Finally, you review your entire app, make any necessary adjustments, and write the README to reflect the current state and functionality of your app. This forces a big-picture reflection on your work and ensures that your project is well-documented.
Questions:
- Which decision in step 4 turned out to be wrong, and what would you change?
- If a stranger read this README, what would they still have to guess?
- What would you do differently if you started this app over tomorrow?

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
