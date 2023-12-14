from textual.app import ComposeResult

from textual.widgets import (
    ContentSwitcher,
    ListView, ListItem, Label
)


class SideBarItem(ListItem): ...


class SideBar(ListView):

    def compose(self) -> ComposeResult:
        yield SideBarItem(
            Label('LISTENERS'),
            classes='menuitem',
            id='mi_listeners',

        )
        yield SideBarItem(
            Label('CONNECTIONS'),
            classes='menuitem',
            id='mi_connections',
        )

    async def on_list_view_selected(self, event: ListView.Selected):
        await self._switch_menu_widget(event.item)

    async def _switch_menu_widget(self, item):
        switcher: ContentSwitcher = self.app.query_one('#switcher', ContentSwitcher)

        # Return if selected is current
        if switcher.current == item.id[3:]:
            return

        if item.id == 'mi_listeners':
            switcher.current = 'listeners'

        elif item.id == 'mi_connections':
            switcher.current = 'connections'
