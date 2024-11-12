import json
import pprint
import socket
from json.decoder import JSONDecodeError
from typing import Dict

import constants
import common


def _check_message(msg: bytes):
    # 校验消息长度
    if len(msg) > constants.MAX_MESSAGE_LENGTH:
        raise BufferError(f"消息长度过长，不可超过 {constants.MAX_MESSAGE_LENGTH} 字节")

    # 校验消息格式
    # try:
    #     data = json.loads(msg, encoding=constants.ENCODING)
    #     pprint.pprint(data)
    # except JSONDecodeError as e:
    #     raise ValueError("消息的格式必须是 json 格式") from e


def send_message(sock: socket.socket, data: Dict):
    msg = json.dumps(data, ensure_ascii=False)
    encoded_msg = msg.encode(encoding=constants.ENCODING)

    _check_message(encoded_msg)

    sock.sendall(encoded_msg)
    print(f"客户端 > 发送数据成功！")


def recv_message(sock: socket.socket) -> Dict:
    decoded_msg = common.recv_all(sock).decode(encoding=constants.ENCODING)
    data = json.loads(decoded_msg)
    return data


def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(constants.SERVER_ADDRESS)

    send_data = {
        "name": "say_hello",
        "args": [1, 2, 3, "你好"],
        "kwargs": {

        }
    }
    send_message(client_socket, send_data)

    recv_data = recv_message(client_socket)
    pprint.pprint(recv_data)

    # client_socket.shutdown(socket.SHUT_RDWR)
    client_socket.close()
    print(f"客户端 > 关闭连接")


if __name__ == '__main__':
    main()
