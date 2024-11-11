import ast
import collections
import enum
import logging
from collections import namedtuple
from types import MappingProxyType, SimpleNamespace
from typing import (
    Any, Union, Optional,
    List, Tuple, Dict, Set, Sequence,
    Callable, Iterator, Generator,
    TypeVar, Generic
)

from django.db import models, connection
from django.db.models.functions import TruncDate, TruncYear, TruncMonth
from django.db.models import Q, Count, F, Case, When, Value, BooleanField
from django.utils import timezone

from measure.shared.universal_utils import get_namedtuple_values
from filing.models import FilingFile
from utils.custom_field import CustomListField

logger = logging.getLogger("mylogger")


# -------------------------------------------------------------------------------------------------------------------- #
# (Q)!: 模型类如何继承和混入？继承的话会被创建表吧？混入的话，cls 如何确定是哪个？ class BaseMixin:
class BaseMixin:
    # 在改混入类中新增函数的时候，一定要注意不要将 model.Model 类中的方法覆盖了！
    @classmethod
    def get_verbose_name_by_var_name(cls, var_name):
        """ 根据字段名获取该字段对应的 verbose_name """
        try:
            field = cls._meta.get_field(var_name)
            return field.verbose_name
        except KeyError as e:
            raise RuntimeError(f"{cls.__class__} 类中不存在 {var_name} 字段") from e

    @classmethod
    def get_verbose_name(cls, var_name):
        # 原函数太长了，缩短一点
        return cls.get_verbose_name_by_var_name(var_name)


# -------------------------------------------------------------------------------------------------------------------- #
class MappingEnum(enum.Enum):
    # (Q)!: 命名好困难，命名成什么好？
    BASE = 0
    RELATED = 1
    EXECUTOR = 2


class CnVar:
    # 【警告】此处的常量不允许轻易修改，牵连的地方过多，如果要修改，数据库也要修改才行！
    # 2024-09-26：此处的常量目前我认为，就是和数据库对应的那些！
    #             这里的值和前端、Excel 导入导出还有些细微差别，之后要注意！三方如果能统一那就最好了！
    case_baseline = "特性 / 用例基线"
    product_improve = "产品改进"
    manage = "管理 & 流程"
    code_check = "CodeCheck规则"
    auto = "自动化用例 & 工具"
    open_source_governance = "开源治理规则改进"
    security_architecture = "安全架构 & 方案"
    secure_coding = "安全编码"  # 2024-09-26：`安全编码治理策略` -> `安全编码`
    secure_baseline = "安全基线"
    security_tool = "安全平台 / 工具"  # 2024-09-26：`安全平台/工具` -> `安全平台 / 工具`
    security_measures = "安防策略或措施"
    compliance_policies = "合规策略 & 用例"
    security = "安防策略"


# -------------------------------------------------------------------------------------------------------------------- #
# 2024-09-26：这个命名及其不合适，除非分析代码，不然没人知道这是什么意思！但是我也不知道取什么名字好呀...
COMMON_MAPPING: Dict[str, List[str]] = {
    CnVar.case_baseline: ["case_baseline", "case_baseline_related", "case_baseline_executor"],
    CnVar.product_improve: ["product_improve", "product_improve_related", "product_improver"],
    CnVar.manage: ["manage", "manage_related", "manage_executor"],
    CnVar.code_check: ["code_check", "code_check_related", "code_check_executor"],
    CnVar.auto: ["auto", "auto_related", "auto_executor"],
    CnVar.open_source_governance: ["open_source_governance",
                                   "open_source_governance_related",
                                   "open_source_governance_executor"],
    CnVar.security_architecture: ["security_architecture",
                                  "security_architecture_related",
                                  "security_architecture_executor"],

    CnVar.secure_coding: ["secure_coding", "secure_coding_related", "secure_coding_executor"],
    CnVar.secure_baseline: ["secure_baseline", "secure_baseline_related", "secure_baseline_executor"],
    CnVar.security_tool: ["security_tool", "security_tool_related", "security_tool_executor"],
    CnVar.security_measures: ["security_measures", "security_measures_related", "security_measures_executor"],
    CnVar.compliance_policies: ["compliance_policies",
                                "compliance_policies_related",
                                "compliance_policies_executor"],
    CnVar.security: [None, None, "security_executor"],  # 注意，为空代表不使用

}


