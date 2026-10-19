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

## Project structure

- `tip-calculator.py`

## Tech stack

### Where it runs

PyQt6 (Python)

### Built with

I chose pyqt6, because  pyqt6 has frameworks for the gui.

I chose this over tkinter because it's newer and I'm interested in learning its syntax.

It offers gui assistance in the form of pre-written frameworks

PyQt6 is in python, but I don't know it yet, so it costs some learning time. The size will be limited to what python ends up needing to save.

## Development

The editor I'm using is vscode, running Python 3.14.7

## Roadmap

I would add a gratuity tracker that tells the user their tip history, and average tip.
