import json
import socket
import traceback
from typing import Tuple, Dict, Callable

import constants
import common


def logger_info(msg):
    print(f"服务端 > {msg}")


class FunctionManager:
    def __init__(self):
        self._functions = {}

    def register(self, name, fn: Callable):
        self._functions[name] = fn

    def call(self, name, args: Tuple, kwargs: Dict):
        args = args if args else tuple()
        kwargs = kwargs if kwargs else dict()

        fn = self._functions.get(name)
        if not fn:
            raise LookupError(f"函数 {name} 未注册！")
        return fn(*args, **kwargs)


function_manager = FunctionManager()


def register_functions():
    def say_hello(*args, **kwargs):
        print(f"{args} - {kwargs}")

    function_manager.register("say_hello", say_hello)


def main():
    register_functions()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(constants.SERVER_ADDRESS)
    server_socket.listen(1)
    logger_info(f"启动成功")

    while True:
        print()
        logger_info(f"等待客户端连接")
        client_socket, client_address = server_socket.accept()
        try:
            logger_info(f"开始接收数据")
            recv_data: bytes = common.recv_all(client_socket)

            logger_info(f"接收到客户端发来的消息长度为：{len(recv_data)} byte")

            decoded_data: str = recv_data.decode(encoding=constants.ENCODING)
            logger_info(f"接收到的数据：{decoded_data}")
            data = json.loads(decoded_data)

            res = function_manager.call(data.get("name"), data.get("args"), data.get("kwargs"))
            logger_info(f"res: {res}")
            client_socket.sendall(json.dumps({
                "result": res
            }).encode(encoding=constants.ENCODING))
        except Exception as e:
            print(f"{e}\n{traceback.format_exc()}")
        finally:
            client_socket.close()


if __name__ == '__main__':
    main()