def get_related_name(base_name):
    """ 形如 case_baseline -> case_baseline_related """
    return COMMON_MAPPING.get(getattr(CnVar, base_name))[MappingEnum.RELATED.value]


def get_related_name_by_en(name):
    return get_related_name(name)


def get_executor_name(base_name):
    """ 形如 case_baseline -> case_baseline_executor """
    return COMMON_MAPPING.get(getattr(CnVar, base_name))[MappingEnum.EXECUTOR.value]


def get_executor_name_by_en(name):
    return get_executor_name(name)


def get_executor_name_by_cn(name):
    # 2024-09-26：该平台又不涉及国际化，cn 的意思就是我数据库存的值，这样好理解
    return COMMON_MAPPING.get(name)[MappingEnum.EXECUTOR.value]


# -------------------------------------------------------------------------------------------------------------------- #

def _generate_mapping(mapping_type: MappingEnum) -> dict:
    index = mapping_type.value
    return {k: v[index] for k, v in COMMON_MAPPING.items() if v[index]}


def _add_owner(val):
    """ 添加个责任人后缀 """
    return val + "责任人"


def _add_related(val):
    """ 添加 是否涉及 前缀 """
    return "是否涉及" + val


# -------------------------------------------------------------------------------------------------------------------- #
class AutoSendMonthReportUser(models.Model):
    username = models.CharField("用户名", max_length=20, unique=True)
    password = models.CharField("加密后的密码", max_length=1000)

    class Meta:
        db_table = "t_auto_send_month_report_user"
        verbose_name = verbose_name_plural = "发送月报用户管理表"


class MissTaskReformExecutor(models.Model):
    # <中文名，变量名>
    EXECUTOR_MAPPING = _generate_mapping(MappingEnum.EXECUTOR)

    # 2024-09-04：default="" 不是挺好的？何必要 null 呢？但是为了避免牵连到以前的内容，就也先 null 吧。
    case_baseline_executor = models.CharField(CnVar.case_baseline, max_length=300, blank=True, null=True)
    product_improver = models.CharField(CnVar.product_improve, max_length=300, blank=True, null=True)
    manage_executor = models.CharField(CnVar.manage, max_length=300, blank=True, null=True)
    code_check_executor = models.CharField(CnVar.code_check, max_length=300, blank=True, null=True)
    auto_executor = models.CharField(CnVar.auto, max_length=300, blank=True, null=True)
    open_source_governance_executor = models.CharField(CnVar.open_source_governance,
                                                       max_length=300, blank=True, null=True)
    security_architecture_executor = models.CharField(CnVar.security_architecture,
                                                      max_length=300, blank=True, null=True)

    secure_coding_executor = models.CharField(CnVar.secure_coding, max_length=300, blank=True, null=True)
    secure_baseline_executor = models.CharField(CnVar.secure_baseline, max_length=300, blank=True, null=True)
    security_tool_executor = models.CharField(CnVar.security_tool, max_length=300, blank=True, null=True)
    security_measures_executor = models.CharField(CnVar.security_measures, max_length=300, blank=True, null=True)
    compliance_policies_executor = models.CharField(CnVar.compliance_policies, max_length=300, blank=True, null=True)
    security_executor = models.CharField(CnVar.security, max_length=300, blank=True, null=True)

    class Meta:
        db_table = "t_measure_miss_task_reform_executor"
        verbose_name = verbose_name_plural = "改进措施责任人表"


class MissTaskOverallTop(models.Model):
    """ MissTaskOverall 指逆向改进总览，Top 指生产安全质量问题 TOP 因素分析表  """
    year_month = models.CharField("生产安全质量问题 TOP 因素分析约束键", max_length=7, unique=True)
    technical_root_cause = models.TextField("技术根因", blank=True, default="")
    management_root_cause = models.TextField("管理根因", blank=True, default="")
    improvement_proposal = models.TextField("改进建议", blank=True, default="")

    class Meta:
        db_table = "t_measure_miss_task_overall_top"
        verbose_name = verbose_name_plural = "生产安全质量问题 TOP 因素分析表"

    def __str__(self):
        return str(self.year_month)

    @classmethod
    def get_verbose_name(cls):
        return cls._meta.verbose_name

    @classmethod
    def get_queryset_by_limit_offset(cls, limit, offset):
        res = cls.objects.raw("select * from %s limit %s offset %s", params=[cls._meta.db_table, limit, offset])
        return res


