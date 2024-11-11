class MissTaskOverallViewSet(ModelViewSet):
    """ 逆向改进总览
        生产安全质量问题：production_safety_and_quality_problems ->
        安全质量问题：safety_and_quality_problems
    """
    # const ---------------------------------------------------------------------------------------------------------- #
    common_const = collections.namedtuple("common_const", [
        "improvement_n_a",
        "close_status",
        "open_status",
        "manage_verbose_name",
    ])(**dict(
        improvement_n_a="不涉及",
        close_status="Close",
        open_status="Open",
        manage_verbose_name="管理 & 流程"
    ))

    # ---------------------------------------------------------------------------------------------------------------- #

    def __const_for_gtd(self):
        # codecheck 要求函数的行数不能过长，因此将其抽出来
        this = self
        return collections.namedtuple("const", [
            "cache_key_misstask_prefix",
            "cache_key_misstaskdetail_prefix",
            "misstaskdetail_needed_keys",
            "expire_time",
        ])(**dict(
            cache_key_misstask_prefix="_generate_table_data:tmp:misstask:",
            cache_key_misstaskdetail_prefix="_generate_table_data:tmp:misstaskdetail:",
            misstaskdetail_needed_keys=(
                "analyze_status", "improvement_status",
                "acceptance_status", "dts_come",
                "dts_no",
                "level",
                "yn_common",
                "control_point",
                "dts_no",
                "description",
                "id"
            ),
            expire_time=2,
        ))

    def __get_cached_value_for_gtd(self, cache_key, model_inst, const):
        this = self
        res = None  # cache.get(cache_key) -> 需要解决这个缓存数据异常的问题，好奇怪...
        if not res:
            res = django_serialize(model_inst)
            cache.set(cache_key, res, const.expire_time)
        return res

    @staticmethod
    def __compare_for_gtd(o1, o2):
        if o1.get("is_timeout") and o2.get("is_timeout"):
            o1_timeout_days = o1.get("timeout_days") if o1.get("timeout_days") else 0
            o2_timeout_days = o2.get("timeout_days") if o2.get("timeout_days") else 0
            return o2_timeout_days - o1_timeout_days
        return -1 if o1.get("is_timeout") else 1

    def __get_item_for_gtd(self, model_objs, model_jsons, extra_data, const) -> t.Dict[str, t.Any]:
        this = self
        res = {}

        # 这里需要优化，怎么可以这样写呢...但是从这里体会到了 classmethod 和 staticmethod 的作用了！
        tmp_mtd_serializer = NewMissTaskDetailserializer([])

        misstask_obj = model_objs.misstask_obj
        misstaskdetail_obj = model_objs.misstaskdetail_obj

        misstaskimprove = model_jsons.misstaskimprove
        misstaskdetail = model_jsons.misstaskdetail

        is_timeout = extra_data.is_timeout
        timeout_days = extra_data.timeout_days

        res.update({
            "is_timeout": is_timeout,
            "timeout_days": timeout_days if is_timeout else timeout_days,
            "improve_count": NewMissTaskDetailserializer.get_improve_count(tmp_mtd_serializer, misstaskdetail_obj),
            "improve_total_count": (NewMissTaskDetailserializer
                                    .get_improve_total_count(tmp_mtd_serializer, misstaskdetail_obj)),
            "accept_count": NewMissTaskDetailserializer.get_accept_count(tmp_mtd_serializer, misstaskdetail_obj),
            "accept_total_count": (NewMissTaskDetailserializer
                                   .get_accept_total_count(tmp_mtd_serializer, misstaskdetail_obj)),
            "task_type": misstask_obj.task_type
        })
        res.update({
            "improvement_type": misstaskimprove.get("improvement_type"),
            "reform_executor": misstaskimprove.get("reform_executor"),
        })
        res.update({
            e: misstaskdetail.get(e)
            for e in const.misstaskdetail_needed_keys
        })
        return res

    def _generate_table_data(self, open_status_misstaskimprove_qs, slice_query_set=None, limit=None, page=None):
        # 请注意，不确定 drf 如何生成的，但是肯定要用到生成器，不然一口气这么多数据在内存中，是不是有点不合理
        if slice_query_set is None:
            slice_query_set = open_status_misstaskimprove_qs

        # literal-const
        const = self.__const_for_gtd()

        res = []
        # vue_key：前端显示表格需要一个唯一值，而当前这个需求并不存在唯一值，需要手动添加一个
        if limit and page:
            vue_key = (page - 1) * limit
        else:
            vue_key = 0
        for inst in slice_query_set:
            # dynamic-const
            # 2024-09-27：此处使用的是 django_serialize 而不是 drf
            misstaskimprove = django_serialize(inst)

            misstaskimprove_pk = misstaskimprove.get("id")
            misstask_id = misstaskimprove.get("misstask")
            dts_no = ast.literal_eval(misstaskimprove.get("dts_no"))[0]

            try:
                # 此处应该不再会出现问题了，但是暂且如此吧
                misstaskdetail_obj = NewMissTaskDetail.objects.get(misstask_id=misstask_id, dts_no=dts_no)
            except NewMissTaskDetail.DoesNotExist:
                logger.error("%s", f"misstask_id={misstask_id}, dts_no={dts_no} 的 NewMissTaskDetail 未查询到")
                continue

            timeout_days = None  # 设置一个不在预期内的值
            is_timeout = (open_status_misstaskimprove_qs
                          .filter(pk=misstaskimprove_pk)
                          .annotate(**MissTaskImprove.get_condition_of_is_timeout())
                          .values_list("is_timeout", flat=True)
                          .first())  # (N)!: 这个太妙了，这个 first() 返回值就是个元组

            # 第二次查询，这样省事... 但是显然发送一次请求就查到结果是最合理的！！而且数据处理能在数据库中就处理完更好
            if is_timeout:
                # 暂且如此，取出来自己用 Python 计算差值，数据库内部暂且不知道怎么处理的
                close_plan_time = (open_status_misstaskimprove_qs
                                   .filter(pk=misstaskimprove_pk)
                                   .values_list("close_plan_time", flat=True)
                                   .first())
                timeout_days = time_difference(timezone.now().date(), close_plan_time).days

            # 2024-08-30：这样抽取意义不大啊，就是单纯将代码提出去。能不能用面向对象思维呢？
            misstask_obj = MissTaskModel.objects.get(pk=misstask_id)
            cache_misstaskdetail = const.cache_key_misstaskdetail_prefix + f"{misstask_id}"
            misstaskdetail = self.__get_cached_value_for_gtd(cache_misstaskdetail, misstaskdetail_obj, const)
            item = self.__get_item_for_gtd(SimpleNamespace(
                misstask_obj=misstask_obj,
                misstaskdetail_obj=misstaskdetail_obj
            ), SimpleNamespace(
                misstaskdetail=misstaskdetail,
                misstaskimprove=misstaskimprove,
            ), SimpleNamespace(
                is_timeout=is_timeout,
                timeout_days=timeout_days
            ), const)
            item["vue_key"] = vue_key
            vue_key += 1
            res.append(item)

        # 在应用层排个序：这里的排序是根据超期时间排序的
        res.sort(key=functools.cmp_to_key(self.__compare_for_gtd))
        return res

    def _sum_fan_diagram_data(self, dict_list):
        this = self
        res = {}
        for dic in dict_list:
            for k, v in dic.items():
                res.setdefault(k, 0)
                res[k] += v
        return res

    def _get_sj_and_xw_from_total_qs(self, total_qs):
        this = self
        sj_qs = total_qs.filter(misstask__task_type=MissTaskModel.TASK_TYPES.sj)
        xw_qs = total_qs.filter(misstask__task_type=MissTaskModel.TASK_TYPES.xw)
        return sj_qs, xw_qs

    def _get_fan_diagram_data_item(self, query_set, field_name, fn=lambda x: x):
        this = self
        # 注意这个 query_set，有个地方调用传进来的是 RelatedManager，对它不能调用 len
        # 2024-08-30：测试环境通过这种方式计算出了 null，咋正式环境没有成功？
        count_all = query_set.count()
        # sql 语句：SELECT field_name, Count(field_name) AS field_name__count FROM t ORDER BY field_name
        res = (query_set
               .values(f"{field_name}")
               .annotate(Count(f"{field_name}"))
               .order_by(f"{field_name}")
               .values_list(f"{field_name}", f"{field_name}__count"))

        # #(C)!: query_set.annotate(abc=a).values(a,b) -> [{a=1,b=2},{a=1,b=2}] select aaa as a
        # #(C)!: query_set.annotate().values_list(a,b) -> [(1,2),(3,4)]

        logger.info("%s", f"{res.query}")

        res = fn(dict(res))

        # 这里注释的代码先留着，当初因为在正式环境加了之后不起作用，结果今天又突然起作用了？（2024-09-02）奇怪了...啊？
        none_val = res.pop(None, None)
        empty_string = res.pop("", None)
        if none_val or empty_string:
            # #(C)!: res["NULL"] = count_all - sum([e for e in res.values()])
            pass

        # 2024-08-30：这个试了一下也能得到结果，上面不知道为什么，待会这里去正式环境测一下吧
        null_count = query_set.filter(**{f"{field_name}__isnull": True}).count()
        if null_count:
            res["NULL"] = null_count
        if empty_string:
            res.setdefault("NULL", 0)
            res["NULL"] += empty_string  # ""

        return res

    # protected ------------------------------------------------------------------------------------------------------ #

    def _count_production_safety_and_quality_problems(self, validated_request_data):
        """ 统计生产安全质量问题所需数据 """
        # static-const
        const = {
            "data_category": "数据类",
            "compliance_category": "合规类",
        }
        # mut
        data = validated_request_data

        # (N)!: 此处筛选之 ExtractYear、ExtractMonth 函数需要总结
        query_set = NewMissTaskDetail.objects.annotate(**dict(
            as_create_time_year=ExtractYear("create_time"),
            as_create_time_mouth=ExtractMonth("create_time"),
        )).filter(**dict(
            as_create_time_year=data.get("year"),
            as_create_time_mouth=data.get("month"),
        ))
        logger.info("%s", f"根据时间筛选出来的问题单有：{len(query_set)} 个")
        sj_qs, xw_qs = self._get_sj_and_xw_from_total_qs(query_set)

        # 注意，此处查了这么多次，应该是可以减少查询次数的？
        #   大范围缩小为小范围，然后在小范围中筛除数据？
        res = {
            "total": len(query_set),
            "sj": len(sj_qs),
            "xw": len(xw_qs),
            "xw_data_category": len(xw_qs.filter(problem_type=const.get("data_category"))),
            "xw_compliance_category": len(xw_qs.filter(problem_type=const.get("compliance_category"))),
            "fan_diagram_data": {
                # 缺陷最佳控制点、产品分布、问题类型
                "control_point_data": self._get_fan_diagram_data_item(query_set, "control_point"),
                "product_data": self._get_fan_diagram_data_item(query_set, "product"),
                "problem_type_data": self._get_fan_diagram_data_item(query_set, "problem_type"),
            }
        }
        return res

    def _count_safety_and_quality_problems(self, validated_request_data):
        """ 统计安全质量问题所需数据 """
        data = validated_request_data
        query_set = NewMissTaskDetail.objects.annotate(**dict(
            as_create_time_year=ExtractYear("create_time"),
            as_create_time_mouth=ExtractMonth("create_time"),
        )).filter(**dict(
            as_create_time_year=data.get("year"),
            as_create_time_mouth__lte=data.get("month"),
        ))
        sj_qs, xw_qs = self._get_sj_and_xw_from_total_qs(query_set)
        res = {
            "total": len(query_set),
            "sj": len(sj_qs),
            "xw": len(xw_qs),
            "fan_diagram_data": {
                # 缺陷最佳控制点、产品分布、问题类型
                "control_point_data": self._get_fan_diagram_data_item(query_set, "control_point"),
                "product_data": self._get_fan_diagram_data_item(query_set, "product"),
                "problem_type_data": self._get_fan_diagram_data_item(query_set, "problem_type"),
            }
        }
        return res

    def _get_safety_and_quality_problems_improvements_query_set(self, data):
        """ 返回安全和质量问题下面的改进措施的 queryset """

        # 2024-10-08：新增需求，未闭环问题列表变成闭环计划为 X 月的问题，未填写闭环计划的忽略。
        return MissTaskImprove.objects.annotate(**dict(
            # #(OLD)!: as_create_time_year=ExtractYear("create_time"),
            # #(OLD)!: as_create_time_mouth=ExtractMonth("create_time"),
            as_close_plan_time_year=ExtractYear("close_plan_time"),
            as_close_plan_time_mouth=ExtractMonth("close_plan_time"),
        )).filter(**dict(
            # #(OLD)!: as_create_time_year=data.get("year"),
            # #(OLD)!: as_create_time_mouth__lte=data.get("month"),
            as_close_plan_time_year=data.get("year"),
            as_close_plan_time_mouth=data.get("month"),
            YN_delete=0,
        )).exclude(**dict(
            improvement=self.common_const.improvement_n_a
        ))

    def _get_safety_and_quality_problems_improvements_query_set2(self, data):
        """ 返回安全和质量问题下面的改进措施的 queryset """
        # 此处给 `2024年截止10月，针对生产安全质量问题共梳理X个改进措施...` 这一行的数据使用的！

        # 2024-10-14：由于之前的 _get_safety_and_quality_problems_improvements_query_set 被两个地方使用
        #             而又因为 10-08 的新需求导致这两个地方的数据筛选条件发生变化，所以创建一个 2 函数
        return MissTaskImprove.objects.annotate(**dict(
            as_create_time_year=ExtractYear("create_time"),
            as_create_time_mouth=ExtractMonth("create_time"),
        )).filter(**dict(
            as_create_time_year=data.get("year"),
            as_create_time_mouth__lte=data.get("month"),
            YN_delete=0,
        )).exclude(**dict(
            improvement=self.common_const.improvement_n_a
        ))

    def _count_safety_and_quality_problems_improvements(self, validated_request_data):
        """ 统计安全质量问题下面的改进措施所需数据 """
        this = self
        # literal-const
        const = self.common_const
        # dynamic-const
        data = validated_request_data

        query_set = self._get_safety_and_quality_problems_improvements_query_set2(data)

        total = len(query_set)
        technical_improvements = len(query_set.exclude(improvement_type=const.manage_verbose_name))
        closed = len(query_set.filter(close_status=const.close_status))

        # 处理 Bug：上面的逻辑查的是 improve 对应的 detail 的数据，improve 与 detail 是多对一的关系，肯定结果不对呀
        # 2024-09-12：优化了一下，速度从 1.4s 降到 0.6s，还能优化，但是目前还不知道分析方法论，看样子得多找 django 的文档看
        control_point_data = {}
        product_data = {}
        filter_data_list = [e for e in query_set.values("misstask_id", "dts_no")]
        for d in filter_data_list:
            d["dts_no__in"] = d.pop("dts_no")
            misstaskdetail_obj = NewMissTaskDetail.objects.only("control_point", "product").get(**d)

            control_point = misstaskdetail_obj.control_point
            control_point_data.setdefault(control_point, 0)
            control_point_data[control_point] += 1

            product = misstaskdetail_obj.product
            product_data.setdefault(product, 0)
            product_data[product] += 1

        none_val = product_data.pop(None, None)
        empty_string_val = product_data.pop("", None)
        if none_val or empty_string_val:
            product_data["NULL"] = sum([none_val if none_val else 0, empty_string_val if empty_string_val else 0])

        res = {
            "total": total,
            "technical_improvements": technical_improvements,
            "non_technical_improvements": total - technical_improvements,
            "closed": closed,
            "closed_rate": round(closed / total, 4) if total else 0,
            "fan_diagram_data": {
                # 缺陷最佳控制点、产品分布
                # 2024-08-26：此处可以抽成函数，除此以外，有没有什么进一步优化的可能？比如 misstask__newmisstaskdetail_set
                "control_point_data": control_point_data,
                "product_data": product_data
            },
            "table_data": None,
            "total_table_data": None
        }
        return res

    def _get_validation_expression_of_year_month(self):
        this = self
        return And(
            Use(str, error="参数 year_month 必须可以被转为 str 类型"),
            Regex(re.compile(r"^\d{4}-\d{2}$").pattern, error="参数结构必须形如 2024-08 ")
        )

    # ---------------------------------------------------------------------------------------------------------------- #

    def _get_misstaskoveralltop_item_res(self, simulated_request):
        params = {k: v for k, v in simulated_request.query_params.items()}
        schema_obj = Schema({
            "year_month": self._get_validation_expression_of_year_month()
        })
        data = schema_obj.validate(params)
        try:
            inst = MissTaskOverallTop.objects.get(year_month=data.get("year_month"))
        except MissTaskOverallTop.DoesNotExist:
            # (Q)!: 如果不存在怎么处理？
            return {}
        return json.loads(serialize("json", [inst]))[0].get("fields")

    @audit_to_local
    def get_misstaskoveralltop_item(self, request: Request):
        """ 根据 year_month 得到对应的行 """
        this = self
        try:
            # request.query_params 的值居然是个列表？有何目的啊？
            res = self._get_misstaskoveralltop_item_res(SimpleNamespace(query_params=request.query_params))
            # 这个感觉不是太需要啊？噢，不对，Response 是 drf 的类，所以可以很方便的序列化
            return JsonResponse({
                "code": 1000,
                "msg": "查询成功",
                "data": res
            }, safe=False, json_dumps_params=dict(ensure_ascii=False))
        except SchemaError as e:
            return global_error_response(msg=f"查询`{MissTaskOverallTop._meta.verbose_name}`数据失败：{e}")
        except Exception as e:
            return ns_utils.unexpected_error_occurred(e, f"查询`{MissTaskOverallTop._meta.verbose_name}`数据失败")

    @audit_to_local
    def create_or_update_misstaskoveralltop_item(self, request: Request):
        """ 创建或者更新记录行 """
        this = self
        try:
            schema_obj = Schema({
                "year_month": self._get_validation_expression_of_year_month(),
                Optional("technical_root_cause"): Use(str, error="参数 technical_root_cause 必须可以被转为 str 类型"),
                Optional("management_root_cause"): Use(str, error="参数 management_root_cause 必须可以被转为 str 类型"),
                Optional("improvement_proposal"): Use(str, error="参数 improvement_proposal 必须可以被转为 str 类型"),
            })
            clean_data = schema_obj.validate(request.data)  # (N)!: clean_data

            # 2024-08-23：此处整体可以改为 update_or_create，但是我正在练习 form 和 django json
            if MissTaskOverallTop.objects.filter(year_month=clean_data.get("year_month")).exists():
                MissTaskOverallTop.objects.filter(year_month=clean_data.get("year_month")).update(**clean_data)
                return global_success_response(msg="更新记录成功")

            # 注意，form 会帮我校验的呀，Schema 应该不需要了。（实践发现，schema 更好用）
            #   但是 form 还会检查是否有任何必填字段为空，所以二者可以合作使用。而且 form.save() 很省事。
            form = MissTaskOverallTopForm(clean_data)
            if not form.is_valid():
                error_msg = form.errors
                # 传 msg=error_msg 比较好
                return global_error_response(msg=f"创建记录失败，原因：{error_msg}")
            form.save()
            return global_success_response(msg="创建记录成功")
        except SchemaError as e:
            return global_error_response(msg=f"创建或更新记录失败，原因：{e}")
        except IntegrityError as e:
            return global_error_response(msg=f"创建或更新记录失败，原因：{e}")
        except Exception as e:
            return ns_utils.unexpected_error_occurred(e, "创建或更新记录失败")

    def __validate_params_for_gos(self, params) -> dict:
        this = self
        schema_obj = Schema({
            "year": And(Use(int), error="参数 year 必须可以被转为 int 类型"),
            "month": And(Use(int), error="参数 month 必须可以被转为 int 类型"),
            Optional("limit"): Use(int, error="参数 limit 必须可以被转为 int 类型"),
            Optional("page"): Use(int, error="参数 page 必须可以被转为 int 类型"),
        })
        return schema_obj.validate(params)

    def _get_overall_situation_res(self, simulated_request):
        params = {k: v for k, v in simulated_request.query_params.items()}
        data = self.__validate_params_for_gos(params)
        res = {
            "count_psaqp": self._count_production_safety_and_quality_problems(data),
            "count_saqp": self._count_safety_and_quality_problems(data),
            "count_psaqp_improvements": self._count_safety_and_quality_problems_improvements(data),
        }
        return res

    @audit_to_local
    def get_overall_situation(self, request: Request):
        """ 查询总体情况 """
        # 2024-08-27：响应时间为 0.5-0.75 s，有点慢了，需要优化。
        try:
            res = self._get_overall_situation_res(SimpleNamespace(query_params=request.query_params))
            return global_success_response(data=res)
        except SchemaError as e:
            logger.error("%s", f"{e}\n{traceback.format_exc()}")
            return global_error_response(msg=f"查询总体情况发生错误，原因：{e}")
        except Exception as e:
            return ns_utils.unexpected_error_occurred(e, "查询总体情况发生错误")

    def _get_overall_situation_table_data_res(self, simulated_request):
        params = {k: v for k, v in simulated_request.query_params.items()}
        data = self.__validate_params_for_gos(params)
        query_set = self._get_safety_and_quality_problems_improvements_query_set(data)
        query_set = query_set.filter(close_status=self.common_const.open_status)

        # 2024-10-30：出现 bug，增加分页功能之后，查询之前应该根据是否超期排个序
        query_set = query_set.annotate(**MissTaskImprove.get_condition_of_is_timeout()).order_by("-is_timeout")

        # 2024-08-28：新增分页功能
        slice_query_set = None
        limit, page = data.get("limit"), data.get("page")
        if limit and page:
            start = (page - 1) * limit
            end = start + limit
            slice_query_set = query_set[start:end]
        res = {
            "table_data": self._generate_table_data(query_set, slice_query_set=slice_query_set, limit=limit, page=page),
            "total": len(query_set)  # 这不又查了一次吗？
        }
        res["total_table_data"] = len(res.get("table_data"))
        return res

    @audit_to_local
    def get_overall_situation_table_data(self, request: Request):
        """ 查询总体情况 之 表格数据 """
        # 查询表格接口分离了，26 行数据需要差不多 0.6-0.7 秒，这是就体现出来分页的好处了。
        # 除此以外，django 自带的 json 可能也比 drf 慢一点，之后的优化方向就是这两部分。
        try:
            res = self._get_overall_situation_table_data_res(SimpleNamespace(query_params=request.query_params))
            return global_success_response(data=res)
        except SchemaError as e:
            logger.error("%s", f"{e}\n{traceback.format_exc()}")
            return global_error_response(msg=f"查询未闭环问题列表发生错误，原因：{e}")
        except Exception as e:
            return ns_utils.unexpected_error_occurred(e, "查询未闭环问题列表发生错误")

    def __generate_context_for_gmr(self, cleaned_data):
        this = self
        year_month, year, month = map(cleaned_data.get, ["year_month", "year", "month"])
        context = {
            "title": "逆向改进总览生成报告",
            "year": year,
            "month": month,
            "overall_situation": self._get_overall_situation_res(
                SimpleNamespace(query_params={
                    "year": year,
                    "month": month,
                })
            ),
            "overall_situation_table_data": self._get_overall_situation_table_data_res(
                SimpleNamespace(query_params={
                    "year": year,
                    "month": month,
                })
            ),
            "misstaskoveralltop_item": self._get_misstaskoveralltop_item_res(
                SimpleNamespace(query_params={
                    "year_month": year_month
                })
            )
        }

        # 闭环率的值需要处理一下，因为模板里面没有提供乘法
        cpi = context.get("overall_situation").get("count_psaqp_improvements")
        cpi["closed_rate"] = round(cpi.get("closed_rate") * 100, 4)
        return context

    @audit_to_local
    def generate_monthly_report(self, request: Request):
        """ 生成月报 """
        # 2024-10-11：当前生成月报的功能只有发邮件，不会生成压缩包了，为此，和生成压缩包的相关代码需要删除。
        # 具体描述一下此处的需求：
        # 起初，只是生成一份报告，又因为 PDF 的样式和前端的样式不一样，所以最后选择 HTML + CSS，生成一份压缩包。
        # 然后，需求变化，要求发送密送邮件，outlook 中很多 css 无法渲染出来，因此又需要了解一下 outlook 的格式，最终完成该需求。

        # 2024-10-14：后续极有可能添加自动发月报的功能，这个功能目前我不清楚如何实现。
        #             Linux + selenium + 一个平台账号 + 定时启动？这样应该能实现吧？

        # 注意事项：
        # 由于 .py 文件中不允许存在工号信息，因此选择以加载配置文件的方式解决该问题。
        # 但是最后发现个问题：密送邮件的发送目标有 36 人，而 .ini 文件中的值只能在一行。所以导致阅读和修改都很困难。

        html_template_name = "email_for_overall_situation2.html"
        config_key = "generate_monthly_report"

        try:

            # 权限认证，正式环境只有魏苗凤可以确认
            if settings.DEBUG:
                allowed_persons = ast.literal_eval(email_config.get(config_key, "debug_permission_allowed_persons"))
            else:
                allowed_persons = ast.literal_eval(email_config.get(config_key, "permission_allowed_persons"))

            if self.request.user_data.get("fullname") not in allowed_persons:
                if settings.DEBUG:
                    msg = f"当前环境为测试环境，只有以下人员有权限：{', '.join(allowed_persons)}"
                else:
                    msg = "您没有权限！"
                return global_error_response(msg=msg)

            cleaned_data = request.data
            # 2024-10-11：这里可能需要将图片分辨率固定，设置最大宽度和长度，否则因为是截图，可能存在异构设备相关问题
            #             举个例子，小组领导的台式机分辨率很大，可能导致图片过大，三张图片小屏幕没法一行查看。
            image_files = [cleaned_data.get(f"imgData{i + 1}") for i in range(9)]
            if not all(image_files):
                # 虽然前端应该解决了未截完图就调用接口的情况，但是加个这个保险一点。
                return global_error_response(msg="生成月报失败，可能存在网络问题，请再试一次。")

            context = self.__generate_context_for_gmr(cleaned_data)  # 生成模板上下文

            html_content = render_to_string(html_template_name, context, request)

            subject = f"【请阅】终端BG IT 逆向改进详细进展（{context.get('year')}年{context.get('month')}月）"
            if settings.DEBUG:
                subject = "（当前为测试环境）" + subject

            if settings.DEBUG:
                to_list = ast.literal_eval(email_config.get(config_key, "debug_to_list"))
                cc_list = ast.literal_eval(email_config.get(config_key, "debug_cc_list"))
                bcc_list = ast.literal_eval(email_config.get(config_key, "debug_bcc_list"))
            else:
                to_list = ast.literal_eval(email_config.get(config_key, "to_list"))
                cc_list = ast.literal_eval(email_config.get(config_key, "cc_list"))
                bcc_list = ast.literal_eval(email_config.get(config_key, "bcc_list"))

            list_email = list(set(to_list + cc_list + bcc_list))
            str_to = ",".join(to_list)
            str_cc = ",".join(cc_list)
            str_bcc = ",".join(bcc_list)

            attachments = []
            for i, file in enumerate(image_files):
                img = MIMEImage(file.read())
                img.add_header("Content-ID", f"<image{i}>")  # 设置Content-ID
                attachments.append(img)
            send_mail_with_cc_or_bcc(MailConfig(html_content, subject, str_to, str_cc, list_email,
                                                str_bcc=str_bcc, attachments=attachments))

            logger.info("%s", f"发送月报成功！\n发送人：{str_to}\n抄送人：{str_cc}\n密送人：{str_bcc}")
            return global_success_response(msg="生成月报并发送邮件成功！")
        except Exception as e:
            logger.error("%s", f"{e}\n{traceback.format_exc()}")
            return ns_utils.unexpected_error_occurred(e, "生成月报")

    def auto_send_monthly_report(self, request: Request):
        drive = webdriver.Chrome()
        if settings.DEBUG:
            drive.get("https://secevaluation-sit.cbgit.huawei.com/commonSecurity/reImprove/reImproveOverview")
        else:
            drive.get("")
        drive.find_element_by_class_name("anticon anticon-export").click()
        drive.quit()
