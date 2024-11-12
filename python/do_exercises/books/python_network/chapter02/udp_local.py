import argparse, socket
from datetime import datetime

MAX_BYTES = 65535  # 一次最多接受字节数
LOCAL_HOST = "127.0.0.1"
ENCODING = "ascii"

sent_server_address = {}


def logger(*args, sep=' ', end='\n', file=None):
    print("logger -> ", *args, sep=sep, end=end, file=file)


logger = print


def server(port=1060):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LOCAL_HOST, port))

    logger("Listening at {}".format(sock.getsockname()))

    while True:
        data, address = sock.recvfrom(MAX_BYTES)
        text = data.decode(ENCODING)

        logger("The client at {} says {!r}".format(address, text))

        text_to_send = "Your data was {} bytes long".format(len(data))
        data_to_send = text_to_send.encode(ENCODING)

        sock.sendto(data_to_send, address)  # 根据地址发回去，此处的 address 是元组


def client(port=1060):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    text = "The time is {}".format(datetime.now())
    data = text.encode(ENCODING)

    sock.sendto(data, (LOCAL_HOST, port))

    logger("The OS assigned me the address {}".format(sock.getsockname()))

    # 此处理当验证一下地址来源
    data, address = sock.recvfrom(MAX_BYTES)  # Danger!
    text = data.decode(ENCODING)

    logger("The server {} replied {!r}".format(address, text))


def main():
    parser = argparse.ArgumentParser(description="Send and receive UDP locally")
    choices = {"server": server, "client": client}
    """ 关于 argparse 的浅显理解：
    parser = argparse.ArgumentParser(description="Title")
    parser.add_argument("a")
    parser.add_argument("b")
    parser.add_argument("c")
    parser.add_argument("-x")
    parser.add_argument("-y")
    parser.add_argument("-z")
    -> Usage: udp_local.py [-h] [-x X] [-y Y] [-z Z] a b c
    args = parser.parse_args()
    -> Fields: args["a"]
               args["b"]
               args["c"]
               args["x"]
               args["y"]
               args["z"]
    """
    parser.add_argument("role",
                        choices=choices,
                        help="which role to play")
    parser.add_argument("-p",
                        metavar="PORT",
                        type=int,
                        default=1060,
                        help="UDP port (default 1060)")
    args = parser.parse_args()
    fn = choices[args.role]
    fn(port=args.p)


if __name__ == '__main__':
    main()
