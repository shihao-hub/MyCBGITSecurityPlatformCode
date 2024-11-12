import errno
import socket
import threading

EOF1 = b"\n\n"
EOF2 = b"\n\r\n"

response_body = """\
Hello, world! <h1> from {thread_name} </h1>\
"""

# Content-Type: text/plain -> 原始代码
response = """\
HTTP/1.0 200 OK\r\n\
Date: Sun, 27 may 2018 01:01:01 GMT\r\n\
Content-Type: text/html; charset=utf-8\r\n\
Content-Length: {length}\r\n\
\r\n\
{body}
"""


def handle_connection(sc, address, delay, cnt):
    print("----------------------------------------")
    print("oh, new conn", sc, address)
    print("delay = {}, cnt = {}".format(delay, cnt))
    # import time
    # time.sleep(delay)

    request = b""
    while EOF1 not in request and EOF2 not in request:
        request += sc.recv(1024)

    print(request.decode())

    cur_thread = threading.current_thread()

    global response_body, response

    body = response_body.format(thread_name=cur_thread.name)
    resp = response.format(length=len(body.encode()), body=body)

    # print(resp)
    sc.send(resp.encode())
    sc.close()


def main():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # server_sock.setblocking(False) # BlockingIOError: [WinError 10035] 无法立即完成一个非阻止性套接字操作。

    server_sock.bind(("127.0.0.1", 8080))
    server_sock.listen(5)

    try:
        i = 0
        while True:
            try:
                sc, address = server_sock.accept()
            except socket.error as e:
                if e.args[0] != errno.EAGAIN:
                    raise
                continue
            i += 1
            t = threading.Thread(target=handle_connection, args=(sc, address, i * 3, i), name="thread-{}".format(i))
            t.start()
    finally:
        server_sock.close()


if __name__ == '__main__':
    main()
