"""Stage 2's numbered step list: arrow keys to move, Enter to edit, Shift+arrows to reorder."""

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Input, Label, ListItem, ListView, Static

from .store import Project


class StepList(ListView):
    BINDINGS = [
        Binding("shift+up", "move(-1)", "Move up"),
        Binding("shift+down", "move(1)", "Move down"),
        Binding("delete", "remove", "Remove"),
    ]

    def action_cursor_down(self) -> None:
        # Down past the last step drops into the input, so arrows reach everything.
        if self.index is None or self.index >= len(self) - 1:
            self.parent.query_one(StepInput).focus()
        else:
            super().action_cursor_down()

    async def action_move(self, delta: int) -> None:
        await self.parent.move(delta)

    async def action_remove(self) -> None:
        await self.parent.remove_step()


class StepInput(Input):
    BINDINGS = [
        Binding("up", "to_list", "Steps", show=False),
        Binding("escape", "cancel", "Cancel edit", show=False),
    ]

    def action_to_list(self) -> None:
        editor = self.parent
        if editor.steps:
            editor.cancel_edit()
            editor.step_list.index = len(editor.steps) - 1
            editor.step_list.focus()

    def action_cancel(self) -> None:
        self.parent.cancel_edit()


class StepEditor(Vertical):
    def __init__(self, project: Project):
        super().__init__(id="step-editor")
        self.project = project
        self.steps = project.steps()
        self.pseudo = project.pseudo()
        self.editing: int | None = None

    def compose(self) -> ComposeResult:
        yield Label("Your steps", classes="question")
        self.step_list = StepList(id="step-list")
        yield self.step_list
        yield StepInput(placeholder="Type a step and press Enter to add it", id="step-input")
        yield Static("↑↓ choose a step · Enter edit · Shift+↑↓ reorder · Delete remove", classes="hint")

    async def on_mount(self) -> None:
        await self.redraw(0 if self.steps else None)

    async def redraw(self, index: int | None) -> None:
        await self.step_list.clear()
        await self.step_list.extend(ListItem(Label(f"{n}. {s}")) for n, s in enumerate(self.steps, 1))
        self.step_list.display = bool(self.steps)
        if index is not None and self.steps:
            self.step_list.index = max(0, min(index, len(self.steps) - 1))

    def save(self) -> None:
        self.project.set_steps(self.steps, self.pseudo)

    @property
    def input(self) -> StepInput:
        return self.query_one(StepInput)

    @on(ListView.Selected, "#step-list")
    def begin_edit(self, event: ListView.Selected) -> None:
        self.editing = self.step_list.index
        self.input.value = self.steps[self.editing]
        self.input.placeholder = f"Editing step {self.editing + 1}"
        self.input.border_title = f"Editing step {self.editing + 1} · Enter save · Esc cancel"
        self.input.focus()

    def cancel_edit(self) -> None:
        if self.editing is not None:
            index, self.editing = self.editing, None
            self.reset_input()
            self.step_list.index = index
            self.step_list.focus()

    def reset_input(self) -> None:
        self.input.value = ""
        self.input.placeholder = "Type a step and press Enter to add it"
        self.input.border_title = None

    @on(Input.Submitted, "#step-input")
    async def submit(self, event: Input.Submitted) -> None:
        text = " ".join(event.value.split())
        if not text:
            return
        if self.editing is None:
            self.steps.append(text)
            self.pseudo.append("")
            self.save()
            self.project.log("step", action="add", index=len(self.steps), text=text)
            self.reset_input()
            await self.redraw(len(self.steps) - 1)
            self.step_list.scroll_end(animate=False)
        else:
            index, self.editing = self.editing, None
            self.project.log("step", action="edit", index=index + 1, before=self.steps[index], text=text)
            self.steps[index] = text
            self.save()
            self.reset_input()
            await self.redraw(index)
            self.step_list.focus()

    async def move(self, delta: int) -> None:
        i = self.step_list.index
        j = (i if i is not None else -1) + delta
        if i is None or not 0 <= j < len(self.steps):
            return
        for items in (self.steps, self.pseudo):
            items[i], items[j] = items[j], items[i]
        self.save()
        self.project.log("step", action="move", index=i + 1, to=j + 1, text=self.steps[j])
        await self.redraw(j)

    async def remove_step(self) -> None:
        i = self.step_list.index
        if i is None:
            return
        removed = self.steps.pop(i)
        self.pseudo.pop(i)
        self.save()
        self.project.log("step", action="remove", index=i + 1, text=removed)
        await self.redraw(i)
        self.app.notify(f"Removed “{removed}”.", timeout=3)
        if not self.steps:
            self.input.focus()
