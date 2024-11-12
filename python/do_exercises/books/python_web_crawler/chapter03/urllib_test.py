import os.path
import re
import sys
import time
import urllib.request

from http.client import HTTPResponse


def main():
    time_s = time.time()
    print("send request...")

    url_value = "https://www.bing.com/"
    response = urllib.request.urlopen(url_value)

    print("get response..., time taken {:.4f} s".format(time.time() - time_s))
    print(response.status)
    print(response.getheaders())

    match = re.compile(r"//www\.(\w+)\.(\w+)").search(url_value)
    if match:
        captures = match.groups()
    else:
        captures = []
    target_file = os.path.basename(sys.argv[0])[:-3] + "_" + "_".join(captures) + ".html"
    with open(target_file, "w", encoding="utf-8") as file:
        time_s = time.time()
        file.write(response.read().decode("utf-8"))
        print("Writing the file `{}` succeeded. Time taken {:.4f} s".format(target_file, time.time() - time_s))


if __name__ == '__main__':
    main()
