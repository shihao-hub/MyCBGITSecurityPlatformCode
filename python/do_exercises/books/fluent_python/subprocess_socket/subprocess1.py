import socket
from concurrent.futures import ThreadPoolExecutor

client_socket = socket.socket()
client_socket.connect(("127.0.0.1", 10086))

client_socket.send("你好！".encode("utf-8"))

pool = ThreadPoolExecutor()
pool.run()
