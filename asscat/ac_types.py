from typing import Literal, Tuple

SocketType = Literal['UDP', 'TCP', 'tcp', 'udp']
SocketAddrType = Tuple[str, int]
AddressFamType = Literal['ipv4', 'ipv6', 'v4', 'v6', '4', '6', 4, 6]
