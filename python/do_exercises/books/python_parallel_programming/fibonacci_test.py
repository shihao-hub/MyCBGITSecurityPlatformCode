import functools
import time


def cal_exc_time(func):
    def fn(*args, **kwargs):
        res = func(*args, **kwargs)
        return res

    def wrap(*args, **kwargs):
        time_s = time.time()
        res = fn(*args, **kwargs)
        print("cost {} s".format(time.time() - time_s))
        return res

    return wrap


def calculate_execute(func, *args, **kwargs):
    time_s = time.time()
    res = func(*args, **kwargs)
    return res, "cost {} s".format(time.time() - time_s)


# @functools.cache
def fib(n):
    if n <= 2:
        return 1
    return fib(n - 2) + fib(n - 1)


@cal_exc_time
def _fib(n):
    return fib(n)


print(_fib(10))
print(_fib(20))

# print(calculate_execute(fib, 100))
# print(calculate_execute(fib, 200))
