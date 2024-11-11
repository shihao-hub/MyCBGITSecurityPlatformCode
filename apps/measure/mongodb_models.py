import logging
from typing import TypeVar, Generic, Type

import mongoengine
from mongoengine import (
    StringField, BooleanField,
    ListField, DictField,
    DateTimeField,
    DynamicDocument,
)

from django.conf import settings

from asset.models import ServicePbiEamapMapping, PBIInfo
from config import config
from utils.get_w3_account import get_cn_name as get_cn_name_of_platform
from gytask.utils.edm_api import Edm

DATABASE_NAME = "combat_platform"
mongoengine.connect(db=DATABASE_NAME, alias=DATABASE_NAME,
                    host=config.get("address", "mongodb_host"), port=int(config.get("address", "mongodb_port")))

T = TypeVar("T")
logger = logging.getLogger("mylogger")


def get_cn_name(en_name):
    # 不调用 get_cn_name 了，这会导致每次都会额外发送请求。数据同步太慢了，而且还有已经离职的很多人查不到中文名。
    return en_name


def _generate_product_subproduct_service(self: mongoengine.Document, code):
    """ 根据 code 生成 product subproduct service """
    if not code:
        return
    # 通过 code 去 RDBMS 查询 product、subproduct、service
    pbi_id = None
    try:
        inst = ServicePbiEamapMapping.objects.only("service_pbi_id").get(eamap_code=code)
        pbi_id = inst.service_pbi_id
        for name in ["service", "subproduct", "product"]:
            try:
                pbi_info_inst = PBIInfo.objects.only("pbi_id", "cn").get(pbi_id=pbi_id)
                setattr(self, name, pbi_info_inst.cn)
                pbi_id = pbi_info_inst.parent_id
            except PBIInfo.DoesNotExist as e:
                logger.error("%s", f"{e}")
    except ServicePbiEamapMapping.DoesNotExist:
        # #(C)!: logger.error("%s", f"pbi_id: {pbi_id}, code:{code}, {e}")
        pass


class BaseServiceMixin(Generic[T]):
    # metaclass conflict:
    # the metaclass of a derived class must be a (non-strict) subclass of the metaclasses of all its bases
    objects: mongoengine.QuerySet

    @classmethod
    def objects_filter(cls: Type[T], q_obj=None, **query) -> Type[T]:
        res = cls.objects(q_obj=q_obj, **query)
        return res

    @classmethod
    def objects_get(cls: Type[T], *q_objs, **query) -> T:
        res = cls.objects.get(*q_objs, **query)
        return res


class DesktopVulnerability(DynamicDocument):
    warningNo = StringField(verbose_name="漏洞告警编号", required=True, primary_key=True)
    warningName = StringField(verbose_name="漏洞告警名称", required=True)
    vulnerabilityType = StringField(verbose_name="漏洞类型", required=True)
    # #(C)!: vulnerabilitySource = StringField(verbose_name="漏洞来源类型", required=True)
    appId = StringField(verbose_name="AppId", required=True)
    rectificationOwner = StringField(verbose_name="责任人", required=True)

    # generated fields
    product = StringField(verbose_name="产品")
    subproduct = StringField(verbose_name="子产品")
    service = StringField(verbose_name="应用/服务")

    confirmTime = DateTimeField()
    closedTime = DateTimeField()
    plannedClosedTime = DateTimeField()
    lastUpdateTime = DateTimeField()

    # 非必填，StringField 可以等价于 Optional[str]
    appCode = StringField()
    appModuleName = StringField()
    subProductCode = StringField()
    subProductName = StringField()
    productCode = StringField()
    productName = StringField()
    cvss = StringField()
    cveId = StringField()
    isBounder = BooleanField()
    hwitvdId = StringField()
    hwpsirtId = StringField()
    warningPriority = StringField()
    status = StringField()
    warningSlaStatus = StringField()
    confirmSlaStatus = StringField()
    effectiveStatus = StringField()
    creator = StringField()
    warningTime = StringField()
    discoveryTime = StringField()
    vulnerabilityDescription = StringField()
    rectificationMeasures = StringField()

    meta = {
        "collection": "c_desktop_vulnerability",
        "db_alias": DATABASE_NAME
    }

    objects: mongoengine.QuerySet

    def _convert_rectification_owner(self):
        if not self.rectificationOwner:
            return
        try:
            self.rectificationOwner = get_cn_name(self.rectificationOwner)
        except Exception as e:
            logger.info("%s", f"{e}")

    def _generate_product_subproduct_service(self):
        return _generate_product_subproduct_service(self, self.appCode)

    def clean(self):
        self._generate_product_subproduct_service()


