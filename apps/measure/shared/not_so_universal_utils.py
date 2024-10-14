import logging
import traceback

from measure.models import MissTaskModel
from measure.utils import get_cn_name
from utils.common import global_error_response

logger = logging.getLogger("mylogger")


def unexpected_error_occurred(e, msg="", where=""):
    logger.error("%s", f"{e}\n{traceback.format_exc()}")
    # 这个括号是必须加的，因为 if else 优先级高于 +
    return global_error_response(msg=f"`{where}`发生错误" + (f"：{msg}" if msg else ""))


def get_cn_name_else(en_name, d=None):
    """ 这个 else 的语法很好用，借鉴 Rust 的，虽然目前我只了解了 Rust 的皮毛 """
    return get_cn_name(en_name) if en_name else d


def generate_executor_map(request_data):
    """
        出现了多次，因此抽取出来
            create_misstaskdetail_instance
            update_executors
        形如：
            {
                "变量名（数据库列名）":"执行人对应的中文名（发来的请求是英文名）",
                ...
            }
    """
    executor_map = {
        e: get_cn_name_else(request_data.get(e), "")
        for e in MissTaskModel.EXECUTOR_VARIABLE_NAMES
    }
    return executor_map
