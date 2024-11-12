import pprint
import urllib.parse
from hashlib import md5
from multiprocessing.pool import Pool

import requests

base_url = "http://www.toutiao.com/search_content/"

debug = True


def get_page(offset):
    url = base_url + "?" + urllib.parse.urlencode({
        "offset": offset,
        "format": "json",
        "keyword": urllib.parse.quote("街拍")
    })

    if debug:
        return url

    response = requests.get(url)
    if response.status_code == 200:
        return response.json()

    return url


def main():
    res = []
    for i in range(20, 100 + 1, 20):
        res.append(get_page(i))

    pprint.pprint(res)

    pool = Pool()
    pool.map()


if __name__ == '__main__':
    main()
