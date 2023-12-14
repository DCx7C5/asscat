from textual.widgets import (
    ListItem,
    Button,
)


class IxIButton(Button):
    """1x1 Button"""

    def on_mount(self) -> None:
        self.styles.max_width = 1
        self.styles.max_height = 1
        self.styles.padding = 0
        self.styles.margin = 0


class ConnectionItem(ListItem): ...


class ListenerItem(ListItem):
    ...