class VulnerabilityTrackingTask(DynamicDocument):
    tracingTaskId = StringField(verbose_name="跟踪任务编号", required=True, primary_key=True)
    vulnerabilityId = StringField(verbose_name="漏洞编号", required=True)
    tracingTaskName = StringField(verbose_name="任务名称", required=True)  # 注意，这个任务名称就是问题描述！
    vulnerabilityDescription = StringField(verbose_name="描述", required=True)
    vulnerabilityCategory = StringField(verbose_name="漏洞类别", required=True)
    productCode = StringField(verbose_name="产品/子产品/应用", required=True)

    handler = StringField(verbose_name="处理人/团队")
    discoverer = StringField(verbose_name="发现人/团队")
    approver = StringField(verbose_name="approver")

    # 结构类似 [{},{}]，其中字典为 {"docId":"","name":""}
    analysisAttachments = ListField(verbose_name="分析报告")
    responseSolutionsAttachments = ListField(verbose_name="处理报告")

    handlingLevel = StringField(verbose_name="处理级别", required=True)
    # generated fields
    product = StringField(verbose_name="产品")
    subproduct = StringField(verbose_name="子产品")
    service = StringField(verbose_name="应用/服务")

    vulnerabilitySeverity = StringField(verbose_name="严重级别")
    cvss = StringField(verbose_name="CVSS 评分")
    rootCause = StringField(verbose_name="根因分析")
    solution = StringField(verbose_name="响应措施")

    # 不要用 DateTimeField，就先用字符串即可！ 但是为什么改了没用。mongodb 服务器需要重启吗？无语。
    vulnerabilityCreateTime = DateTimeField(verbose_name="漏洞创建时间")
    vulnerabilityLastUpdatedTime = DateTimeField(verbose_name="漏洞最近更新时间")
    discoveryTime = DateTimeField(verbose_name="漏洞发现时间")
    preWarningTime = DateTimeField(verbose_name="漏洞预警时间")

    meta = {
        "collection": "c_vulnerability_tracking_task",
        "db_alias": DATABASE_NAME,
        # #(C)!: "indexes": ["tracingTaskId"]
    }

    objects: mongoengine.QuerySet

    def _convert_analysis_and_response_solutions_attachments(self):
        def _convert(field_name):
            try:
                attachments = getattr(self, field_name)
                if not attachments:
                    return
                res = []
                for d in attachments:
                    appid = settings.APPID
                    url = Edm().get_download_url(settings.env).format(project_id=appid, doc_id=d.get("docId"))
                    res.append(f'<a href="{url}">{d.get("name")}</a>')
                setattr(self, field_name, "\n".join(res))
            except Exception as e:
                # 2024-10-18：由于目前没有数据测试，因此 try except 保证不出错比较重要
                logger.error("%s", f"{e}")

        _convert("analysisAttachments")
        _convert("responseSolutionsAttachments")

    def _convert_name_of_person(self):
        for field in ["handler", "discoverer", "approver"]:
            if hasattr(self, field):
                try:
                    value = getattr(self, field)
                    setattr(self, field, get_cn_name(value))
                except Exception as e:
                    logger.error("%s", f"{e} -> self.{field}: {getattr(self, field)}")

    def _convert_vulnerability_category(self):
        if not self.vulnerabilityCategory:
            return
        self.vulnerabilityCategory = {
            "SEC_VULN_MODEL": "漏洞类",
            "SEC_DATA_MODEL": "数据类",
            "SEC_COMPLIANCE_MODEL": "合规类",
        }.get(self.vulnerabilityCategory)

    def _convert_vulnerability_severity(self):
        """ 严重级别转换 """
        if not self.vulnerabilitySeverity:
            return
        self.vulnerabilitySeverity = {
            "LOW": "一般",
            "MEDIUM": "重要",
            "HIGH": "严重",
            "URGENT": "致命",
        }.get(self.vulnerabilitySeverity)

    def _generate_product_subproduct_service(self):
        return _generate_product_subproduct_service(self, self.productCode)

    def clean(self):
        self._convert_name_of_person()

        self._generate_product_subproduct_service()

        self._convert_vulnerability_severity()
        self._convert_vulnerability_category()

        self._convert_analysis_and_response_solutions_attachments()
