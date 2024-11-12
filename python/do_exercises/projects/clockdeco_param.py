import functools
import time

DEFAULT_FMT = "[{elapsed:0.8f}s] {name}({args}) -> {result}"


def clock(fmt=DEFAULT_FMT):
    def out_wrapper(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):  # fixme
            t0 = time.perf_counter()
            ret = func(*args, **kwargs)
            elapsed = time.perf_counter() - t0
            name = func.__name__
            args = ", ".join(repr(arg) for arg in args)
            if kwargs:
                args += ", " + "**kwargs"
            result = repr(ret)
            # 此处 locals() 返回的是字典，而 **locals() 则代表传入键值对
            print(fmt.format(**locals()))
            return ret

        return wrapper

    return out_wrapper


if __name__ == '__main__':
    @clock()
    def snooze(seconds, key=2):
        time.sleep(seconds)


    for i in range(3):
        snooze(.123, key=3)
