from __future__ import annotations

from textual.app import ComposeResult

from textual.widgets import (
    TabPane, Label,
)


class Settings(TabPane):
    TITLE = 'Settings'

    def compose(self) -> ComposeResult:
        yield Label('Stuff')
