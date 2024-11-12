import os

from util.debug.debug_env import is_debug_env

DEBUG = False  # 警告：要上线的时候再改成 False，只有上线的时候域名地址才允许改成正式环境的域名地址

if is_debug_env():
    DEBUG = True

DOMAIN = (DEBUG
          and "https://secevaluation-sit.cbgit.huawei.com/"
          or "https://secplatform.cbgit.huawei.com/")

BASE_DIR = os.path.dirname(__file__)
X_HW_ID = "20230712144356oPb6qe9XqPdEsBG10ZJW6ARrqiexKrGwtLoiDLe7FRA=1X@fi4FIczrGd3pz8n5CciZ/g=="
X_HW_APPKEY = "20230712144356rNVyb2csONf7Pn6IMivIFLid1OOMLNgvxNx1dNprHFs=1X@N5/6qgvXqeZnar7Aax4Z6Q=="
APP_ID_STATIC_CREDENTIAL = "20230712144356TS4Be5SdGZi3WUBIUZrchy+v8z18zpVDal0A01wl3IPoWBUC6b+HdMmGk1eLKYfMx3oM6hweX0pEIQJKSGB48eYNW/yr8N5JoQf01maaRu/X1bW28XxaMTj5uDs2wr8m1X@LF25nznx3IHnPQQmfd6sZw=="
