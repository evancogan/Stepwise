"""An editable numbered list (steps, files or tests): arrow keys to move, Enter to edit,
Shift+arrows to reorder, Delete to remove."""

from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Input, Label, ListItem, ListView, Static

from .store import Project


class StepItem(ListItem):
    def _on_click(self, event: events.Click) -> None:
        # ListView treats any click as "select", which opened the edit box on a single click.
        # Here a click only highlights the item; a double-click edits it, like Enter.
        event.prevent_default()
        items: ListView = self.parent
        items.focus()
        items.index = items.children.index(self)
        if event.chain >= 2:
            items.action_select_cursor()


class StepList(ListView):
    BINDINGS = [
        Binding("shift+up", "move(-1)", "Move up"),
        Binding("shift+down", "move(1)", "Move down"),
        Binding("delete", "remove", "Remove"),
    ]

    def action_cursor_down(self) -> None:
        # Down past the last item drops into the input, so arrows reach everything.
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
        Binding("up", "to_list", "List", show=False),
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
    """`name` is the list it edits: "steps", "files" or "tests". Each item's own answers
    (its pseudo-code, file, tick…) travel with it when it's moved or removed."""

    NOUNS = {"steps": "step", "files": "file", "tests": "test"}

    def __init__(self, project: Project, name: str = "steps", title: str = "Your steps", placeholder: str = ""):
        super().__init__(classes="step-editor")
        self.project = project
        self.list_name = name
        self.noun = self.NOUNS[name]
        self.title = title
        self.add_placeholder = placeholder or f"Type a {self.noun} and press Enter to add it"
        self.steps = project.items(name)
        self.extras = project.item_answers(name)
        self.editing: int | None = None

    def compose(self) -> ComposeResult:
        yield Label(self.title, classes="question")
        self.step_list = StepList(id="step-list")
        yield self.step_list
        yield StepInput(placeholder=self.add_placeholder, id="step-input")
        yield Static(f"↑↓ choose a {self.noun} · Enter or double-click edit · Shift+↑↓ reorder · Delete remove",
                     classes="hint")

    async def on_mount(self) -> None:
        await self.redraw(0 if self.steps else None)

    async def redraw(self, index: int | None) -> None:
        await self.step_list.clear()
        await self.step_list.extend(StepItem(Label(f"{n}. {s}")) for n, s in enumerate(self.steps, 1))
        self.step_list.display = bool(self.steps)
        if index is not None and self.steps:
            self.step_list.index = max(0, min(index, len(self.steps) - 1))

    def save(self) -> None:
        self.project.set_items(self.list_name, self.steps, self.extras)
        self.app.schedule_preview()
        self.app.refresh_sidebar()

    @property
    def input(self) -> StepInput:
        return self.query_one(StepInput)

    @on(ListView.Selected, "#step-list")
    def begin_edit(self, event: ListView.Selected) -> None:
        self.editing = self.step_list.index
        self.input.value = self.steps[self.editing]
        self.input.placeholder = f"Editing {self.noun} {self.editing + 1}"
        self.input.border_title = f"Editing {self.noun} {self.editing + 1} · Enter save · Esc cancel"
        self.input.focus()

    def cancel_edit(self) -> None:
        if self.editing is not None:
            index, self.editing = self.editing, None
            self.reset_input()
            self.step_list.index = index
            self.step_list.focus()

    def reset_input(self) -> None:
        self.input.value = ""
        self.input.placeholder = self.add_placeholder
        self.input.border_title = None

    @on(Input.Submitted, "#step-input")
    async def submit(self, event: Input.Submitted) -> None:
        text = " ".join(event.value.split())
        if not text:
            return
        if self.editing is None:
            self.steps.append(text)
            self.extras.append({})
            self.save()
            self.project.log(self.noun, action="add", index=len(self.steps), text=text)
            self.reset_input()
            await self.redraw(len(self.steps) - 1)
            self.step_list.scroll_end(animate=False)
        else:
            index, self.editing = self.editing, None
            self.project.log(self.noun, action="edit", index=index + 1, before=self.steps[index], text=text)
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
        for items in (self.steps, self.extras):
            items[i], items[j] = items[j], items[i]
        self.save()
        self.project.log(self.noun, action="move", index=i + 1, to=j + 1, text=self.steps[j])
        await self.redraw(j)

    async def remove_step(self) -> None:
        i = self.step_list.index
        if i is None:
            return
        removed = self.steps.pop(i)
        self.extras.pop(i)
        self.save()
        self.project.log(self.noun, action="remove", index=i + 1, text=removed)
        await self.redraw(i)
        self.app.notify(f"Removed “{removed}”.", timeout=3)
        if not self.steps:
            self.input.focus()
