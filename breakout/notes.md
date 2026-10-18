# Breakout: notes

Your answers from Stepwise, by stage. Stepwise rewrites this file, so keep your own edits elsewhere.

## 1. Idea

**Intent**

This is a ball and paddle game, where a ball is shot towards the paddle in some slightly random direction, and the paddle is aimed so that the ball can bounce off of it and hit bricks for a score.

**If you could only ship one screen, what would be on that screen?**

The game screen, with the ball, paddle, and bricks

**What's the one thing this app does that nothing else you've used does?**

Nothing, this is for fun

## 2. Step Breakdown

**Steps**

1. A game window is rendered
2. A ball is rendered on screen
3. A paddle is rendered on screen
4. An array of bricks is rendered on screen
5. A start button is rendered somewhere on the screen
6. The start button pushes the ball towards the paddle, skewed a random direction
7. The paddle can hit the ball and the ball bounces in the opposite direction on impact
8. The ball hits the brick, and the brick disappears. A score is added

**Which step, if you got it wrong, would break everything after it?**

1, since the game window must be created for a game to be rendered

**Which steps depend on something you haven't built yet, and which could you start today?**

The game window

**If you had half the time, what would you cut, and what would the app lose?**

The score system

## 3. Pseudo Implementation

**Step 1: A game window is rendered**

```
START
game window created
renderer initialized
```

**Step 2: A ball is rendered on screen**

```
make shape ball
make color red
```

**Step 3: A paddle is rendered on screen**

```
a line is drawn on screen
```

**Step 4: An array of bricks is rendered on screen**

```
colored lines in an array on the top of the screen
```

**Step 5: A start button is rendered somewhere on the screen**

```
a button appears, text inside says "start"
```

**Step 6: The start button pushes the ball towards the paddle, skewed a random direction**

```
ball x position goes down, random small y position for skew
```

**Step 7: The paddle can hit the ball and the ball bounces in the opposite direction on impact**

```
paddle hits ball
ball bounces in the reverse direction
```

**Step 8: The ball hits the brick, and the brick disappears. A score is added**

```
ball hits brick]
Brick disappears
```

## 4. README Part One
