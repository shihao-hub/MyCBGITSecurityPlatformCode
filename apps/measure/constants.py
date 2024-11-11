# 2024-09-19：此处虽然可能存在冗余数据存储，但是应该懂得取舍，显然冗余存储相对更好理解，也方便一点
_ONE_SJ_XW_COMMON_HEADER = [
    ("问题单号", "dts_no"), ("问题描述", "description"), ("问题时间", "dts_create_time"),
    ("级别", "level"), ("类型", "problem_type"), ("问题来源", "dts_come"),
    ("版本", "version"), ("应用", "service"), ("部门", "product"),
    ("问题发生环节\n（最佳控制点）", "control_point"),

    ("问题根因分析", ""),  # 空字符串代表不需要，None 代表整个都没意义？
    ("", None),
    ("改进措施/修改方案", ""),
]

_ONE_SJ_XW_COMMON_FOOTER = [
    ("是否共性问题", "yn_common"), ("共性问题排查版本及排查落地情况", "improvement_situation"),
    ("问题重犯", "repeated"), ("确认状态", "confirmed_status"),
    ("分析责任人", "analyze_executor"), ("验收负责人", "acceptance_owner"),
    ("分析状态", "analyze_status"),
    ("改进状态", "improvement_status"),
    ("验收状态", "acceptance_status"),
]

_TWO_SJ_XW_COMMON_HEADER = [
    ("", None), ("", None), ("", None), ("", None), ("", None),
    ("", None), ("", None), ("", None), ("", None), ("", None),

    ("技术根因", "technical_reason"),
    ("流程/管理根因", "process_manage_reason"),
]

_TWO_SJ_XW_COMMON_FOOTER = [
    ("", None), ("", None),
    ("", None), ("", None),
    ("", None), ("", None),
    ("", None), ("", None),
    ("", None),
]

SJ_ONE_MAPPING = [
    *_ONE_SJ_XW_COMMON_HEADER,

    ("", None), ("", None), ("", None), ("", None), ("", None), ("", None),

    *_ONE_SJ_XW_COMMON_FOOTER
]

SJ_IMPROVEMENT_MEASURES = [
    ("安全架构&方案刷新\n（责任人：韩斌）", "security_architecture"),
    ("安全编码治理策略刷新\n（责任人：刘亚非）", "secure_coding"),
    ("开源治理规则改进\n（责任人：韩斌）", "open_source_governance"),
    ("特性/用例基线刷新\n（责任人：黄龙章）", "case_baseline"),
    ("自动化/工具/平台改进\n（责任人：陆伟/吕鹏）", "auto"),
    ("管理&流程改进\n（责任人：范冬）", "manage"),
    ("产品改进", "product_improve"),
]

SJ_TWO_MAPPING = [
    *_TWO_SJ_XW_COMMON_HEADER,
    *SJ_IMPROVEMENT_MEASURES,
    *_TWO_SJ_XW_COMMON_FOOTER,
]

XW_ONE_MAPPING = [
    *_ONE_SJ_XW_COMMON_HEADER,

    ("", None), ("", None), ("", None), ("", None), ("", None), ("", None), ("", None), ("", None),

    *_ONE_SJ_XW_COMMON_FOOTER,
]

XW_IMPROVEMENT_MEASURES = [
    ("安全架构&方案刷新\n（责任人：韩斌）", "security_architecture"),
    ("安全编码治理策略刷新\n（责任人：刘亚非）", "secure_coding"),
    ("开源治理规则改进\n（责任人：韩斌）", "open_source_governance"),
    ("特性/用例基线刷新\n（责任人：黄龙章）", "case_baseline"),
    ("自动化/工具/平台改进\n（责任人：陆伟/吕鹏）", "auto"),
    ("管理&流程改进\n（责任人：范冬）", "manage"),
    ("安防策略或措施改进\n（责任人：陈伦伟）", "security_measures"),
    ("合规策略&用例刷新\n（责任人：叶桦）", "compliance_policies"),
    ("产品改进", "product_improve"),
]

XW_TWO_MAPPING = [
    *_TWO_SJ_XW_COMMON_HEADER,
    *XW_IMPROVEMENT_MEASURES,
    *_TWO_SJ_XW_COMMON_FOOTER,
]

SJ_TEMPLATE_FILE_NAME = "产品ICSL送检缺陷流出与逆向改进分析V2.0.xlsx"
XW_TEMPLATE_FILE_NAME = "终端BG IT现网安全问题管理与回溯分析V2.0.xlsx"

SJ_HEADER_OF_FIRST_LINE = [e[0] for e in SJ_ONE_MAPPING]
SJ_HEADER_OF_SECOND_LINE = [e[0] for e in SJ_TWO_MAPPING]
XW_HEADER_OF_FIRST_LINE = [e[0] for e in XW_ONE_MAPPING]
XW_HEADER_OF_SECOND_LINE = [e[0] for e in XW_TWO_MAPPING]

SJ_EXCEL_SHEET_NAME = "隐私安全问题"
XW_EXCEL_SHEET_NAME = SJ_EXCEL_SHEET_NAME

SJ_EXCEL_DATA_VALIDATION_FORMULA_OF_LEVEL = '"致命,严重,一般,提示"'
SJ_EXCEL_DATA_VALIDATION_FORMULA_OF_PROBLEM_TYPE = '"红线A1,红线A2,红线B类,TOPN类,隐私基线,合规基线,其他问题"'
SJ_EXCEL_DATA_VALIDATION_FORMULA_OF_DTS_COME = '"IT ICSL送检,ICSL送检"'
SJ_EXCEL_DATA_VALIDATION_FORMULA_OF_CONTROL_POINT = '"需求分析,架构&设计,产品开发,安全编码,开源治理,安全测试"'

XW_EXCEL_DATA_VALIDATION_FORMULA_OF_LEVEL = '"致命,严重,一般,提示"'
XW_EXCEL_DATA_VALIDATION_FORMULA_OF_PROBLEM_TYPE = '"数据类,漏洞类,合规类"'
XW_EXCEL_DATA_VALIDATION_FORMULA_OF_DTS_COME = '"IT ICSL送检,ICSL送检"'
XW_EXCEL_DATA_VALIDATION_FORMULA_OF_CONTROL_POINT = ('"需求分析,架构&设计,产品开发,安全编码,'
                                                     '开源治理,安全测试,安全配置,防护&运营,合规治理,其他"')

COMMON_LIST_BOX_ERROR_INFORMATION = {
    "error": "Your entry is not in the list",
    "errorTitle": "Invalid Entry",
    "prompt": "Please select from the list",
    "promptTitle": "List Selection",
}

new_miss_task_detail_serializer_context = {
    "use_first_table_fields": [
        "acceptance_owner", "auto_executor", "case_baseline_executor",
        "code_check_executor", "manage_executor", "open_source_governance_executor",
        "product_improver", "security_architecture_executor",

        "secure_coding_executor", "secure_baseline_executor", "security_tool_executor",
        "security_measures_executor", "compliance_policies_executor",

        "deadline", "is_count",
        "creator", "project",
        "task_type"
    ]
}
