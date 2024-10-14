import datetime
import functools
import logging
import traceback
from dateutil import relativedelta
from typing import TypeVar, Generic

import pytz

from django.utils import timezone

# 为了兼容，不要删除
from measure.pydantic_models.utils import PydanticCustomBaseModel, PydanticConstant

T = TypeVar("T")

logger = logging.getLogger("mylogger")


def get_last_month_begin_and_end():
    """ 获得上个月的起始，ISO 格式 """
    java_date_format = "%Y-%m-%dT%H:%M:%S.%fZ"

    # 获取上个月的月初和月末，这个相对有点小麻烦吧？但是我为什么觉得本不该这样麻烦呢？（2024-09-24）
    # #(C)!: today = pytz.timezone("Asia/Shanghai").localize(timezone.now())
    # 作战平台那边是 UTC 时间格式
    today = pytz.utc.localize(timezone.now())
    last_month_today = today - relativedelta.relativedelta(months=1)
    first_day_info = dict(day=1, hour=0, minute=0, second=0, microsecond=0)

    last_month_begin = (last_month_today.replace(**first_day_info)
                        .strftime(java_date_format)
                        .replace("000Z", "Z"))
    last_month_end = ((today.replace(**first_day_info) - datetime.timedelta(microseconds=1))
                      .strftime(java_date_format)
                      .replace("999Z", "Z"))
    return last_month_begin, last_month_end


class CustomException(Exception):
    """ 除了可以携带 message，还能携带 data 的异常类 """

    def __init__(self, *args, data=None):
        super().__init__(*args)
        self.data = data


class OutputParameter(Generic[T]):
    """ 输出参数类，当然，这是违背《重构》这本书的理念的，该书不建议使用输出参数 """

    def __init__(self, value: T = None):
        # init 的参数 value: T 不会让代码分析工具误解吗？但是 Optional[T] 也会误解吧？
        # 目前来说，没发现什么问题，确实方便了许多，之后再看吧！
        self._value: T = value

    def set_value(self, value: T):
        self._value = value

    def get_value(self) -> T:
        return self._value

    def __str__(self):
        return str(self._value)


def pdebug(msg):
    logger.debug("%s", msg)


def pinfo(msg):
    logger.info("%s", msg)


def pwarning(msg):
    logger.warning("%s", msg)


def perror(msg):
    logger.info("%s", msg)


def validate_assumption(expr, msg=None):
    # check_hypothesis、validate_assumption、is_hypothesis_valid
    # evaluate_hypothesis、verify_hypothesis、test_hypothesis、check_condition
    # 不理解 AssertionError 的意义，还是用我遵循的原则吧：及时出错，哪里还区分什么测试环境、正式环境
    # assert 的作用我觉得需要 程序员的技术能力强 + 测试人员的技术能力强 时才有所体现
    if not expr:
        raise RuntimeError(f"表达式不为真{(' -> ' + msg) if msg else ''}"
                           f"\n{traceback.format_exc()}")


def get_namedtuple_keys(inst) -> tuple:
    return tuple(inst._asdict().keys())  # NOQA


def get_namedtuple_values(inst) -> tuple:
    return tuple(inst._asdict().values())  # NOQA


def get_dict_data_by_keys(data, keys, default=None, process_fn=None) -> dict:
    """
        顾名思义，以 keys 元素为键，去 data 中取值。
            step1. 若不存在，则赋值为 default。
            step2. 若存在，则取出来，若 fn 存在，则还会处理一下值。
    """
    res = {}
    for k in keys:
        val = default if data.get(k) is None else data.get(k)
        if val is not None:
            res[k] = val if not process_fn else process_fn(val)
    return res


def time_difference(minuend_time, subtrahend_time) -> datetime.timedelta:
    """ 计算两个日期的差值 """
    minuend_time, subtrahend_time = map(str, (minuend_time, subtrahend_time,))
    date_format = "%Y-%m-%d"
    minuend_date = datetime.datetime.strptime(minuend_time, date_format)
    subtrahend_date = datetime.datetime.strptime(subtrahend_time, date_format)
    res_date = minuend_date - subtrahend_date
    return res_date


def _generate_decorator_for_marking(func):
    """ 生成表示用的装饰器 """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def decorator_is_web_interface(func):
    """ 顾名思义，一个普通的装饰器，标识一下是 web 接口而已
            目前（2024-08-20）没有添加其他作用
    """
    return _generate_decorator_for_marking(func)


def decorator_refactored(func):
    """ 标识已经被重构过，方便使用编辑器的检索功能 """
    return _generate_decorator_for_marking(func)


def decorator_deprecated(_logger):
    """ 标识该函数已经过时 """

    def outer(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            res = func(*args, **kwargs)
            _logger.info("%s", f"警告：`{func.__name__}` 已经被废弃")
            return res

        return wrapper

    return outer
