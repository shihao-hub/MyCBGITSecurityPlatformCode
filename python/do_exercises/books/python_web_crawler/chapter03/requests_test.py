import functools
import time

import requests
from pprint import pprint


def clock(func):
    @functools.wraps(func)
    def clocked(*args, **kwargs):
        start_t = time.time()
        res = func(*args, **kwargs)
        # sys.stderr.write("cost: {}s\n".format(time.time() - start_t))
        print("cost: {}s".format(time.time() - start_t))
        return res

    return clocked


@clock
def main():
    # response = requests.get("http://127.0.0.1:8000/tests/test_list", headers={
    #     "Authorization": "Basic cm9vdDp6c2gyMDAxMDQxNw==",
    # })
    # print(response.status_code)
    # pprint(response.json())
    # pprint(response.headers)

    session = requests.session()
    response = session.get("http://127.0.0.1:8000/tests/test_list", headers={
        "Authorization": "Basic cm9vdDp6c2gyMDAxMDQxNw==",
    })
    pprint(response.json())


if __name__ == '__main__':
    main()
