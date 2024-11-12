from abc import ABC, abstractmethod


# Command 接口
class Command(ABC):
    """ 命令接口，该接口包含一个 execute 方法，用于执行命令。 """

    @abstractmethod
    def execute(self):
        pass


class LightOnCommand(Command):
    """ 具体命令类 """

    def __init__(self, light):
        # 命令接收者
        self.light = light

    def execute(self):
        self.light.turn_on()


class LightOffCommand(Command):
    """ 具体命令类 """

    def __init__(self, light):
        self.light = light

    def execute(self):
        self.light.turn_off()


class RemoteControl:
    """
        Invoker 类，用于发送命令。
        可以理解为遥控器或者中介者模式的聊天室对象等，主要用来存储命令和执行全部命令。
        该类的主要作用应该是将请求统一存储和集中（命令注册处）。
        至于请求发送者和接收者解耦，我目前看不出来。所以我目前应该也不知道命令模式的使用场景。（2024-10-09）
    """

    def __init__(self):
        self.commands = []

    def add_command(self, command):
        self.commands.append(command)

    def execute_commands(self):
        # 为什么要执行全部命令呢？如果以遥控器为例的话，理当提供的功能是执行单个命令吧？
        for command in self.commands:
            command.execute()


class Light:
    """ Receiver 类，用于执行命令 """

    def turn_on(self):
        print("The light is on")

    def turn_off(self):
        print("The light is off")


if __name__ == '__main__':
    light = Light()

    remote_control = RemoteControl()
    remote_control.add_command(LightOnCommand(light))
    remote_control.add_command(LightOffCommand(light))

    remote_control.execute_commands()
