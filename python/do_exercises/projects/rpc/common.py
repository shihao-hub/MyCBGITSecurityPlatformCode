import socket


def recv_all(sock: socket.socket, max_length=1024) -> bytes:
    # 2024-11-12：while 循环存在问题，暂且不解决
    data = b""
    while True:
        more = sock.recv(1024)
        if not more:
            break
        data += more

        break  # 临时添加
    return data
