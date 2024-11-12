import json
import socket
import traceback
from typing import Dict, Callable, List

import common
import constants
from crypto_helper import CryptoHelper


class RPCServer:
    @staticmethod
    def logger_info(msg):
        print(f"服务端 > {msg}")

    @staticmethod
    def logger_error(msg):
        print(f"ERROR: {msg}")

    @staticmethod
    def create_server_socket(backlog=5):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(constants.SERVER_ADDRESS)
        # backlog: 积压的。

        # backlog 表示在有客户端连接请求到来时，最多可以排队 backlog 个连接请求（不包括已经连接的那个）。
        # 如果有多于 backlog 的连接请求到达，超出的连接请求会被拒绝，直到队列中有空间。

        # 如果你的应用需要处理多个并发连接，建议将 listen() 的参数设置为更大的值，例如 5 或 10 等。
        
        server_socket.listen(backlog)
        return server_socket

    @staticmethod
    def recv_data(sock: socket.socket) -> Dict:
        RPCServer.logger_info(f"开始接收数据")

        data: bytes = common.recv_all(sock)
        RPCServer.logger_info(f"接收到客户端发来的消息长度为：{len(data)} byte")

        decoded_data: str = data.decode(encoding=constants.ENCODING)

        res = json.loads(decoded_data)
        # print(res) # json 之 null-None, []-list, {}-dict
        return res

    class FunctionManager:
        def __init__(self):
            self._functions = {}

        def register(self, name: str, fn: Callable):
            self._functions[name] = fn

        def _check_parameters_for_call(self, args, kwargs):
            this = self
            if not isinstance(args, List):
                raise ValueError("参数类型错误，args 必须是列表类型")
            if not isinstance(kwargs, Dict):
                raise ValueError("参数类型错误，kwargs 必须是字典类型")

        def call(self, name, args: List, kwargs: Dict):
            args = args if args else list()
            kwargs = kwargs if kwargs else dict()

            self._check_parameters_for_call(args, kwargs)

            fn = self._functions.get(name)
            if not fn:
                raise LookupError(f"函数 {name} 未注册！")
            return fn(*args, **kwargs)

    def __init__(self):
        self._function_manager = RPCServer.FunctionManager()

    def register_function(self, name: str, fn: Callable):
        return self._function_manager.register(name, fn)

    def _call(self, name, args: List, kwargs: Dict):
        return self._function_manager.call(name, args, kwargs)

    def _do_circular_task(self, server_socket):
        RPCServer.logger_info(f"等待客户端连接")

        client_socket, client_address = server_socket.accept()
        try:
            data = self.recv_data(client_socket)
            try:
                res = self._call(data.get("name"), data.get("args"), data.get("kwargs"))
                client_socket.sendall(common.generate_success_response_data(data=res))
            except Exception as e:
                msg = f"调用 {data.get('name')} 函数发生错误"
                reason = f"{e}"
                client_socket.sendall(common.generate_error_response_data(msg=msg, reason=reason))
                raise
        except Exception as e:
            RPCServer.logger_error(f"{e}\n{traceback.format_exc()}")
        finally:
            client_socket.close()

    def run(self):
        server_socket = None
        try:
            server_socket = type(self).create_server_socket()
            while True:
                self._do_circular_task(server_socket)
                print()
        except Exception as e:
            RPCServer.logger_error(f"{e}\n{traceback.format_exc()}")
        finally:
            if server_socket:
                server_socket.close()


def say_hello(*args, **kwargs):
    print(f"{args} - {kwargs}")


def main():
    rpc_server = RPCServer()

    rpc_server.register_function("say_hello", say_hello)
    rpc_server.register_function("CryptoHelper_encrypt", CryptoHelper().encrypt)
    rpc_server.register_function("CryptoHelper_decrypt", CryptoHelper().decrypt)

    rpc_server.run()


if __name__ == '__main__':
    main()
