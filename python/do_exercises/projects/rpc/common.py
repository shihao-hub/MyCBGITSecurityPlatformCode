import json
import socket
from typing import Optional

# 最小依赖原则
from constants import ENCODING


def generate_success_response_data(msg: Optional[str] = None, data=None) -> bytes:
    data = {
        "code": 1000,
        "msg": msg,
        "data": data
    }
    return json.dumps(data).encode(encoding=ENCODING)


def generate_error_response_data(msg=None, data=None, reason=None) -> bytes:
    data = {
        "code": 1001,
        "data": data,
        "msg": msg,
        "reason": reason,
        "status": "Error"
    }
    return json.dumps(data).encode(encoding=ENCODING)


def recv_all(sock: socket.socket, max_length=1024) -> bytes:
    # 2024-11-12：while 循环存在问题，暂且不解决
    per_len = 1024

    data = b""
    while True:
        more = sock.recv(per_len)
        if not more:
            break
        data += more
        if len(more) < per_len:
            break

        # break  # 临时添加
    return data
