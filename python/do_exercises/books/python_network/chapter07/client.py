import random, socket, argparse

import zen_utils


def client(address, cause_error=False):
    print(cause_error)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(address)
    aphorisms = list(zen_utils.aphorisms)
    if cause_error:
        sock.sendall(aphorisms[0][:-1])
        return
    for e in random.sample(aphorisms, 3):
        sock.sendall(e)
        print(e, zen_utils.recv_until(sock, b"."))
    sock.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Example client")
    parser.add_argument("host", help="IP or hostname")
    parser.add_argument("-e", action="store_true", help="cause an error")
    parser.add_argument("-p", metavar="port", type=int, default=1060, help="TCP port(default 1060)")

    args = parser.parse_args()
    address = (args.host, args.e)
    client(address, args.e)
