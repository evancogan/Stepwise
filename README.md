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