# ----------------------------------------------------------------------------------------------------------------------
# 2024-08-21: 以前的代码放置的位置太乱了，统一移动到此处
# 任务信息表
class MissTaskModel(BaseMixin, models.Model):
    """漏测问题任务-->逆向改进管理任务表
    生产环境迁移时一个一个迁移
    :create_time: 2022.10.08
    """
    STATUS = ((1, '创建任务'), (2, '分析中'), (3, '改进中'), (4, "验收中"), (5, '关闭'))
    TASK_TYPES = namedtuple("TASK_TYPES", ["sj", "xw"])(sj="ICSL送检", xw="现网问题")

    # 责任人字段公共属性
    EXECUTOR_PUB_ATTRS = dict(max_length=300, blank=True, null=True)
    # <中文名，变量名>
    OWNER_MAPPING = _generate_mapping(MappingEnum.EXECUTOR)
    # 变量名元组，此处已经被其他地方依赖，因此没有删除
    EXECUTOR_VARIABLE_NAMES: Tuple[str] = tuple(OWNER_MAPPING.values())
    # 给创建字段是用了，这样写的目的是 TASK_TYPES 变动，TYPE 也会自动变动
    TYPE = tuple((e, e) for e in get_namedtuple_values(TASK_TYPES))

    # 下面紧挨着的这几个字段是以后会用到的，其他字段应该是用不到了，注意是应该（2024-09-06）
    task_type = models.CharField("任务类型", default="ICSL送检", max_length=300, choices=TYPE)
    creator = models.CharField("创建人", max_length=100, blank=True, null=True)
    create_time = models.DateTimeField("创建时间", auto_now_add=True)
    project = models.CharField("项目", max_length=300, blank=True, null=True)
    # ---------------------------------------------------------------------------------------------------------------- #
    # 2024-09-19：以下内容几乎用不到了！
    deadline = models.DateField("截止时间", blank=True, null=True)
    is_count = models.BooleanField("是否统计", default=True)
    product = models.CharField("产品", max_length=300, blank=True, null=True)
    subproduct = models.CharField("子产品", max_length=300, blank=True, null=True)
    service = models.CharField("应用/服务", max_length=300, blank=True, null=True)
    version = models.CharField("版本", max_length=300, blank=True, null=True)
    # 送检
    case_baseline_executor = models.CharField(_add_owner(CnVar.case_baseline), **EXECUTOR_PUB_ATTRS)
    product_improver = models.CharField(_add_owner(CnVar.product_improve), **EXECUTOR_PUB_ATTRS)
    manage_executor = models.CharField(_add_owner(CnVar.manage), **EXECUTOR_PUB_ATTRS)
    code_check_executor = models.CharField(_add_owner(CnVar.code_check), **EXECUTOR_PUB_ATTRS)
    auto_executor = models.CharField(_add_owner(CnVar.auto), **EXECUTOR_PUB_ATTRS)
    open_source_governance_executor = models.CharField(_add_owner(CnVar.open_source_governance), **EXECUTOR_PUB_ATTRS)
    security_architecture_executor = models.CharField(_add_owner(CnVar.security_architecture), **EXECUTOR_PUB_ATTRS)
    # 现网
    secure_coding_executor = models.CharField(_add_owner(CnVar.secure_coding), **EXECUTOR_PUB_ATTRS)
    secure_baseline_executor = models.CharField(_add_owner(CnVar.secure_baseline), **EXECUTOR_PUB_ATTRS)
    security_tool_executor = models.CharField(_add_owner(CnVar.security_tool), **EXECUTOR_PUB_ATTRS)
    security_measures_executor = models.CharField(_add_owner(CnVar.security_measures), **EXECUTOR_PUB_ATTRS)
    compliance_policies_executor = models.CharField(_add_owner(CnVar.compliance_policies), **EXECUTOR_PUB_ATTRS)
    security_executor = models.CharField(_add_owner(CnVar.security), **EXECUTOR_PUB_ATTRS)
    # 2024-09-04 目前好像暂未使用
    codedex_executor = models.CharField("安全编码责任人", max_length=300, blank=True, null=True)
    design_executor = models.CharField("安全设计责任人", max_length=300, blank=True, null=True)
    case_executor = models.CharField("安全测试责任人", max_length=300, blank=True, null=True)

    acceptance_owner = models.CharField("验收负责人", blank=True, max_length=300, default="叶桦 00630246")

    w3_task_uuid = models.CharField("W3待办审批任务ID", max_length=64, blank=True, null=True)
    w3_accept_task_uuid = models.CharField("W3待办验收任务ID", max_length=64, blank=True, null=True)
    status = models.IntegerField("漏测状态", choices=STATUS, blank=True, null=True)
    update_time = models.DateTimeField("修改时间", auto_now=True)
    is_old = models.BooleanField("是否新数据（2024-3之后新建皆为新数据）", default=False)

    class Meta:
        db_table = "t_measure_miss_task"
        verbose_name = "逆向改进问题任务表"

    def get_all_executor_fields_var_name(self):
        """ 获得责任人字段的变量名 """
        res = []
        for field in self._meta.fields:
            if field.verbose_name.endswith("责任人"):
                res.append(field.name)
        return res


