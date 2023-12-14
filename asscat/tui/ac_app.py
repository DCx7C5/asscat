from __future__ import annotations

from textual import events
from textual.app import App
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import RichLog

from asscat.manager import AssCatManager
from asscat.tui.screens import LiveLog, ExitScreen, Default


class AssCatApp(App):
    TITLE = 'AssCat'
    CSS_PATH = 'style.tcss'
    BINDINGS = [
        Binding("ctrl+c", "request_exit", "Exit", show=False, priority=True),
    ]

    MODES = {
        "default": Default,
        "logs": LiveLog,
        "exit": ExitScreen,
    }
    ENABLE_COMMAND_PALETTE = False

    _acm: AssCatManager = AssCatManager()
    _livelog: RichLog | Widget = None

    @property
    def acm(self) -> AssCatManager:
        return self._acm

    async def on_ready(self) -> None:
        self.log.info('Starting app...')

    async def on_mount(self) -> None:
        self.install_screen(Default(), 'default')
        self.install_screen(LiveLog(), 'logs')
        self.install_screen(ExitScreen(), 'exit')
        self.acm.set_textual_app(self)
        await self.push_screen('default')

    async def action_request_exit(self) -> None:
        await self.push_screen('exit')

