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

## 4. README Part One

**Files**

- tip-calculator.py

**Where will people use your app: in a browser, on a phone, on a desktop, or in a terminal?**

PyQt6 (Python)

**What are you building it with? Name the language, framework and libraries, and say why you picked them.**

I chose pyqt6, because  pyqt6 has frameworks for the gui.

I chose this over tkinter because it's newer and I'm interested in learning its syntax.

It offers gui assistance in the form of pre-written frameworks

PyQt6 is in python, but I don't know it yet, so it costs some learning time. The size will be limited to what python ends up needing to save.

**What will you write, run and debug it with? Your editor, runtime and package manager.**

The editor I'm using is vscode, running Python 3.14.7

**How does someone get those installed? Write the steps you'd give a friend: making a virtual environment, installing the libraries, anything else. Stepwise won't run these.**

Run from the repo root. The commands assume C:\Repos\Stepwise, and the venv lives at C:\Repos\Stepwise\.venv.

Step 1 (only if activation is blocked):

 Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned

(lets PowerShell run the activate script. It applies only to the current window and resets when you close it.)

Step 2: Activate the venv with .venv\Scripts\Activate.ps1.

Step 3: Start the app with python

tip-calculator\tip-calculator.py

## 5. Syntax Implementation

**Step 1: A screen displays a text field: "Enter total"** in `tip-calculator.py`, done

Stuck on step 1: I found the docs to be helpful https://doc.qt.io/qtforpython-6/gettingstarted.html#getting-started. This got me installing qt for python packages.

**Step 2: A textbox is displayed underneath it** in `tip-calculator.py`, done

**Step 3: Another text field pops up: "Tip Percentage"** in `tip-calculator.py`, done

**Step 4: A slider with a number that rolls with it is shown below it** in `tip-calculator.py`, done

**Step 5: The app calculates: total * tip percentage** in `tip-calculator.py`, done

**Step 6: The app displays tip to give** in `tip-calculator.py`, done

## 6. App Execution

**What one command starts your app? Stepwise runs it inside your project folder, just like typing it into a terminal there. Like: python main.py**

python tip-calculator.py

**It ran! What did you see, and how does it compare to what you described back in stage 1?**

I had to use more of the python
