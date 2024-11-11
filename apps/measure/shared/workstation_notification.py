import ast
import configparser
import contextlib
import datetime
import json
import logging
import os.path
import threading
import traceback
import typing as t
import urllib.parse
from typing import Optional, List, Dict

from django.conf import settings
from django.db import models
from django.db.models import When, Case, Value, F, DateField, IntegerField
from django.db.models.functions import TruncDate, TruncDay
from django.utils import timezone

from measure.models import MissTaskImprove
from measure.shared.universal_utils import CustomException
from utils.common import send_feedmsg

logger = logging.getLogger("mylogger")

# 共享资源
_notification_manager: Optional["NotificationManager"] = None

config = configparser.ConfigParser()
config.read(os.path.join(settings.BASE_DIR, "apps", "measure", "shared", "workstation_notification.ini"))


@contextlib.contextmanager
def synchronized():
    # 锁定代码块（和 Java synchronize 一样使用即可）
    lock = threading.Lock()  # 创建一个锁
    lock.acquire()
    yield
    lock.release()


class NotificationManager:
    DELAYED_NOTIFICATION_TIME_POINTS = (1, 3, 7,)

    class AppServiceData:
        def __init__(self, context=None, title=None, content=None, msg_type=1, jump_url=""):
            self.context = context if context else {}
            self.title = title
            self.content = content
            self.msg_type = msg_type
            self.jump_url = jump_url

    @staticmethod
    def get_domain():
        return settings.DOMAIN

    @staticmethod
    def get_instance():
        # 单例模式，但是 Python 不是那么合适吧？构造函数没法隐藏
        def assign_value_and_lock():
            # 临界区
            global _notification_manager
            if _notification_manager is None:
                _notification_manager = NotificationManager()

        global _notification_manager
        if _notification_manager is None:
            logger.info("%s", f"_notification_manager is None，当前线程 id：{threading.currentThread().ident}")
            # 锁定代码块
            with synchronized():
                assign_value_and_lock()
        return _notification_manager

    @classmethod
    def get_jump_url(cls, query=""):
        jump_url = ("https://"
                    + cls.get_domain()
                    + f"/commonSecurity/reImprove/reImproveManage"
                    + query)
        logger.info("%s", f"app.jump_url={jump_url}")
        return jump_url

    def __init__(self):
        pass

    def _get_common_title(self):
        this = self
        title = "逆向改进通知"
        if settings.DEBUG:
            title = title + "（正式环境不会出现这个括号及其中的内容）"
        return title

    def _get_queryset_of_day_to_closed_plan_is(self, interval_day):
        this = self
        # 2024-09-29：时间计算，没有系统了解，每次写都要去查一查，这太常用了，不该如此。
        close_plan_time = Value(timezone.now().date() + datetime.timedelta(days=interval_day - 1))
        improve_qs = (MissTaskImprove.objects.filter(close_plan_time=close_plan_time,
                                                     YN_delete=0,
                                                     close_status=MissTaskImprove.CloseStatus.OPEN))
        for inst in improve_qs:
            yield inst

    def _modify_receivers_in_test_environment(self, receivers):
        this = self
        if not settings.DEBUG:
            return receivers
        # 首先，肯定要发给我本人，其次只能发给我们平台的人
        must_receivers = ast.literal_eval(config.get("debug_receivers", "must_receivers"))
        platform_people = ast.literal_eval(config.get("debug_receivers", "platform_people"))

        res = []
        res.extend(must_receivers)
        for receiver in receivers:
            if receiver in platform_people:
                res.append(receiver)

        logger.info("%s", f"测试环境，源接收人：{receivers}，现接收人：{res}")
        return res

    def _notify(self, receivers: List, title, content, msg_type=1, jump_url=""):
        this = self
        receivers = self._modify_receivers_in_test_environment(receivers)

        try:
            send_feedmsg(receivers, title, content, msg_type, jump_url=jump_url)
        except Exception as e:
            # 发送应用号出错，选择让其不崩溃。
            logger.error("%s", f"发送应用号通知失败，原因：{e}")

    def notify_when_distribute_test_manager(self, user_list: List, context: Dict):
        """ 指定测试项目经理后，发应用号给被分发者 """
        title = self._get_common_title()

        # 应用号的尊敬两个字为 7 个空格？
        content = (f"尊敬的安全测试平台用户，您好：\n"
                   f"       您已被指定为逆向改进问题 {context.get('dts_no')} 的测试经理，请点击前往安全测试平台。")

        row_data = urllib.parse.quote(json.dumps({
            **{
                k: v
                for k, v in context.items()
                if k in ["control_point", "description", "dts_no", "id", "level", "task_type", "yn_common", ]},
        }))
        self._notify(user_list, title, content, jump_url=self.get_jump_url(query=f"?rowData={row_data}"))

    def notify_when_reform_executor_modified(self, user_list: List, context: Dict):
        """ 改进措施责任人修改后，发应用号给改进措施责任人 """
        return self._notify_improve_common(user_list, context)

    def notify_when_analysis_completed_and_confirmed(self, user_list: List, context: Dict):
        """ 分析完成+确认状态已确认后，发应用号给改进措施责任人 """
        return self._notify_improve_common(user_list, context)

    def notify_closed_loop_when_completed(self, user_list: List, context: Dict):
        """ 闭环完，给验收责任人发应用号 """
        title = self._get_common_title()

        content = (f"尊敬的安全测试平台用户，您好：\n"
                   f"       您有一个逆向改进问题 {context.get('dts_no')} 待验收，请点击前往安全测试平台。")

        row_data = urllib.parse.quote(json.dumps({
            **{
                k: v for k, v in context.items()
                if k in ["control_point", "description", "dts_no", "id", "level", "task_type", "yn_common", ]
            },
            "tab_type": 1
        }))
        self._notify(user_list, title, content, jump_url=self.get_jump_url(query=f"?rowData={row_data}"))

    def notify_periodically_before_closed_loop_plan(self):
        """ 闭环计划前的 1天，3天，7天自动给改进措施责任人发应用号提醒 """
        # 2024-09-23：这个应该在 tasks.py 文件中执行。这个要用到 Django-Celery。
        try:
            title = self._get_common_title()
            content_template = ("您有一个逆向改进问题 {dts_no} 的改进措施计划于 {close_plan_time} 闭环，"
                                "预计还有 {interval_day} 天到期，请点击前往安全测试平台。")

            for interval_day in self.DELAYED_NOTIFICATION_TIME_POINTS:
                count = 0
                for inst in self._get_queryset_of_day_to_closed_plan_is(interval_day):
                    if inst.reform_executor:
                        count += 1
                        content = content_template.format(**dict(
                            dts_no=inst.dts_no[0],
                            close_plan_time=inst.close_plan_time,
                            interval_day=interval_day,
                        ))

                        detail_inst = inst.get_misstaskdetail_obj()
                        row_data = urllib.parse.quote(json.dumps({
                            "control_point": detail_inst.control_point,
                            "description": detail_inst.description,
                            "dts_no": detail_inst.dts_no,
                            "id": detail_inst.id,
                            "level": detail_inst.level,
                            "task_type": detail_inst.misstask.task_type,
                            "yn_common": detail_inst.yn_common,

                            "tab_type": 0
                        }))
                        query = f"?rowData={row_data}"
                        self._notify([inst.reform_executor], title, content, jump_url=self.get_jump_url(query=query))
                logger.info("%s", f"【闭环计划前自动给改进措施责任人发应用号提醒】【{interval_day}-{count}】")
        except Exception as e:
            raise CustomException(f"{e}\n{traceback.format_exc()}") from e

    def _notify_improve_common(self, user_list: List, context: Dict):
        """ 改进页面通用应用号通知 """
        title = self._get_common_title()

        content = (f"尊敬的安全测试平台用户，您好：\n"
                   f"       您有一个逆向改进问题 {context.get('dts_no')} 的改进措施待处理，请点击前往安全测试平台。")

        row_data = urllib.parse.quote(json.dumps({
            **{
                k: v
                for k, v in context.items()
                if k in ["control_point", "description", "dts_no", "id", "level", "task_type", "yn_common", ]
            },
            "tab_type": 0  # 2024-10-23：与前端约定，tab_type = 0 是待改进页面，tab_type = 1 是待验收页面
        }))
        self._notify(user_list, title, content, jump_url=self.get_jump_url(query=f"?rowData={row_data}"))
