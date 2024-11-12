from urllib.request import HTTPPasswordMgrWithDefaultRealm, HTTPBasicAuthHandler, build_opener
from urllib.error import URLError, HTTPError

config = {
    "username": "ZWX1333091",
    "password": "Zsh20010417.",
    "url": "https://secevaluation-sit.cbgit.huawei.com/api/gytask/dtses/",
}
p_obj = HTTPPasswordMgrWithDefaultRealm()
p_obj.add_password(None, config["url"], config["username"], config["password"])

auth_handler = HTTPBasicAuthHandler(p_obj)

opener = build_opener(auth_handler)

try:
    res = opener.open(config["url"])
    html = res.read().decode("utf-8")
    print(html)
except URLError as e:
    print(e.reason)
