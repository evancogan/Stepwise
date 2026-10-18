# tip-calculator: notes

Your answers from Stepwise, by stage. Stepwise rewrites this file, so keep your own edits elsewhere.

## 1. Idea

**Describe your app in a sentence or two. Who is it for, and what does it do for them?**

A simple solution to paying a tip at a fine dining establishment

**Walk through using your app once, start to finish. What does the user see, and what do they do?**

The app opens to a screen that displays: "Enter tip percentage" and "Enter Total" There is a slider for the percentage, and a text box for the total.

**Why are you building this?**

Have you ever been sitting at a restaurant, nervously punching numbers into your phone's calculator? No more! I say, as the solution is this app. Simply open the app, and select a tip amount.

**What will building it yourself give you that an existing app wouldn't?**

Building it myself would give me proof of ownership, that I made my own tip calculator.

## 2. Step Breakdown

**Steps**

1. The app opens
2. A screen displays a text field: "Enter total"
3. A textbox is displayed underneath it
4. Another text field pops up: "Tip Percentage"
5. A slider with a number that rolls with it is shown below it
6. The user enters both fields
7. The app calculates: total * tip percentage
8. The app displays tip to give

**Walk through one use of your app again. Which step handles each moment? Add a step for any moment none of them covers.**

The app opens, and a screen displays a text field asking the user for a total. A textbox is used as the entry field. Another text field is below it, asking for a tip percentage. The tip percentage is input

**Which step, if you got it wrong, would break everything after it?**

The tip calculation logic, and the app opening at all, step 1.

**Why?**

If the tip calculation logic is off, the whole app is considered imperfect, so that line of code is really important. The app not opening at all would also impede the user, so healthy builds and good commit habits are necessary prevention habits.

**If you had half the time, which steps would you cut?**

The user experience, the core logic is the heart of the app.

**What would the app lose without them?**

the app would lose the smoothness of the ui, the friendliness in the experience, a slider/text box is more intuitive.

## 3. Pseudo Implementation

**Step 1: The app opens**

```
not applicable to code
```

**Step 2: A screen displays a text field: "Enter total"**

```
input = get user input("Enter total")
```

**Step 3: A textbox is displayed underneath it**

```
input = type(text)
```

**Step 4: Another text field pops up: "Tip Percentage"**

```
input = tip percentage
```

**Step 5: A slider with a number that rolls with it is shown below it**

```
output slider min 0 max 100
```

**Step 6: The user enters both fields**

```
not applicable to code
```

**Step 7: The app calculates: total * tip percentage**

```
tip = total * tip percentage
```

**Step 8: The app displays tip to give**

```
output tip
```

**What does your app have to keep track of while it runs, or between runs?**

The value of total, tip, and tip percentage

**What input does your app take?**

tip percentage and total

**What happens when that input is missing or wrong?**

There is not enough data for a logical operation to output a new number

**Which step's logic was hardest to put into words?**

getting the user experience right is harder than this, as the logical operation is one line

**Why?**

see above

## 4. README Part One

**Where does your app run, and what does someone need to open it?**

PyQt6 (Python)

**What does the user see, what handles the logic, and where does the data live? Name the tool for each.**

The user sees the gui, python handles the logic, and pyqt6 has frameworks for said gui

**Why each one, over the alternatives you looked at?**

I chose this over tkinter because it's newer and I'm interested in learning its syntax.

**Which libraries will you use, and what does each one do for you?**

 PyQt6 is the library I'm using, it offers gui assistance in the form of pre-written frameworks

**What does each one cost you: learning time, size, or control?**

 PyQt6 is in python, but I don't know it yet, so it costs some learning time. The size will be limited to what python ends up needing to save.

**How do the parts of your app talk to each other?**

All through python

**What will you write, run and debug it with? Editor, runtime, package manager, build tools.**

The editor I'm using is vscode

**Which choice are you least sure about?**

I'm least sure about the UI, I still don't know how I'll do that, it could be that I have to copy/paste a lot of documentation examples

**What's the cheapest way to test it before you commit?**

I could try to look at the doc first and break it down into pseudocode
