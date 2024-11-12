import socket

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(("127.0.0.1", 10086))
server_socket.listen(5)

# 共享内存
# 管道
# 队列
# 文件
# socket

while True:
    sc, address = server_socket.accept()
    data = sc.recv(1024)
    print(data.decode("utf-8"))
    sc.close()
