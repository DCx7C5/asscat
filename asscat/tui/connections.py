from textual.app import ComposeResult
from textual.containers import Horizontal, Container
from textual.widgets import ListView


class Connections(Horizontal):

    def compose(self) -> ComposeResult:
        yield ListView(classes='panel', id='connections_lst')
        yield Container(classes='panel', id='connections_cfg')
