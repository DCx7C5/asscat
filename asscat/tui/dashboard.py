from __future__ import annotations

from textual.app import ComposeResult

from textual.widgets import (
    ContentSwitcher,
    TabPane,
)

from asscat.tui.connections import Connections
from asscat.tui.listeners import Listeners
from asscat.tui.sidebar import SideBar


class OutputContainer(ContentSwitcher): ...


class Dashboard(TabPane):
    TITLE = 'Dashboard'

    def compose(self) -> ComposeResult:
        yield SideBar(id='sidebar')
        with OutputContainer(initial='listeners', id='switcher'):
            yield Listeners(id='listeners')
            yield Connections(id='connections')
