import functools
import http.client
import pprint
import socket
import sys
import time
import urllib.request
import urllib.parse
from urllib.error import URLError
from urllib.request import HTTPPasswordMgrWithDefaultRealm, HTTPBasicAuthHandler, build_opener, ProxyHandler

# NOTE: urllib.request.urlopen -> HTTPResponse，所以有的时候可以不看源码，用 type(instance) 确定类型呀！
from http.client import HTTPResponse


def clock(func):
    @functools.wraps(func)
    def clocked(*args, **kwargs):
        start_t = time.time()
        res = func(*args, **kwargs)
        # sys.stderr.write("cost: {}s\n".format(time.time() - start_t))
        print("cost: {}s".format(time.time() - start_t))
        return res

    return clocked


def base():
    # response: http.client.HTTPResponse = urllib.request.urlopen("http://127.0.0.1:1060/")
    # pprint.pprint(response.__dict__)
    # pprint.pprint(response.getheaders())
    # print(response.read().decode("utf-8"))

    # NOTE: 设置权限、POST 请求、数据转化为比特流
    request = urllib.request.Request(url="http://127.0.0.1:8000/tests/test_list/", headers={
        "Authorization": "Basic cm9vdDp6c2gyMDAxMDQxNw==",
    })

    data = {
        "name": "abcdef"
    }
    data = urllib.parse.urlencode(data, encoding="utf-8").encode("utf-8")
    print("data(dict->str): {}".format(data))
    response = urllib.request.urlopen(url=request, data=data)
    print(response.read().decode("utf-8"))


def handle():
    url = "http://127.0.0.1:8000/tests/test_list/"
    p = HTTPPasswordMgrWithDefaultRealm()
    p.add_password(None, url, "root", "zsh20010417")
    auth_handler = HTTPBasicAuthHandler(p)
    opener = build_opener(auth_handler)

    try:
        response = opener.open(url)
        pprint.pprint(response.__dict__)
        pprint.pprint(response.read().decode("utf-8"))
    except URLError as e:
        print(e.reason)


def proxy():
    # url = "https://www.baidu.com"  # NOTE: [WinError 10061] 由于目标计算机积极拒绝，无法连接。

    url = "http://127.0.0.1:8000/tests/test_list/"

    p = HTTPPasswordMgrWithDefaultRealm()
    p.add_password(None, url, "root", "zsh20010417")
    auth_handler = HTTPBasicAuthHandler(p)

    proxy_handler = ProxyHandler({
        "http": "http://127.0.0.1:9743",
        "https": "https://127.0.0.1:9743",
    })
    opener = build_opener(auth_handler, proxy_handler)

    try:
        response = opener.open(url, timeout=0.03)
        pprint.pprint(response.__dict__)
        # pprint.pprint(response.read().decode("utf-8"))
    except URLError as e:
        print("---", type(e.reason))
        if isinstance(e.reason, socket.timeout):
            print("TIME OUT")
        else:
            print(e.reason)
    except Exception as e:
        print("---", type(e))
        print(e)


def urllib_parse():
    parse = urllib.parse

    url = "https://www.bing.com/search?q=%E9%98%85%E8%AF%BB%E4%BB%A3%E7%A0%81%E7%9A%84%E6%97%B6%E5%80%99%E7%94%BB%E5%9B%BE&qs=n&form=QBRE&sp=-1&lq=0&pq=%E9%98%85%E8%AF%BB%E4%BB%A3%E7%A0%81%E7%9A%84%E6%97%B6%E5%80%99hua%27tu&sc=10-13&sk=&cvid=7096E70F7F9A4E358FD9D7F8F4B6E689&ghsh=0&ghacc=0&ghpl=&ntref=1&dayref=1"
    url = parse.unquote(url)

    res = parse.urlparse(url)
    print(res)
    pprint.pprint([res[i] if i != 4 else parse.parse_qsl(res[i]) for i in range(len(res))])


@clock
def main():
    # response: http.client.HTTPResponse = urllib.request.urlopen("http://127.0.0.1:8000/")
    # pprint.pprint(response.__dict__)
    # pprint.pprint(response.getheaders())
    # print(response.read().decode("utf-8"))
    # base()
    # handle()
    # proxy()
    urllib_parse()


if __name__ == '__main__':
    main()
