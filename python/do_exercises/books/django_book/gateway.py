import os
import pprint
import sys


from simple_app import simple_app


def WSGI_to_bytes(s: str):
    return s.encode()


def run_with_cgi(application):
    environment = dict(os.environ.items())

    environment["wsgi.input"] = sys.stdin.buffer
    environment["wsgi.errors"] = sys.stderr
    environment["wsgi.version"] = (1, 0)
    environment["wsgi.multithread"] = False
    environment["wsgi.multiprocess"] = True
    environment["wsgi.run_once"] = True
    if environment.get("Https", "off") in ("on", "1"):
        environment["wsgi.url_scheme"] = "https"
    else:
        environment["wsgi.url_scheme"] = "http"

    headers_set = []
    headers_sent = []

    def write(data):
        out = sys.stdout.buffer
        if not headers_set:
            raise AssertionError("write() before start_response()")
        elif not headers_sent:
            status, response_headers = headers_sent[:] = headers_set
            out.write(WSGI_to_bytes("Status: {}\r\n".format(status)))
            for header in response_headers:
                out.write(WSGI_to_bytes("{}: {}\r\n".format(*header)))
            out.write(WSGI_to_bytes("\r\n"))
        out.write(data)
        out.flush()

    def start_response(status, response_headers, exc_info=None):
        if exc_info:
            try:
                if headers_set:
                    # 如果已经发送了 header，则重新抛出原始异常信息
                    raise (exc_info[0], exc_info[1], exc_info[2])
            finally:
                exc_info = None  # 避免循环引用
        elif headers_set:
            raise AssertionError("Headers already set!")

        headers_set[:] = [status, response_headers]
        return write

    result = application(environment, start_response)
    # pprint.pprint(environment)

    # 这下面在干什么？？？
    try:
        for data in result:
            if data:  # 如果没有 body，则不发送 header
                write(data)
        if not headers_sent:  # 如果没有调用 write，即没有 body，则发送数据 header
            write("")
    finally:
        if hasattr(result, "close"):
            result.close


def test():
    headers_set = [1, 2]
    headers_sent = []
    status, response_header = headers_sent[:] = headers_set
    print(headers_sent)
    print(status, response_header)
    # raise (1, 2, 3)


if __name__ == "__main__":
    run_with_cgi(simple_app)
    # test()
