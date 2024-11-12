import errno
import pprint
import socket
import time

EOL1 = b"\n\n"
EOL2 = b"\n\r\n"

body = """Hello, world! <h1> from the5fire 《Django 企业开发实战》</h1>"""
response_params = [
    "HTTP/1.0 200 OK",
    "Date: {}".format(time.asctime(time.localtime(time.time()))),
    "Content-Type: {}".format("text/html; charset=utf-8"),  # text/plain; 需要改成 html 否则渲染失败
    "Content-Length: {}\r\n".format(len(body.encode())),
    body
]
response = "\r\n".join(response_params)


def handle_connection(conn: socket, addr):
    print("oh, new conn", conn, addr) # 每次访问网站会 accept 两次，为什么呢
    request = b""
    while EOL1 not in request and EOL2 not in request:
        request += conn.recv(1024)
    # pprint.pprint(request.split(br"\r\n"))
    # pprint.pprint(request)
    # print(request)
    # pprint.pprint(request.split(b"\r\n"))
    # import time
    # time.sleep(5)
    conn.send(response.encode())
    conn.close()


def main():
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    address = ("127.0.0.1", 8000)
    serversocket.bind(address)
    serversocket.listen(5)
    print("http://{}:{}".format(*address))

    # serversocket.setblocking(False) # 设置成非阻塞模式会报 10335 错误
    try:
        while True:
            try:
                conn, addr = serversocket.accept()
            except socket.error as e:
                if e.args[0] != errno.EAGAIN:
                    raise
                continue
            handle_connection(conn, addr)
    finally:
        serversocket.close()


if __name__ == "__main__":
    main()
