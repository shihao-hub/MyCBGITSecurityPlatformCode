#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gytask.models import GYTaskResult, GYApproveRecord
from task.models import RLTask
from utils.filter_helper import BaseFilter, FilterModel
from utils.common import TimeHelper


class DesignBaseLineListControl(BaseFilter):
    id = FilterModel(field_name="id", lookup_expr="exact")
    product = FilterModel(field_name="product", lookup_expr="exact")
    subproduct = FilterModel(field_name="subproduct", lookup_expr="exact")
    service = FilterModel(field_name="service", lookup_expr="exact")
    version = FilterModel(field_name="version", lookup_expr="exact")
    create_user = FilterModel(field_name="create_user", lookup_expr="icontains")
    time_range = FilterModel(field_name="create_time", lookup_expr="range", method="filter_time")

    class Meta:
        model = RLTask
        ordering = ("-id",)


class GYTaskRejectListControl(BaseFilter):
    task_id = FilterModel(field_name="task_id", lookup_expr="exact")
    is_maturity = FilterModel(field_name="is_maturity", lookup_expr="exact")
    reject_type = FilterModel(field_name="reject_type", lookup_expr="exact")
    product = FilterModel(field_name="task__product", lookup_expr="exact")
    subproduct = FilterModel(field_name="task__subproduct", lookup_expr="exact")
    service = FilterModel(field_name="task__service", lookup_expr="exact")
    version = FilterModel(field_name="task__version", lookup_expr="exact")
    product_executor = FilterModel(field_name="task__create_user", lookup_expr="icontains")

    class Meta:
        model = GYTaskResult
        ordering = ("-create_time",)


class EFlowRejectListControl(BaseFilter):
    product = FilterModel(field_name="eflow__product", lookup_expr="exact")
    subproduct = FilterModel(field_name="eflow__subproduct", lookup_expr="exact")
    service = FilterModel(field_name="eflow__service", lookup_expr="exact")
    version = FilterModel(field_name="eflow__version", lookup_expr="exact")
    product_executor = FilterModel(field_name="eflow__creator", lookup_expr="icontains")
    reject_type = FilterModel(field_name="reject_type", lookup_expr="exact")
    eflow_id = FilterModel(field_name="eflow_id", lookup_expr="exact")

    class Meta:
        model = GYApproveRecord
        ordering = ("-create_time",)
