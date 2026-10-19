# tip-calculator

A simple solution to paying a tip at a fine dining establishment

## About

The app opens to a screen that displays: "Enter tip percentage" and "Enter Total" There is a slider for the percentage, and a text box for the total.

## Why I built this

Have you ever been sitting at a restaurant, nervously punching numbers into your phone's calculator? No more! I say, as the solution is this app. Simply open the app, and select a tip amount.

Building it myself would give me proof of ownership, that I made my own tip calculator.

## Build plan

- [ ] A screen displays a text field: "Enter total"
- [ ] A textbox is displayed underneath it
- [ ] Another text field pops up: "Tip Percentage"
- [ ] A slider with a number that rolls with it is shown below it
- [ ] The app calculates: total * tip percentage
- [ ] The app displays tip to give

## How it works

The app opens, and a screen displays a text field asking the user for a total. A textbox is used as the entry field. Another text field is below it, asking for a tip percentage. The tip percentage is input

### What it keeps track of

The value of total, tip, and tip percentage

### Input

tip percentage and total

There is not enough data for a logical operation to output a new number

## Tech stack

### Where it runs

PyQt6 (Python)

### Built with

The user sees the gui, python handles the logic, and pyqt6 has frameworks for said gui

I chose this over tkinter because it's newer and I'm interested in learning its syntax.

PyQt6 is the library I'm using, it offers gui assistance in the form of pre-written frameworks

PyQt6 is in python, but I don't know it yet, so it costs some learning time. The size will be limited to what python ends up needing to save.

## Development

The editor I'm using is vscode, running Python 3.14.7

## Challenges and what I learned

### The step everything depends on

The tip calculation logic, and the app opening at all, step 1.

If the tip calculation logic is off, the whole app is considered imperfect, so that line of code is really important. The app not opening at all would also impede the user, so healthy builds and good commit habits are necessary prevention habits.

### The hardest step to describe

Getting the user experience right is perhaps the hardest part, everything else is an easy line of code

### The choice I'm least sure about

I'm least sure about the UI, I still don't know how I'll do that, it could be that I have to copy/paste a lot of documentation examples

I could try to look at the doc first and break it down into pseudocode

## Roadmap

I would add a gratuity tracker that tells the user their tip history, and average tip.
