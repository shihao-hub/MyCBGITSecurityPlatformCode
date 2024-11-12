import pprint
import socket
import http.client
import urllib.parse
from urllib import request


def main():
    # print(socket.getservbyname("domain"))
    # print(socket.getaddrinfo(None, 53))
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 1060))
    # print(sock.fileno())
    value = sock.getsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    print(type(value), value)
    print(sock.getsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST))


request_text = """\
GET https://www.bing.com/ HTTP/1.1\r\n\
Host: www.bing.com:443\r\n\
User-Agent: socket_test.py (Foundations of Python NetWork Programming)\r\n\
Connection: close\r\n\
\r\n\




"""
# Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)
request_text = """\
GET https://www.bing.com/\r\n\
Host: www.bing.com\r\n\
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0\r\n\
\r\n\
"""


def main2():
    req = request.Request(url="https://www.bing.com/", headers={
        "User-Agent": "Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)",
        "Host": "www.bing.com",
    }, method="GET")
    # print(request.urlopen(req).read().decode("utf-8"))

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # sock.settimeout(5)
    # sock.connect(("45.79.19.196", 80))
    sock.connect(("127.0.0.1", 63342))
    sock.sendall(request_text.encode("utf-8"))
    print(111)
    raw_reply = b""
    while True:
        more = sock.recv(4096)
        if not more:
            break
        raw_reply += more
    print(raw_reply.decode("utf-8"))


def main3():
    # pprint.pprint(socket.getaddrinfo("gatech.edu", "www"))
    # pprint.pprint(socket.getaddrinfo("bilibili.com", "www"))
    print(socket.gethostname())
    print(socket.getfqdn())
    print(socket.ge())
    print(socket.gethostbyname("zWX1333091k"))
    print(socket.gethostbyname("zWX1333091k.china.huawei.com"))
    print(socket.gethostbyaddr("10.85.208.146"))
    print(socket.getaddrinfo("bing.com", "www"))
    print(socket.getaddrinfo(None, "smtp", 0, socket.SOCK_STREAM, 0, socket.AI_PASSIVE))
    print(socket.getaddrinfo("localhost", "smtp", 0, socket.SOCK_STREAM, 0))
    print(socket.getaddrinfo("", 53))


if __name__ == '__main__':
    # main()
    main3()
    # try:
    #     main2()
    #     pass
    # except Exception as e:
    #     print(e)
