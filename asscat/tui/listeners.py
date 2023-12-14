from __future__ import annotations
from asyncio import Server
from typing import Optional, Union, ClassVar, Iterable

from textual import events
from textual.app import ComposeResult
from textual.binding import BindingType, Binding
from textual.containers import Horizontal, VerticalScroll
from textual.events import Mount
from textual.geometry import clamp
from textual.message import Message
from textual.reactive import reactive
from textual.validation import Number
from textual.widget import Widget, AwaitMount
from textual.widgets import (
    Input,
    Button,
    Select,
    Static,
    Checkbox,
    Label,
)

from asscat.manager import AssCatManager


class Protocols:

    def __iter__(self):
        yield 'TCP', 'TCP'
        yield 'UDP', 'UDP'


class ListenerItem(Widget, can_focus=False):
    isserving = reactive[bool](False, always_update=True)
    highlighted = reactive[bool](False)

    class Clicked(Message):
        def __init__(self, item: ListenerItem) -> None:
            self.item = item
            super().__init__()

    class Closed(Message):
        def __init__(self, item: ListenerItem) -> None:
            self.item = item
            self.sid = item._sid
            super().__init__()

    class Start(Message):
        def __init__(self, item: ListenerItem) -> None:
            self.item = item
            self.sid = item._sid
            super().__init__()

    class Stop(Message):
        def __init__(self, item: ListenerItem) -> None:
            self.item = item
            self.sid = item._sid
            super().__init__()

    def __init__(
            self,
            server_id: int,
            server: Server,
            **kwargs,
    ):
        self._sid: int = server_id
        self._server: Server = server
        self._isserving = False
        self._host, self._port = self._server.sockets[0].getsockname()
        super().__init__(name=f'{self._host}:{self._port}', **kwargs)

    def on_mount(self, _: Mount) -> None:
        self.isserving = self._isserving

    def _on_click(self, _: events.Click) -> None:
        self.post_message(self.Clicked(self))

    async def watch_highlighted(self, value: bool) -> None:
        self.set_class(value, "--highlight")
        self.query_one('#close')

    async def watch_isserving(self, value: bool) -> None:
        pass

    @property
    def server(self) -> Server:
        return self._server

    def compose(self) -> ComposeResult:
        yield Label(self._host, id='hostlabel')
        yield Label(str(self._port), id='portlabel')
        yield Button(label='A', id='startstop')
        yield Button(label='🗑', id='close')

    async def on_button_pressed(self, event: Button.Pressed):
        button = event.button
        if button.id == 'close':
            self.post_message(self.Closed(self))
        elif button.id == 'startstop' and self.isserving:
            self.post_message(self.Stop(self))
        elif button.id == 'startstop' and not self.isserving:
            self.post_message(self.Start(self))


class ListenerCreator(Static):

    _list: ListenersList | None = None

    def on_mount(self) -> None:
        self._list: ListenersList | Widget = self.parent.query_one('#listeners_lst')

    def compose(self) -> ComposeResult:
        yield Input(placeholder='127.0.0.1', id='hostinput', value='127.0.0.1')
        yield Input(placeholder='8888', id='portinput', value='8888', validators=[
            Number(minimum=1, maximum=65535),
        ])
        yield Static(id='ph1')
        yield Select(Protocols(), prompt='Protocol', id='protocolinput', value='TCP')
        yield Checkbox('SSL', id='sslinput')
        yield Static(id='ph2')
        yield Static(id='ph3')
        yield Button(label='Create', id='create')

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'create':
            host: str = self.query_one('#hostinput').value
            port: int = int(self.query_one('#portinput').value)
            ssl: bool = self.query_one('#sslinput').value
            acm: AssCatManager = self.app.acm
            sid, server = await acm.create_listener(host, port)
            self.log('Created:', sid, server, self._list, host, port)
            await self._list.append(ListenerItem(server_id=sid, server=server))
            self.screen.set_focus(self._list)


