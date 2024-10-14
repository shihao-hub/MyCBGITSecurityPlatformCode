import pydantic


class PydanticConstant:
    PYDANTIC_ERROR_MSG_TEMPLATES = {
        "value_error.missing": "缺少字段",
        "type_error.str": "需要 str 类型",
    }


class PydanticCustomBaseModel(pydantic.BaseModel):
    class Config:
        error_msg_templates = PydanticConstant.PYDANTIC_ERROR_MSG_TEMPLATES

    @staticmethod
    def errors_formatting(exception: pydantic.ValidationError):
        res = [f"{e.get('msg')}({','.join(e.get('loc'))})" for e in exception.errors()]
        return "，".join(res)
