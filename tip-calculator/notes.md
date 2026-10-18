# tip-calculator: notes

Your answers from Stepwise, by stage. Stepwise rewrites this file, so keep your own edits elsewhere.

## 1. Idea

**Describe your app in a sentence or two. Who is it for, and what does it do for them?**

A simple solution to paying a tip at a fine dining establishment

**Walk through using your app once, start to finish. What does the user see, and what do they do?**

The app opens to a screen that displays: "Enter tip percentage" and "Enter Total" There is a slider for the percentage, and a text box for the total.

**Why are you building this, and why build it yourself?**

Have you ever been sitting at a restaurant, nervously punching numbers into your phone's calculator? No more! I say, as the solution is this app. Simply open the app, and select a tip amount.

Building it myself would give me proof of ownership, that I made my own tip calculator.

## 2. Step Breakdown

**Steps**

1. A screen displays a text field: "Enter total"
2. A textbox is displayed underneath it
3. Another text field pops up: "Tip Percentage"
4. A slider with a number that rolls with it is shown below it
5. The app calculates: total * tip percentage
6. The app displays tip to give

**Walk through your app once more using your steps. Describe the flow from start to finish. If a moment isn't covered by any step, go back and add one.**

The app opens, and a screen displays a text field asking the user for a total. A textbox is used as the entry field. Another text field is below it, asking for a tip percentage. The tip percentage is input

**Which step does everything else depend on, and why?**

The tip calculation logic, and the app opening at all, step 1.

If the tip calculation logic is off, the whole app is considered imperfect, so that line of code is really important. The app not opening at all would also impede the user, so healthy builds and good commit habits are necessary prevention habits.

**Once the first version works, what would you add next?**

I would add a gratuity tracker that tells the user their tip history, and average tip.

## 3. Pseudo Implementation

**Step 1: A screen displays a text field: "Enter total"**

```
input = get user input("Enter total")
```

**Step 2: A textbox is displayed underneath it**

```
input = type(text)
```

**Step 3: Another text field pops up: "Tip Percentage"**

```
input = tip percentage
```

**Step 4: A slider with a number that rolls with it is shown below it**

```
output slider min 0 max 100
```

**Step 5: The app calculates: total * tip percentage**

```
tip = total * tip percentage
```

**Step 6: The app displays tip to give**

```
output tip
```

**What does your app need to keep track of while it runs?**

The value of total, tip, and tip percentage

**What does the user give your app, and what should happen if it's missing or wrong?**

tip percentage and total

There is not enough data for a logical operation to output a new number

**Which step was hardest to describe in plain words, and what made it hard?**

getting the user experience right is harder than this, as the logical operation is one line

## 4. README Part One

**Where will people use your app: in a browser, on a phone, on a desktop, or in a terminal?**

PyQt6 (Python)

**What are you building it with? Name the language, framework and libraries, and say why you picked them.**

The user sees the gui, python handles the logic, and pyqt6 has frameworks for said gui

I chose this over tkinter because it's newer and I'm interested in learning its syntax.

PyQt6 is the library I'm using, it offers gui assistance in the form of pre-written frameworks

PyQt6 is in python, but I don't know it yet, so it costs some learning time. The size will be limited to what python ends up needing to save.

**What will you write, run and debug it with? Your editor, runtime and package manager.**

The editor I'm using is vscode

**Which of these choices are you least sure about, and how could you test it quickly?**

I'm least sure about the UI, I still don't know how I'll do that, it could be that I have to copy/paste a lot of documentation examples

I could try to look at the doc first and break it down into pseudocode
