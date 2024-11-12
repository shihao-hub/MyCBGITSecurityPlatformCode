import json
import time
import functools

def logger(*args, **kwargs):
    print("zsh->", *args, **kwargs)


def clock(func):
    @functools.wraps(func)
    def wrap(*args, **kwargs):
        time_s = time.time()
        res = func(*args, **kwargs)
        logger(f"call {func.__name__} cost {time.time() - time_s} s")
        return res

    return wrap


@clock
def json2dict_safe(data):
    save_info = None
    try:
        save_info = json.loads(data)
    except Exception as e:
        logger(f"error: {e}")
    return save_info or {}
