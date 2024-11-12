# __all__ = []

import argparse, socket, time


request = """\
GET HTTP1.1 task_type=""
Allow: POST, OPTIONS

"""

aphorisms = {
    b"Beautiful is better than?": b"Ugly.",
    b"Explicit is better than?": b"Implicit.",
    b"Simple is better than?": b"Complex.",
}


def __get_answer(aphorism):
    time.sleep(0.0)
    return aphorisms.get(aphorism, b"Error: Unknown aphorism.")


def parse_command_line(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("host", help="IP or hostname")
    parser.add_argument("-p", metavar="port", type=int, default=1060, help="TCP port(default 1060)")

    args = parser.parse_args()
    address = (args.host, args.p)
    return address


def create_srv_socket(address):
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SOCK_STREAM, 1)
    listener.bind(address)
    listener.listen(60)
    print("Listening at {}".format(address))
    return listener


def recv_until(sock, suffix):
    msg = sock.recv(4096)
    if not msg:
        raise EOFError("socket closed")
    while not msg.endswith(suffix):
        data = sock.recv(4096)
        if not data:
            raise IOError("received {!r} then socket close".format(msg))
        msg += data
    return msg


def __handle_request(sock: socket.socket):
    aphorism = recv_until(sock, b"?")
    sock.sendall(__get_answer(aphorism))


def __handle_conversation(sock, address):
    try:
        while True:
            __handle_request(sock)
    except EOFError:
        print("Client socket to {} has closed".format(address))
    except Exception as e:
        print("Client {} error: {}".format(address, e))
    finally:
        sock.close()


def accept_connections_forever(listener: socket.socket):
    while True:
        sock, address = listener.accept()
        print("Accepted connection from {}".format(address))
        __handle_conversation(sock, address)
