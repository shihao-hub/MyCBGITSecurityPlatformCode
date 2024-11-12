import argparse, socket, random, sys
import re
from datetime import datetime

MAX_BYTES = 65535  # 一次最多接受字节数
LOCAL_HOST = "127.0.0.1"

sent_server_address = {}


def server(interface, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if re.compile(" +").match(interface):
        # 使用 argparse 解析的时候，windows 似乎没法传递空字符串...
        interface = "0.0.0.0"  # 这个好像是来者不拒，只要发到这个端口的都接收？
    sock.bind((interface, port))

    print("Listening at {}".format(sock.getsockname()))

    while True:
        data, address = sock.recvfrom(MAX_BYTES)

        if random.random() < 0.5:
            print("Pretending to drop packet from {}".format(address))
            continue

        text = data.decode("ascii")

        print("The client at {} says {!r}".format(address, text))

        msg = "Your data was {} bytes long".format(len(data))
        sock.sendto(msg.encode("ascii"), address)  # 根据地址发回去，此处的 address 是元组


def client(hostname, port):
    """
    本机 ip 地址？
    127.0.0.1
    10.85.208.146 -> 私有地址
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sock.connect((hostname, port))

    print(hostname, sock)
    print("Client socket name is {}".format(sock.getsockname()))
    print("Client target socket name is {}".format((hostname, port)))
    print(sock.getpeername())

    delay = 0.1
    text = "This is another message"
    data = text.encode("ascii")

    while True:
        sock.send(data)
        sock.settimeout(delay)
        try:
            data = sock.recv(MAX_BYTES)
        except socket.timeout as e:
            print("Waiting up to {} seconds for a reply".format(delay))
            delay *= 2
            if delay > 2.0:
                raise RuntimeError("I think the server is down")
        else:
            break

    print("The server says {!r}".format(data.decode("ascii")))


def main():
    parser = argparse.ArgumentParser(description="Send and receive UDP locally,"
                                                 " pretending packets are often dropped")
    choices = {"server": server, "client": client}
    parser.add_argument("role",
                        choices=choices,
                        help="which role to play")
    parser.add_argument("-hs",
                        metavar="HOST",
                        type=str,
                        default="127.0.0.1",
                        help="interface the server listens at;"
                             "host the client sends to")
    parser.add_argument("-p",
                        metavar="PORT",
                        type=int,
                        default=1060,
                        help="UDP port (default 1060)")
    args = parser.parse_args()
    fn = choices[args.role]
    fn(args.host, args.p)


if __name__ == '__main__':
    main()
