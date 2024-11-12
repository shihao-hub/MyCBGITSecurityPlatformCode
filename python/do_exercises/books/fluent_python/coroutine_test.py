import functools
import traceback
from asyncio import coroutine
from inspect import getgeneratorstate


def pre_active_coroutine(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        gen = func(*args, **kwargs)
        gen.send(None)
        return gen

    return wrapper


@pre_active_coroutine
def cor_test():
    x = yield 0
    print("第一次激活")
    y = yield 1
    print("第二次激活")
    z = yield 2
    print("第三次激活，生成器将结束")


gen = cor_test()

print(getgeneratorstate(gen))


try:
    print(gen.send(11))
    # print(gen.send(22))
    # print(gen.send(33))
    gen.close()
except Exception as e:
    print(traceback.format_exc())
finally:
    print("finally->", getgeneratorstate(gen))

# try:
#     gen.close()
# except Exception as e:
#     print(e)

# print(gen.throw(RuntimeError))

# compute_duration