class MissTaskFile(models.Model):
    """逆向改进文件表
    :create_time: 2022.10.09
    """
    misstask = models.ForeignKey(MissTaskModel, on_delete=models.CASCADE, blank=True, null=True,
                                 verbose_name="逆向改进任务")
    fileid = models.CharField(max_length=500, blank=True, null=True, verbose_name="Fastdfs文件ID")
    filename = models.CharField(max_length=500, blank=True, null=True, verbose_name="文件名")
    upload_time = models.DateTimeField(verbose_name=u'上传时间', auto_now_add=True)
    author = models.CharField(max_length=50, verbose_name="文件上传者", blank=True, null=True)
    is_delete = models.BooleanField(verbose_name="是否删除", help_text="1:删除，0:未删除", default=False)
    file_type = models.CharField(max_length=500, blank=True, null=True, verbose_name="附件类型")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='修改时间')

    class Meta:
        db_table = "t_measure_miss_file"
        verbose_name = "逆向改进问题文件表"
        ordering = ('-create_time',)


# 改进表
class MissTaskImprove(models.Model):
    """逆向问题改进环节
    :create_time: 2023.01.12
    """

    class AcceptanceStatusEnum(enum.Enum):
        TO_BE_ACCEPT = 0
        PASS = 1
        REJECT = 2
        OTHER = 3

        @classmethod
        def to_mapping(cls):
            return {
                cls.TO_BE_ACCEPT.value: "待验收",
                cls.PASS.value: "通过",
                cls.REJECT.value: "驳回",
                cls.OTHER.value: "/"
            }

    class CloseStatus:
        OPEN = "Open"
        CLOSE = "Close"

    IMPROVEMENT_NA = "不涉及"

    STATUS = ((CloseStatus.OPEN, "Open"), (CloseStatus.CLOSE, "Close"))
    YN = ((0, "否"), (1, "是"))
    ACCEPTANCE_STATUS = tuple(AcceptanceStatusEnum.to_mapping().items())

    # 2024-09-08：懒得吐槽了，之前的人建个表天天 blank=True, null=True 干嘛？凭什么这么多必填的内容你允许为 null？
    misstask = models.ForeignKey(MissTaskModel, on_delete=models.CASCADE, blank=True, null=True,
                                 verbose_name="外键逆向改进问题ID")
    dts_no = CustomListField(max_length=8000, verbose_name="DTS单号", blank=True, null=True)
    improvement = models.CharField(max_length=1024, blank=True, null=True, verbose_name='改进措施')
    improvement_type = models.CharField(max_length=64, blank=True, null=True, verbose_name="改进类型")
    reform_executor = models.CharField(max_length=1024, blank=True, null=True, verbose_name='改进措施责任人')
    close_progress = models.CharField(max_length=1024, blank=True, null=True, verbose_name='闭环进展')
    close_status = models.CharField(max_length=64, default="Open", choices=STATUS, verbose_name='闭环状态')
    update_by = models.CharField(max_length=64, blank=True, null=True, verbose_name='更新人')
    YN_delete = models.IntegerField(default=0, choices=YN, verbose_name='是否删除')
    close_plan_time = models.DateField(verbose_name=u'闭环计划时间', default=None, blank=True, null=True)
    final_close_datetime = models.DateTimeField(verbose_name="最后一次闭环时间", blank=True, null=True, default=None)
    w3_improve_task_uuid = models.CharField(max_length=64, verbose_name=u"W3待办审批任务ID", blank=True, null=True)
    attachment_id = models.ForeignKey(MissTaskFile, on_delete=models.CASCADE, blank=True, null=True,
                                      verbose_name="上传的附件id")
    create_time = models.DateTimeField(verbose_name=u'创建时间', auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True, verbose_name="修改时间")
    acceptance_status = models.IntegerField(choices=ACCEPTANCE_STATUS, default=3, verbose_name="验收状态")

    class Meta:
        db_table = "t_measure_miss_improve"
        verbose_name = "逆向问题改进表"

    @staticmethod
    def get_condition_of_is_timeout():
        return dict(
            close_plan_time_date=TruncDate("close_plan_time"),
            final_close_datetime_date=TruncDate("final_close_datetime"),
            is_timeout=Case(
                When(
                    close_status="Close",
                    close_plan_time_date__lt=F("final_close_datetime_date"),
                    then=Value(True),
                ),
                When(
                    close_status="Open",
                    close_plan_time_date__lt=timezone.now().date(),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField()
            )
        )

    @classmethod
    def get_queryset_by(cls, misstask_id, dts_no: str, filter_data=None, deleted=False):
        """ 【封装细节】 YN_delete 字段封装起来 """
        res = cls.objects.filter(misstask_id=misstask_id,
                                 dts_no__icontains=dts_no,
                                 YN_delete=int(deleted))
        if filter_data:
            res = res.filter(**filter_data)
        return res

    def get_misstaskdetail_obj(self, only: List[str] = None, extra_filter_data=None):
        """ 【封装细节】 根据本模型实例的 misstask_id 和 dts_no 去定位 misstaskdetail 模型实例 """
        extra_filter_data = extra_filter_data if extra_filter_data else {}
        filter_data = dict(misstask_id=self.misstask_id, dts_no__in=self.dts_no)
        filter_data.update(extra_filter_data)
        try:
            # 2024-09-13：此处可以加个 only
            if not only:
                return NewMissTaskDetail.objects.get(**filter_data)
            else:
                return NewMissTaskDetail.objects.only(*only).get(**filter_data)
        except NewMissTaskDetail.DoesNotExist as e:
            if extra_filter_data:
                return None
            raise NewMissTaskDetail.DoesNotExist(f"未查询到 "
                                                 f"misstask_id={self.misstask_id}，"
                                                 f"dts_no__in={self.dts_no} "
                                                 f"的 NewMissTaskDetail 实例") from e
        except NewMissTaskDetail.MultipleObjectsReturned:
            # 正式环境存在两个同名问题单，这是不应该的事情，后续会添加校验，但是不要用数据库的 unique 约束（2024-09-04）
            logger.error("%s", f"警告！MultipleObjectsReturned：{filter_data}")
            return NewMissTaskDetail.objects.filter(**filter_data).first()


# 验收表
class MissTaskImproveAcceptRecord(models.Model):
    """逆向问题改进验收记录
    :create_time: 2023.09.19
    """
    ACCEPTANCE_STATUS = ((0, "to_be_accepted"), (1, "pass"), (2, "reject"))
    OPERATION_TYPE = ((1, "edit_improve"), (2, "accept"))
    misstask_improve = models.ForeignKey(MissTaskImprove, on_delete=models.CASCADE, verbose_name="外键逆向改进问题ID")
    update_by = models.CharField(max_length=64, blank=True, null=True, verbose_name='更新人')
    file_id = models.CharField(max_length=500, blank=True, null=True, verbose_name="验收文件")
    file_name = models.CharField(max_length=500, blank=True, null=True, verbose_name="验收文件名称")
    conclusion = models.TextField(default="", blank=True, null=True, verbose_name="验收结论")
    create_time = models.DateTimeField(verbose_name=u'创建时间', auto_now_add=True)
    acceptance_status = models.IntegerField(choices=ACCEPTANCE_STATUS, blank=True, null=True, verbose_name="验收状态")
    operation_type = models.IntegerField(choices=OPERATION_TYPE, blank=True, null=True, verbose_name="操作类型")

    class Meta:
        db_table = "t_measure_miss_improve_accept_record"
        verbose_name = "逆向问题改进验收记录"


# 创建表
class NewMissTaskDetail(BaseMixin, models.Model):
    """逆向改进详情分析表(新)
    """

    class YNEnum(enum.Enum):
        NO = 0
        YES = 1

        @classmethod
        def to_mapping(cls):
            return {
                cls.NO.value: "否",
                cls.YES.value: "是"
            }

    class AnalyzeStatusEnum(enum.Enum):
        PENDING = 0  # 待分析
        FINISH = 1  # 分析完成

        @classmethod
        def to_mapping(cls):
            return {
                cls.PENDING.value: "/",
                cls.FINISH.value: "分析完成"
            }

    class ConfirmedStatusEnum(enum.Enum):
        UNCONFIRMED = 0  # 未确认
        CONFIRMED = 1  # 已确认
        DISPUTED_ISSUES = 2  # 争议问题

        @classmethod
        def to_mapping(cls):
            # 2024-09-11：这里有待优化，因为不好用啊，Enum 为什么我总感觉不好用呢？用 class 不就够了？
            return {
                cls.UNCONFIRMED.value: "未确认",
                cls.CONFIRMED.value: "已确认",
                cls.DISPUTED_ISSUES.value: "争议问题"
            }

    YN = tuple(YNEnum.to_mapping().items())
    ANALYZESTATUS = tuple(AnalyzeStatusEnum.to_mapping().items())
    CONFIRMED_STATUS_CHOICES = ConfirmedStatusEnum.to_mapping()

    IMPROVEMENT_BASE_MAPPING = _generate_mapping(MappingEnum.BASE)
    IMPROVEMENT_RELATED_MAPPING = _generate_mapping(MappingEnum.RELATED)

    misstask = models.ForeignKey(MissTaskModel,
                                 on_delete=models.CASCADE,
                                 blank=True, null=True,
                                 verbose_name="外键漏测问题ID")
    dts_no = models.CharField(max_length=64, blank=True, null=True, verbose_name="DTS单号")
    description = models.TextField(default="", blank=True, null=True, verbose_name="问题描述")
    yn_common = models.IntegerField(default=YNEnum.NO.value, choices=YN, verbose_name='是否共性问题')
    product = models.CharField(max_length=50, blank=True, null=True, verbose_name="产品")
    subproduct = models.CharField(max_length=50, blank=True, null=True, verbose_name="子产品")
    service = models.CharField(max_length=50, blank=True, null=True, verbose_name="应用")
    version = models.CharField(max_length=50, blank=True, null=True, verbose_name="版本")
    control_point = models.CharField(max_length=64, blank=True, null=True, verbose_name='最佳控制点')
    analyze_executor = models.CharField(max_length=128, blank=True, null=True, verbose_name='分析责任人')
    acceptance_owner = models.CharField(max_length=128, blank=True, null=True, verbose_name='验收责任人')
    reform_executor = models.CharField(max_length=500, blank=True, null=True, verbose_name='改进措施责任人')
    detail_desc = models.TextField(default="", verbose_name="详细描述", blank=True, null=True)
    dts_come = models.CharField(max_length=64, blank=True, null=True, verbose_name="问题来源")
    dts_class = models.CharField(max_length=128, blank=True, null=True, verbose_name="问题大类")
    dts_subclass = models.CharField(max_length=128, blank=True, null=True, verbose_name="问题小类")
    level = models.CharField(max_length=32, blank=True, null=True, verbose_name="问题级别")
    problem_type = models.CharField(max_length=32, blank=True, null=True, verbose_name="问题类型")
    technical_reason = models.CharField(max_length=500, blank=True, null=True, verbose_name='技术根因')
    technical_reason_related = models.BooleanField("是否涉及技术根因", default=False)
    process_manage_reason = models.CharField(max_length=500, blank=True, null=True, verbose_name='流程根因')
    process_manage_reason_related = models.BooleanField("是否涉及流程根因", default=False)
    improvement_situation = models.CharField(max_length=500, blank=True, null=True,
                                             verbose_name='共性问题排查版本及排查落地情况')

    # 2024-09-04：目前涉及的 12 个，但我有个疑问，为什么全是 blank=True, null=True？
    security_architecture = models.CharField(CnVar.security_architecture, max_length=500, blank=True, null=True)
    security_architecture_related = models.BooleanField(_add_related(CnVar.security_architecture), default=False)
    secure_coding = models.CharField(CnVar.secure_coding, max_length=500, blank=True, null=True)
    secure_coding_related = models.BooleanField(_add_related(CnVar.secure_coding), default=False)
    secure_baseline = models.CharField(CnVar.secure_baseline, max_length=500, blank=True, null=True)
    secure_baseline_related = models.BooleanField(_add_related(CnVar.secure_baseline), default=False)
    case_baseline = models.CharField(CnVar.case_baseline, max_length=500, blank=True, null=True)
    case_baseline_related = models.BooleanField(_add_related(CnVar.case_baseline), default=False)
    open_source_governance = models.CharField(CnVar.open_source_governance, max_length=500, blank=True, null=True)
    open_source_governance_related = models.BooleanField(_add_related(CnVar.open_source_governance), default=False)
    auto = models.CharField(CnVar.auto, max_length=500, blank=True, null=True)
    auto_related = models.BooleanField(_add_related(CnVar.auto), default=False)
    security_measures = models.CharField(CnVar.security_measures, max_length=500, blank=True, null=True)
    security_measures_related = models.BooleanField(_add_related(CnVar.security_measures), default=False)
    security_tool = models.CharField(CnVar.security_tool, max_length=500, blank=True, null=True)
    security_tool_related = models.BooleanField(_add_related(CnVar.security_tool), default=False)
    compliance_policies = models.CharField(CnVar.compliance_policies, max_length=500, blank=True, null=True)
    compliance_policies_related = models.BooleanField(_add_related(CnVar.compliance_policies), default=False)
    product_improve = models.CharField(CnVar.product_improve, max_length=500, blank=True, null=True)
    product_improve_related = models.BooleanField(_add_related(CnVar.product_improve), default=False)
    code_check = models.CharField(CnVar.code_check, max_length=500, blank=True, null=True)
    code_check_related = models.BooleanField(_add_related(CnVar.code_check), default=False)
    manage = models.CharField(CnVar.manage, max_length=500, blank=True, null=True)
    manage_related = models.BooleanField(_add_related(CnVar.manage), default=False)

    status = models.CharField("状态", max_length=32, blank=True, null=True)
    repeated = models.BooleanField("是否重犯")
    dts_create_time = models.CharField(max_length=500, blank=True, null=True, verbose_name="DTS创建时间")
    improvement_status = models.CharField("改进状态", max_length=64, blank=True, null=True, default="待改进")
    acceptance_status = models.CharField("验收状态", max_length=64, blank=True, null=True, default="待验收")
    analyze_status = models.IntegerField("分析状态", choices=ANALYZESTATUS, default=0)
    create_time = models.DateTimeField("创建时间", auto_now_add=True)
    update_time = models.DateTimeField("修改时间", auto_now=True)
    review_minute_file = models.OneToOneField(MissTaskFile,
                                              on_delete=models.CASCADE,
                                              blank=True, null=True,
                                              verbose_name="上传的评审纪要",
                                              related_name="review_minute_file")
    improvement_problem_file = models.OneToOneField(MissTaskFile,
                                                    on_delete=models.CASCADE,
                                                    blank=True, null=True,
                                                    verbose_name="导入的问题",
                                                    related_name="improvement_problem_file")
    confirmed_status = models.IntegerField("确认状态", choices=CONFIRMED_STATUS_CHOICES.items(), default=0)

    misstaskreformexecutor = models.OneToOneField(MissTaskReformExecutor,
                                                  on_delete=models.CASCADE,
                                                  verbose_name="改进措施责任人",
                                                  blank=True, null=True)

    class Meta:
        db_table = "t_new_measure_miss_detail"
        verbose_name = "逆向改进问题分析详情表"

    def get_misstaskimprove_queryset(self, filter_data=None, exclude_data=None):
        """ 【封装细节】 获得当前表旗下的所有改进措施 """
        res = MissTaskImprove.get_queryset_by(self.misstask_id, self.dts_no, deleted=False)
        if filter_data:
            res = res.filter(**filter_data)
        if exclude_data:
            res = res.exclude(**exclude_data)
        return res


# ----------------------------------------------------------------------------------------------------------------------
