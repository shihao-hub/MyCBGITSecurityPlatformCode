import pydantic
from pydantic import BaseModel, Field

from measure.pydantic_models.utils import PydanticCustomBaseModel


class DistributeTestManagerValidator(PydanticCustomBaseModel):
    id: int = Field(title="ident")
    test_manager: str = Field(title="测试项目经理", description="必填字符串", example="")


class SubmitAnalysisResultValidator(PydanticCustomBaseModel):
    class Constant:
        required_fields = (
            "level", "problem_type", "dts_come",  # 问题级别、问题类型、问题来源
            "product", "subproduct", "service", "version",  # 产品、子产品、应用/服务、版本
            "control_point", "analyze_executor",  # 最佳控制点、测试项目经理
            "repeated", "yn_common",  # 是否问题重犯、共性问题
        )

        optional_fields = (
            "dts_create_time", "improvement_situation",  # 问题时间、共性问题排查版本及排查落地情况
        )


class CreateMissTaskDetailInstanceValidator(PydanticCustomBaseModel):
    pass
