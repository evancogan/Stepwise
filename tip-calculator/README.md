# tip-calculator

A simple solution to paying a tip at a fine dining establishment

## About

The app opens to a screen that displays: "Enter tip percentage" and "Enter Total" There is a slider for the percentage, and a text box for the total.

## Why I built this

Have you ever been sitting at a restaurant, nervously punching numbers into your phone's calculator? No more! I say, as the solution is this app. Simply open the app, and select a tip amount.

Building it myself would give me proof of ownership, that I made my own tip calculator.

## Build steps

- [ ] The app opens
- [ ] A screen displays a text field: "Enter total"
- [ ] A textbox is displayed underneath it
- [ ] Another text field pops up: "Tip Percentage"
- [ ] A slider with a number that rolls with it is shown below it
- [ ] The user enters both fields
- [ ] The app calculates: total * tip percentage
- [ ] The app displays tip to give

## How it works

The app opens, and a screen displays a text field asking the user for a total. A textbox is used as the entry field. Another text field is below it, asking for a tip percentage. The tip percentage is input

**Keeps track of:** The value of total, tip, and tip percentage

**Input:** tip percentage and total

**When input goes wrong:** There is not enough data for a logical operation to output a new number

**How the parts connect:** All through python

## Getting started

**Requirements:** PyQt6 (Python)

## Tech stack

**Built with:** The user sees the gui, python handles the logic, and pyqt6 has frameworks for said gui

**Why these:** I chose this over tkinter because it's newer and I'm interested in learning its syntax.

**Libraries:**  PyQt6 is the library I'm using, it offers gui assistance in the form of pre-written frameworks

**Trade-offs:**  PyQt6 is in python, but I don't know it yet, so it costs some learning time. The size will be limited to what python ends up needing to save.

## Development

The editor I'm using is vscode

## Challenges and what I learned

**Everything else depends on:** The tip calculation logic, and the app opening at all, step 1.

**Why:** If the tip calculation logic is off, the whole app is considered imperfect, so that line of code is really important. The app not opening at all would also impede the user, so healthy builds and good commit habits are necessary prevention habits.

**Hardest to pin down:** getting the user experience right is harder than this, as the logical operation is one line

**Why:** see above

**Least sure about:** I'm least sure about the UI, I still don't know how I'll do that, it could be that I have to copy/paste a lot of documentation examples

**How I'll find out:** I could try to look at the doc first and break it down into pseudocode

## Roadmap

**Could come later:** The user experience, the core logic is the heart of the app.

**What it adds:** the app would lose the smoothness of the ui, the friendliness in the experience, a slider/text box is more intuitive.
