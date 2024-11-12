import abc


class Handler(abc.ABC):
    @abc.abstractmethod
    def set_next(self, handler):
        # 设置当前处理器的下一个处理器，链表咯？
        pass

    @abc.abstractmethod
    def handle(self, request):
        pass


class AbstractHandler(Handler):
    def __init__(self):
        self._next_handler = None

    def set_next(self, handler):
        self._next_handler = handler
        # 返回 handler，可以让代码变成这样：handler1.set_next(handler2).set_next(handler3)
        return handler

    def handle(self, request):
        if self._next_handler:
            return self._next_handler.handle(request)
        return None


class ConcreteHandler1(AbstractHandler):
    def handle(self, request):
        if request == "request1":
            return "Handled by ConcreteHandler1"
        else:
            return super().handle(request)


class ConcreteHandler2(AbstractHandler):
    def handle(self, request):
        if request == "request2":
            return "Handled by ConcreteHandler2"
        else:
            return super().handle(request)


class ConcreteHandler3(AbstractHandler):
    def handle(self, request):
        if request == "request3":
            return "Handled by ConcreteHandler3"
        else:
            return super().handle(request)


if __name__ == '__main__':
    handler1 = ConcreteHandler1()
    handler2 = ConcreteHandler2()
    handler3 = ConcreteHandler3()

    handler1.set_next(handler2).set_next(handler3)

    # 2024-10-09：
    # 以上样例的目的如下
    # handler1 作为头，handler2 和 handler3 作为后置元素
    # 每个 handle 函数里，要么根据条件判断执行自己的逻辑，要么执行父类提供的 handle，
    # 而父类提供的 handle 是执行当前 handler 的下一个元素的 handle 函数。
    # 所以整体逻辑就是：遍历 handlers，找到那个满足条件以执行自己的逻辑的 handler 终止？
    # 				  这算啥？这最终不也就执行一个 handler 吗？

    # 发送请求
    requests = ["request1", "request2", "request3", "request4"]
    for request in requests:
        response = handler1.handle(request)
        if response:
            print(response)
        else:
            print(f"{request} was not handled")
