import contextlib
import json
import pprint
import socket
import traceback
from typing import Dict, List, Optional

import common
import constants


class RPCClient:
    @staticmethod
    def logger_info(msg):
        print(f"客户端 > {msg}")

    @staticmethod
    def logger_error(msg):
        print(f"ERROR: {msg}")

    @staticmethod
    @contextlib.contextmanager
    def create_client_socket():
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(constants.SERVER_ADDRESS)
        yield client_socket
        client_socket.close()
        RPCClient.logger_info(f"关闭连接")

    @staticmethod
    def send_data(sock: socket.socket, request_data: Dict):
        data: str = json.dumps(request_data, ensure_ascii=False)
        encoded_data = data.encode(encoding=constants.ENCODING)

        # 校验消息长度
        if len(encoded_data) > constants.MAX_MESSAGE_LENGTH:
            raise BufferError(f"消息长度过长，不可超过 {constants.MAX_MESSAGE_LENGTH} 字节")

        # 校验消息格式
        # try:
        #     data = json.loads(encoded_data, encoding=constants.ENCODING)
        #     pprint.pprint(data)
        # except JSONDecodeError as e:
        #     raise ValueError("消息的格式必须是 json 格式") from e

        sock.sendall(encoded_data)
        RPCClient.logger_info(f"发送数据成功！")

    @staticmethod
    def recv_data(sock: socket.socket) -> Dict:
        data: bytes = common.recv_all(sock)

        decoded_data = data.decode(encoding=constants.ENCODING)

        res = json.loads(decoded_data)
        return res

    @staticmethod
    def rpc(name="", args: Optional[List] = None, kwargs: Optional[Dict] = None) -> Dict:
        try:
            args = args if args else list()
            kwargs = kwargs if kwargs else dict()

            request_data = dict(name=name, args=args, kwargs=kwargs)

            with RPCClient.create_client_socket() as sock:
                RPCClient.send_data(sock, request_data)
                recv_data = RPCClient.recv_data(sock)
            return recv_data
        except Exception as e:
            RPCClient.logger_error(f"{e}\n{traceback.format_exc()}")

    def __init__(self):
        pass


def main():
    rpc_client = RPCClient()

    recv_data = rpc_client.rpc(**{
        "name": "CryptoHelper_decrypt",
        "args": ["mgLrYJwzamUM3HgAm9YvYg=="],
        "kwargs": {

        }
    })
    pprint.pprint(recv_data)
    print(recv_data.get("data"))


if __name__ == '__main__':
    main()
