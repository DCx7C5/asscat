from __future__ import annotations

from typing import Coroutine

from textual.app import ComposeResult, App
from textual.binding import Binding
from textual.screen import Screen, ModalScreen
from textual.containers import Grid

from textual.widgets import (
    Header,
    Footer,
    Label,
    Button,
    RichLog, TabbedContent,
)

from asscat.tui.dashboard import Dashboard
from asscat.tui.settings import Settings


class ShellScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, id='header')
        yield Footer()


class LiveLog(Screen):
    TITLE = 'EventLog'
    BINDINGS = [
        Binding('ctrl+d', 'request_default_screen', 'Dashboard', show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, id='header')
        yield RichLog(highlight=True, markup=True, id='livelog')
        yield Footer()

    async def action_request_default_screen(self) -> None:
        await self.app.switch_mode('default')


class QuoteScreen(ModalScreen[bool]):
    TITLE = ''

    def compose(self):
        yield Label('TEST')


class ExitScreen(ModalScreen):

    _acm_close: Coroutine = None

    def on_mount(self) -> None:
        from asscat.tui.ac_app import AssCatApp
        app: App | AssCatApp = self.app
        self._acm_close = app.acm.shutdown()

    def compose(self) -> ComposeResult:
        with Grid(id='dialog'):
            yield Label("Are you sure you want to exit?", id='question')
            yield Button("Exit", variant="error", id='exit')
            yield Button("Cancel", variant="primary")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "exit":
            await self.acm_close()
            self.app.exit()
        else:
            self.app.pop_screen()

    async def acm_close(self) -> None:
        await self._acm_close


class Default(Screen):
    BINDINGS = [
        Binding('ctrl+l', 'request_logs_screen', '🪵EventLog', show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, id='header')
        with TabbedContent(id='content'):
            yield Dashboard('🖥️Dashboard', classes='tab', id='tab0')
            yield Settings('⚙️Settings', classes='tab', id='tab1')
        yield Footer()

    async def action_request_logs_screen(self) -> None:
        await self.app.switch_mode('logs')
