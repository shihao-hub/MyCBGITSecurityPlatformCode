import socket


def recvall(sc: socket.socket):
    # FIXME: 这里这样写不对！recv 无法终止
    data = b""
    while True:
        more = sc.recv(4096)
        if not more:
            break
        data += more
    return data


def main():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("127.0.0.1", 8080))
    server_sock.listen(5)

    while True:
        sc, address = server_sock.accept()
        data = sc.recv(4096)
        print(data)
        with open(r"git_template.zip", "rb") as file:
            for e in file:
                print(e)
                sc.send(e)
        sc.close()


if __name__ == '__main__':
    main()
    # 111
    print(1)
    print(111)
    print(22)
    print(222)
    print(3)
    print(333)
    print(333)
    print(333)
