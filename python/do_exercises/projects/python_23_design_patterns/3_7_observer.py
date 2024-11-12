import abc


# 2024-10-08
# Q: 继承 abc.ABC 的类算是接口吧？还是类似 Java 的抽象类，支持默认函数？
# A: 运行的时候没发现什么问题，得去看看代码规范建议不建议这样做。

class Subject(abc.ABC):
    def __init__(self):
        self._observers = set()

    def attach(self, observer):
        """ 注册观察者（观察者订阅） """
        self._observers.add(observer)

    def detach(self, observer):
        """ 注销观察者（观察者取消订阅） """
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, modifier=None):
        """ 广播 """
        for observer in self._observers:
            # 中介者模式的样例代码和观察者模式区别并不大，这是为何呢？是不是中介者模式的样例不够鲜明。
            if modifier != observer:
                # 观察者模式的缺点是，
                # 它可能会导致过多的细节传递，因为主题在通知观察者时必须传递详细信息。
                # 这可能会导致性能问题或安全问题，因为观察者可以访问到主题的私有信息。
                observer.update(self)


class Observer(abc.ABC):
    @abc.abstractmethod
    def update(self, subject):
        pass


class ConcreteSubject(Subject):
    def __init__(self):
        super().__init__()
        self._state = None

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        # 该被观察者的状态发生变化时，通知所有订阅方。订阅方会调用它自己实现的 update 函数。
        self._state = state
        self.notify()


class ConcreteObserver(Observer):
    def __init__(self, name):
        self._name = name

    def update(self, subject):
        print(f'{self._name} received an update: {subject.state}')


def unittest():
    # 测试驱动开发？这类知识，找到个稳定的工作再说吧。目前最主要的还是工程实践也就是项目经验。（2024-10-08）
    subject = ConcreteSubject()
    observer1 = ConcreteObserver('Observer 1')
    observer2 = ConcreteObserver('Observer 2')
    subject.attach(observer1)
    subject.attach(observer2)

    subject.state = 123
    subject.detach(observer1)

    subject.state = 456


if __name__ == '__main__':
    unittest()
