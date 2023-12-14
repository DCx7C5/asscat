from __future__ import annotations
from rich.text import TextType
from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Label, Static


class StartStopListener(Static):
    DEFAULT_CSS = """
    StartStopListener {
        width: 1;
        height: 1;
        background: $panel;
                
    }
    """
    label: reactive[TextType] = reactive[TextType]("")

    class Pressed(Message):

        def __init__(self, stasto: StartStopListener) -> None:
            self.stasto: StartStopListener = stasto
            super().__init__()

        @property
        def control(self) -> StartStopListener:
            return self.stasto