class ListenersList(VerticalScroll, can_focus=True, can_focus_children=False):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter", "select_cursor", "Select", show=False),
        Binding("up", "cursor_up", "Cursor Up", show=False),
        Binding("down", "cursor_down", "Cursor Down", show=False),
        Binding("right", "cursor_right", "Cursor Right", show=False),
        Binding("left", "cursor_left", "Cursor Left", show=False),
    ]

    index = reactive[Optional[int]](0, always_update=True)

    class Highlighted(Message):
        """Posted when the highlighted item changes."""
        ALLOW_SELECTOR_MATCH = {"item"}

        def __init__(self, list_view: ListenersList, item: ListenerItem | None) -> None:
            super().__init__()
            self.list_view: ListenersList = list_view
            self.item: ListenerItem | None = item

        @property
        def control(self) -> ListenersList:
            return self.list_view

    class Selected(Message):
        """Posted when a list item is selected, e.g. when you press the enter key on it."""
        ALLOW_SELECTOR_MATCH = {"item"}

        def __init__(self, list_view: ListenersList, item: ListenerItem) -> None:
            super().__init__()
            self.list_view: ListenersList = list_view
            self.item: ListenerItem = item

        @property
        def control(self) -> ListenersList:
            return self.list_view

    def __init__(
            self,
            *children: ListenerItem,
            initial_index: int | None = 0,
            name: str | None = None,
            id: str | None = None,
            classes: str | None = None,
            disabled: bool = False,
    ) -> None:
        super().__init__(
            *children,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled
        )
        self._index = initial_index
        self._acm: AssCatManager = self.app.acm

    def _on_mount(self, _: Mount) -> None:
        """Ensure the ListView is fully-settled after mounting."""
        self.index = self._index

    @property
    def acm(self) -> AssCatManager:
        return self._acm

    @property
    def highlighted_child(self) -> ListenerItem | None:
        """The currently highlighted ListItem, or None if nothing is highlighted."""
        if self.index is not None and 0 <= self.index < len(self._nodes):
            list_item = self._nodes[self.index]
            assert isinstance(list_item, ListenerItem)
            return list_item
        else:
            return None

    async def action_select_cursor(self) -> None:
        """Select the current item in the list."""
        selected_child = self.highlighted_child
        if selected_child is None:
            return
        self.post_message(self.Selected(self, selected_child))

    async def action_cursor_down(self) -> None:
        """Highlight the next item in the list."""
        if self.index is None:
            self.index = 0
            return
        self.index += 1

    async def action_cursor_up(self) -> None:
        """Highlight the previous item in the list."""
        if self.index is None:
            self.index = 0
            return
        self.index -= 1

    async def action_cursor_left(self) -> None:
        self.screen.set_focus(self.screen.query_one('#sidebar'))

    async def action_cursor_right(self) -> None:
        pass

    async def on_listener_item_clicked(self, event: ListenerItem.Clicked) -> None:
        self.focus()
        self.index = self._nodes.index(event.item)
        self.post_message(self.Selected(self, event.item))

    async def on_listener_item_closed(self, event: ListenerItem.Closed) -> None:
        listener: Server = event.item.server
        self.log('listener closed', listener)
        listener.close()
        await event.item.remove()

    async def on_listener_item_start(self, event: ListenerItem.Start) -> None:
        self.log('LISTENER START SERVING', event.item)

    async def on_listener_item_stop(self, event: ListenerItem.Stop) -> None:
        self.log('LISTENER STOP SERVING', event.item)

    def _scroll_highlighted_region(self) -> None:
        if self.highlighted_child is not None:
            self.scroll_to_widget(self.highlighted_child, animate=True)

    async def extend(self, items: Iterable[ListenerItem]) -> AwaitMount:
        await_mount = self.mount(*items)
        if len(self) == 1:
            self.index = 0
        return await_mount

    async def append(self, item: ListenerItem) -> AwaitMount:
        return await self.extend([item])

    def __len__(self):
        return len(self._nodes)

    def validate_index(self, index: int | None) -> int | None:
        if not self._nodes or index is None:
            return None
        return self._clamp_index(index)

    def _clamp_index(self, index: int) -> int:
        last_index = max(len(self._nodes) - 1, 0)
        return clamp(index, 0, last_index)

    def _is_valid_index(self, index: int | None) -> bool:
        if index is None:
            return False
        return 0 <= index < len(self._nodes)

    def watch_index(self, old_index: int, new_index: int) -> None:
        """Updates the highlighting when the index changes."""
        if self._is_valid_index(old_index):
            old_child = self._nodes[old_index]
            assert isinstance(old_child, ListenerItem)
            old_child.highlighted = False

        new_child: Widget | None
        if self._is_valid_index(new_index):
            new_child = self._nodes[new_index]
            assert isinstance(new_child, ListenerItem)
            new_child.highlighted = True
        else:
            new_child = None

        self._scroll_highlighted_region()
        self.post_message(self.Highlighted(self, new_child))


class Listeners(Horizontal):

    def compose(self) -> ComposeResult:
        yield ListenersList(classes='panel', id='listeners_lst')
        yield ListenerCreator(classes='panel', id='listeners_cfg')
