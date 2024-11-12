import pprint
import re
import traceback
import urllib.parse
from abc import abstractmethod

import requests
from cachetools import TTLCache, cached
from requests.status_codes import codes as status

from plugins.l30021226.secplatfrom_review_plugin.common import SecPlatformAPIs

from util.debug.local import decrypt
from setting import X_HW_ID, APP_ID_STATIC_CREDENTIAL
from common import logger


@cached(cache=TTLCache(maxsize=1, ttl=290))
def get_his_dynamic_token():
    url = 'https://oauth2.huawei.com/ApiCommonQuery/appToken/getRestAppDynamicToken'
    payload = {
        'appId': decrypt(X_HW_ID),
        'credential': decrypt(APP_ID_STATIC_CREDENTIAL)
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers, verify=False)
    if response.status_code == 200:
        data = response.json()
        dynamic_token = data.get("result")
    else:
        raise Exception(f'Failed to get HIS dynamic token. Res:{response.text}')
    return dynamic_token


# -------------------------------------------------------------------------------------------- 基础设计模式：继承、多态
class ISCLDistributor:
    _cut_pattern = None

    def __init__(self, base_url: str, api1: str = None, api2: str = None):
        self.base_url = base_url.endswith("/") and base_url or base_url + "/"
        self.api1 = self._process_api_format(api1)
        self.api2 = self._process_api_format(api2)

    @classmethod
    def _generate_authorization_header(cls):
        # return {}
        return {
            "X-HW-ID": "com.huawei.m00544510",
            "Authorization": get_his_dynamic_token()
        }

    @classmethod
    def cut_out_number(cls, cut):
        logger(cls._cut_pattern)
        if not cls._cut_pattern:
            cls._cut_pattern = re.compile(r".*?(\d+).*")
        logger(cls._cut_pattern)
        try:
            res = cls._cut_pattern.match(cut).group(1)
        except Exception as e:
            logger(f"错误原因：{e}")
            raise Exception(f"{cut} 中没有匹配到数字")
        return res

    @classmethod
    def _process_api_format(cls, api):
        if not api:
            return api
        return api.startswith("/") and api.replace("/", "", 1) or api

    @classmethod
    def _check_status_ok(cls, response):
        if response.status_code != status.ok:
            logger(response.json())
            raise requests.exceptions.HTTPError(f"response.status_code({response.status_code}) != {status.ok}")

    @abstractmethod
    def get_executor(self, resp_json_data):
        pass

    def get_one_record(self, query=None, api=None):
        api = self._process_api_format(api) or self.api1
        url = self.base_url + api
        if query:
            url += "?" + urllib.parse.urlencode(query)
        headers = self._generate_authorization_header()
        # logger(url)
        # logger(headers)
        # 记得超时处理
        response = requests.get(url, verify=False, headers=headers, timeout=10)
        logger(response.json())
        self._check_status_ok(response)
        return response.json()

    def distribute(self, data, api=None):
        api = self._process_api_format(api) or self.api2
        url = self.base_url + api
        headers = self._generate_authorization_header()
        response = requests.post(url, json=data, verify=False, headers=headers, timeout=10)
        logger(response.json())
        # 分发人未在平台注册的时候，怎么会返回 400 状态码的？
        # self._check_status_ok(response)
        return response.json()


class TaskISCLDistributor(ISCLDistributor):
    def get_executor(self, resp_json_data):
        return self.cut_out_number(resp_json_data["data"]["executors"])


class EflowISCLDistributor(ISCLDistributor):
    def get_executor(self, resp_json_data):
        return self.cut_out_number(resp_json_data["data"]["handler"])


if __name__ == '__main__':
    pre_validation = ISCLDistributor("https://httpbin.org/", "/get", "/post")
    pprint.pprint(pre_validation.get_one_record(query={
        "name": "zsh"
    }))
    pprint.pprint(pre_validation.distribute(data={
        "employee_id": "213191443"
    }))
