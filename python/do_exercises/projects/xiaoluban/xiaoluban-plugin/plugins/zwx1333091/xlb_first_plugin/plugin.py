import functools
import pprint
import re
import traceback

from util.msg import Msg
from util.api.by_token.send_msg import send_msg
from util.api.by_token.api import recv_next_msg

from common import clock, json2dict_safe, logger
from distributor import ISCLDistributor, TaskISCLDistributor, EflowISCLDistributor
from setting import DOMAIN


class Dispatch:
    choices = {"1": "icsl_gytask_task_distribute", "2": "icsl_gytask_eflow_distribute"}

    def __init__(self, msg: Msg, save_info: dict):
        self.msg = msg
        self.save_info = save_info
        self.base_url = (DOMAIN
                         + "sectas/"
                         + "publicservices/")

    @clock
    def dispatch(self):
        handler = getattr(self, self.choices[self.save_info["option"]])
        # logger(f"handler: {handler.__name__}")
        return handler()

    class DistributeHelperOnly:
        def __init__(self, msg, save_info, distributor):
            self.msg = msg
            self.save_info = save_info
            self.distributor = distributor

        def validate_input_format_and_content(self):
            keys, values = self.get_values_keys()
            return len(keys) == len(values)

        def validate_task_id(self):
            try:
                self.get_task_id()
            except ValueError:
                return False
            return True

        def get_values_keys(self):
            yield ("task_id", "distributor",)
            yield [e for e in re.split(r"(?:, *)|(?:， *)", self.msg.params)]

        def get_one_record_by_task_id(self):
            return self.distributor.get_one_record({
                "task_id": self.get_task_id(),
            })

        def get_task_id(self):
            try:
                task_id = int(self.save_info["task_id"])
            except ValueError:
                raise
            return task_id

        def get_employee_id(self):
            return self.save_info["distributor"]

        def update_save_info(self, data):
            self.save_info.update(data)

        def sender_is_executor(self, executor, sender):
            return executor == sender

        def get_distribute_body(self):
            return {
                "task_id": self.get_task_id(),
                "employee_no": self.get_employee_id(),  # 1
                "employee_id": self.get_employee_id(),  # 2
                "sender": self.msg.sender
            }

    def distribute(self, step_1_msg, distributor: ISCLDistributor):
        self.save_info["step"] += 1
        while True:
            step = self.save_info["step"]
            if step == 1:
                send_msg(step_1_msg, self.msg.receiver)
                recv_next_msg(self.msg, self.save_info)
            elif step == 2:
                # -----------------------------------------------------------------------------------------
                # 2024-07-02
                # 当前区域中的内嵌函数，后续是需要把他们移出去的，目前还放在这里是因为重构还没有结束
                #   注意事项：请写一下测试用例
                #       1. 校验格式，task_id 要是数字，输入内容要形如 123,zhangsan 123456
                #       2. 校验处理人和分发人，想要分发，发送人必须是当前的处理人
                #       3. ...... （好像有点太麻烦），TTD 到底怎么做到呢
                #   这边的重构流程是学习《重构》这本书的，感觉收获很少，《重构》这本书应该是需要多经历才有体会。
                # 2024-07-12：学到了一个命名法，形如 deliverDateHelperOnly，让人一见即知不应该直接使用这个类/函数

                # def validate_input_format_and_content():
                #     keys, values = get_values_keys()
                #     return len(keys) == len(values)
                #
                # def validate_task_id():
                #     try:
                #         get_task_id()
                #     except ValueError:
                #         return False
                #     return True
                #
                # def get_values_keys():
                #     yield ("task_id", "distributor",)
                #     yield [e for e in re.split(r"(?:, *)|(?:， *)", self.msg.params)]
                #
                # def get_one_record_by_task_id():
                #     return distributor.get_one_record({
                #         "task_id": get_task_id(),
                #     })
                #
                # def get_task_id():
                #     try:
                #         task_id = int(self.save_info["task_id"])
                #     except ValueError:
                #         raise
                #     return task_id
                #
                # def get_employee_id():
                #     return self.save_info["distributor"]
                #
                # def update_save_info(data):
                #     self.save_info.update(data)
                #
                # def sender_is_executor(executor, sender):
                #     return executor == sender
                #
                # def get_distribute_body():
                #     return {
                #         "task_id": get_task_id(),
                #         "employee_no": get_employee_id(),  # 1
                #         "employee_id": get_employee_id(),  # 2
                #         "sender": self.msg.sender
                #     }

                # 传参这里应该也能用到重构列表中的重构方法
                helper = self.DistributeHelperOnly(self.msg,self.save_info,distributor)
                # 注意，Python 这样传递对象方法的时候，应该是使用了类似 functools.partial 这样的功能固定了第一个参数
                validate_input_format_and_content = helper.validate_input_format_and_content
                update_save_info = helper.update_save_info
                get_values_keys = helper.get_values_keys
                validate_task_id = helper.validate_task_id
                get_one_record_by_task_id = helper.get_one_record_by_task_id
                sender_is_executor = helper.sender_is_executor
                get_distribute_body = helper.get_distribute_body
                get_task_id = helper.get_task_id
                get_employee_id = helper.get_employee_id

                # -----------------------------------------------------------------------------------------

                if not validate_input_format_and_content():
                    self.session_go_back("输入的内容格式不正确，请重新输入！", 1)
                    continue

                # 这里也需要重构，因为 update_save_info 必须在 validate_task_id 之前执行，状态依赖，这不太好
                #   而且说实话，get_values_keys 这个函数抽象的很有问题，不如展开呢。
                #       2024-07-02-14:12 目前 get_values_keys 有两个调用点
                update_save_info(dict(zip(*get_values_keys())))

                if not validate_task_id():
                    self.session_go_back("输入的任务 ID 不是数字，请重新输入！", 1)
                    continue

                record_json = get_one_record_by_task_id()
                if record_json.get("status", "") == "Error":
                    self.session_go_back(record_json["msg"], 1)
                    continue
                elif not record_json["data"]:
                    self.session_go_back("任务未查询到，请检查你输入的任务 ID 是否存在！", 1)
                    continue

                if not sender_is_executor(distributor.get_executor(record_json),
                                          distributor.cut_out_number(self.msg.sender)):
                    self.session_go_back("你不是当前任务的处理人，请重新输入！", 1)
                    continue

                distribute_json = distributor.distribute(get_distribute_body())
                if distribute_json.get("status", "") == "Error":
                    self.session_go_back(distribute_json["msg"], 1)
                    continue
                else:
                    send_msg(distribute_json["msg"] + "\n"
                             + f"任务 ID：{get_task_id()}，分发人：{get_employee_id()}，发送人：{self.msg.sender}\n",
                             self.msg.receiver)

            # 正常只需要成功执行一遍就会退出，while True 的目的是，出现输入格式不正常的时候继续循环处理
            break

    def icsl_gytask_task_distribute(self):
        return self.distribute(("请输入：\n"
                                "        ICSL 送检预验证 任务 ID\n"
                                "        分发人的完整工号\n"
                                "（分隔符为逗号，例如 1000, zhangsan WX123456, ...）"),
                               TaskISCLDistributor(self.base_url,
                                                   "gytask/byXLB",
                                                   "gytask/distribute/byXLB", ))

    def icsl_gytask_eflow_distribute(self):
        return self.distribute(("请输入： \n"
                                "        ICSL 送检测试 电子流 ID\n"
                                "        分发人的完整工号\n"
                                "（分隔符为逗号，例如 1000, zhangsan WX123456, ...）"),
                               EflowISCLDistributor(self.base_url,
                                                    "eflow/byXLB",
                                                    "eflow/distribute/byXLB", ))

    @classmethod
    def raise_option_exception(cls, option):
        raise RuntimeError(f"不存在这个选项，对话终止 ({option})")

    @classmethod
    def check_option(cls, option):
        if option not in cls.choices:
            cls.raise_option_exception(option)

    def session_go_back(self, msg, step):
        send_msg(msg, self.msg.receiver)
        self.save_info["step"] = step


def handle(msg: Msg):
    if msg.is_first_input():
        send_msg('当前支持功能：\n'
                 '    1、ICSL送检预验证分发\n'
                 '    2、ICSL送检测试电子流分发\n'
                 '请输入数字选择（输入不在列表内的数字会抛出异常）', msg.receiver)
        recv_next_msg(msg, {"option": "0", "step": 0})  # 表示会接收用户发的的下一条消息
    else:
        save_info = json2dict_safe(msg.save_info)

        if save_info["option"] == "0":
            option = msg.params

            Dispatch.check_option(option)

            save_info["option"] = option

        Dispatch(msg, save_info).dispatch()


if __name__ == '__main__':
    from util.debug.debug import debug_handle

    user_input = '/'
    debug_handle(handle, user_input)
