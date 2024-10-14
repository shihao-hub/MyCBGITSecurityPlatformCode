class AnalyzingUserViewSet(OldAnalyzingUserViewSet):
    ANALYSIS_PAGE_KEY_PREFIX = "measure_analysis_page_editing:"
    ANALYSIS_PAGE_EMPIRE_TIME = 300

    @classmethod
    def generate_cache_key(cls, unique_id):
        return f"{cls.ANALYSIS_PAGE_KEY_PREFIX}{unique_id}"

    @classmethod
    def set_cache_by(cls, key, value, empire_time=None):
        empire_time = empire_time if empire_time else cls.ANALYSIS_PAGE_EMPIRE_TIME
        cache.set(key, value, empire_time)

    @classmethod
    def get_cache_by(cls, key):
        return cache.get(key)

    @classmethod
    def delete_cache_by(cls, key):
        cache.delete(key)

    def get_analyzing(self, request, pk=None):
        """ 获取当前分析中用户 """
        user_data = request.user_data
        analyzing_by = self.get_cache_by(self.generate_cache_key(pk))
        if analyzing_by and analyzing_by != user_data.get("fullname"):
            return global_success_response(data=dict(allow_analyze=False, analyzing_by=analyzing_by),
                                           msg="{}正在编辑".format(analyzing_by))
        else:
            self.set_cache_by(self.generate_cache_key(pk), user_data.get("fullname"))
            return global_success_response(data=dict(allow_analyze=True))

    def reset_analyzing(self, request, pk=None):
        """ 重置分析中用户 """
        user_data = request.user_data
        analyzing_by = self.get_cache_by(self.generate_cache_key(pk))
        if user_data.get("fullname") == analyzing_by:
            cache.delete(self.generate_cache_key(pk))
        return global_success_response()



class ReverseImprovementAndDtsPlatform(ModelViewSet):
    @audit_to_local
    def get_dts_platform_data(self, request):
        def handle_request():
            return request

        def handle_parameters():
            return Schema({
                "id": And(lambda x: x is not None, error="id 为必填项")
            }).validate(dict(request.query_params.items()))

        try:
            # SLAP
            # 1. 处理请求
            # 2. 处理参数
            # 3. 处理数据
            request = handle_request()
            cleaned_data = handle_parameters()

            # 去 DTS 平台根据问题单号获取信息
            dts_detail_data = QueryDTSDetailControl().get_dts_detail([cleaned_data.get("id")])
            return global_success_response(data=dts_detail_data, msg="获取 DTS 平台的信息成功！")
        except Exception as e:
            return ns_utils.unexpected_error_occurred(e, where="获取 DTS 平台的信息")


class ReverseImprovementAndCombatPlatform(ModelViewSet):
    class GetCombatPlatformData:
        java_date_format = "%Y-%m-%dT%H:%M:%S.%fZ"

        @staticmethod
        def is_vulnerability_tracking_task(_id: str):
            # 暂时这样判断
            return not _id.startswith("WARN")

        @staticmethod
        def is_desktop_vulnerability(_id: str):
            # 暂时这样判断
            return _id.startswith("WARN")

        def __init__(self, source: "ReverseImprovementAndCombatPlatform", request: Request):
            self.source = source
            self.request = request

            self.cleaned_data = Schema({
                "id": And(lambda x: x is not None, error="id 为必填项")
            }, ignore_extra_keys=True).validate(dict(self.request.query_params.items()))

        def _generate_temporary_response_data(self, _id):
            this = self

            # 数据库没有同步他们那边的正式环境数据，所以应该这样显示：
            data = {"tracingTaskId": _id, "warningNo": _id}
            return data

        def apply(self):
            try:
                # SLAP：处理请求参数、查询和处理数据、返回响应

                # 2024-09-26：我认为，clean_data 的生成应该放在此处，明显点比较好！

                _id = self.cleaned_data.get("id")

                try:

                    if self.is_vulnerability_tracking_task(_id):
                        if _id.startswith("2"):
                            obj = VulnerabilityTrackingTask.objects.get(vulnerabilityId=_id)
                        else:
                            obj = VulnerabilityTrackingTask.objects.get(_id=_id)
                    elif self.is_desktop_vulnerability(_id):
                        obj = DesktopVulnerability.objects.get(_id=_id)
                    else:
                        raise TypeError(
                            f"出现可能既不是跟踪任务，也不是漏洞桌面的问题单号：{_id}")
                except mongoengine.DoesNotExist:
                    # 不存在应该要去获取吧？作战平台那边应该还需要根据 id 查询记录的功能...真麻烦
                    logger.error("%s", f"问题单号 {_id} 不存在！")
                    data = self._generate_temporary_response_data(_id)
                    return global_success_response(data=data, msg=f"问题单号 {_id} 不存在！")

                # (Q)!: mongoengine 只能 to_json 吗，还需要我手动转换？为什么 to_json 有 $ 符号？
                return global_success_response(data=dict(obj.to_mongo(use_db_field=False)))
            except SchemaMissingKeyError as e:
                return global_error_response(msg=f"获取作战平台数据模块出错，原因：{e}")
            except Exception as e:
                return ns_utils.unexpected_error_occurred(e, where="获取作战平台数据模块")

    @audit_to_local
    def get_combat_platform_data(self, request: Request):
        return self.GetCombatPlatformData(self, request).apply()


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

        # 在应用层排个序
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
        res = (query_set
               .values(f"{field_name}")
               .annotate(Count(f"{field_name}"))
               .order_by(f"{field_name}")
               .values_list(f"{field_name}", f"{field_name}__count"))

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
            res["NULL"] += empty_string

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


class MissTaskViewSet(OldMissTaskViewSet):
    """ 逆向改进管理页的接口--原漏测管理 create_time: 2022.10 """

    def get_all_misstaskdetail_list(self, request):
        """ 查询所有任务 """
        # 先设计好，暂未使用
        pass

    def export_misstaskdetail_list_as_excel(self, request):
        """ 导出数据为 Excel 表，共有三种导出：选中导出，筛选导出，全部导出 """
        # 先设计好，暂未使用
        pass

    def import_questions_list(self, request):
        """ 导入问题列表 """
        # 先设计好，暂未使用
        pass

    class SubmitAnalysisResult:
        required_fields = SubmitAnalysisResultValidator.Constant.required_fields
        optional_fields = SubmitAnalysisResultValidator.Constant.optional_fields

        def __init__(self, source: "MissTaskViewSet", request: Request):
            self.source = source
            self.request = request
            self.validator = SubmitAnalysisResultValidator

            self.keys_to_be_removed = set()
            # 在 __init__ 中这样允许吗？
            self.misstaskdetail_obj = (NewMissTaskDetail.objects
                                       .select_related("misstask")
                                       .get(pk=self.request.data.get("id")))
            self.misstask_obj = self.misstaskdetail_obj.misstask
            self.misstask_id = self.misstaskdetail_obj.misstask_id
            self.dts_no = self.misstaskdetail_obj.dts_no
            self.task_type = self.misstask_obj.task_type

            self.improvement_fields = [
                "security_architecture",  # 安全架构&方案刷新
                "manage",  # 管理&流程改进
                "open_source_governance",  # 开源治理规则改进
                "product_improve",  # 产品改进
                "secure_coding",  # 安全编码治理策略刷新
                "case_baseline",  # 特性/用例基线刷新
                "auto",  # 自动化/工具/平台改进
            ]
            if self.task_type == MissTaskModel.TASK_TYPES.xw:
                self.improvement_fields.extend([
                    "security_measures",  # 安防策略或措施改进
                    "compliance_policies",  # 合规策略&用例刷新
                ])

        # ------------------------------------------------------------------------------------------------------------ #
        def _check_editing(self):
            """ 检查是否正在被编辑 """
            this = self
            request = self.request

            record_id = request.data.get("id")
            user = request.user_data.get("fullname", "")
            cache_key = AnalyzingUserViewSet.generate_cache_key(record_id)

            editing_user = AnalyzingUserViewSet.get_cache_by(cache_key)
            if editing_user and editing_user != user:
                raise CustomException(f"用户 `{editing_user}` 正在编辑，无法提交。", data=dict(allow_analyze=False))
            AnalyzingUserViewSet.set_cache_by(cache_key, user)

        def _check_permissions(self):
            this = self
            request = self.request
            # 重构的时候将这个移进来了，虽然要多查一次，但是减少了参数个数
            # 而且这里可以优化的，因为只用到了 analyze_executor 字段，用 values 限制一下应该可行
            misstaskdetail_obj = NewMissTaskDetail.objects.get(pk=request.data.get("id"))
            analyze_executor = misstaskdetail_obj.analyze_executor
            login_user_roles = request.user_data.get("roles", [])
            is_administrator = "管理员" in login_user_roles
            is_analyze_executor = analyze_executor == request.user_data.get("fullname", "")
            if not is_administrator and not is_analyze_executor:
                raise CustomException("你不是当前任务的测试经理，没有权限")

        def __get_name(self, name, model=None):
            this = self
            model = model if model else NewMissTaskDetail
            return f"{model.get_verbose_name_by_var_name(name)}"  # ({name})

        def __generate_validation_only_when_related(self, name, related_name=None, model=None):
            """ 涉及时才是必填项的校验函数 """
            get_name = self.__get_name
            # 如果是不涉及，则允许通过验证。如果是涉及，则成为必填项，不可为空
            # 我不确定我这种方式是否适宜，但是我觉得还挺方便的
            #   但是我又发现，因为多了东西，删掉更安全...些许无语，到底有啥好办法没有？
            if related_name is None:
                related_name = name + "_related"
            if not self.request.data.get(related_name):
                key = str(uuid.uuid4())
                # 如果是不涉及，就插入
                self.keys_to_be_removed.add(key)
                return Optional(key), And(lambda x: x)

            return name, And(lambda x: x is not None and bool(x.strip()),
                             error=f"{get_name(name, model=model)}是必填项，不允许为空")

        def _validate_misstaskdetail_data(self, executors: OutputParameter[t.Dict]):
            # 2024-09-09：此处的校验工作由于涉及与不涉及的存在导致有点混乱，需要重新设计

            required_fields = self.required_fields
            optional_fields = self.optional_fields
            keys_to_be_removed = self.keys_to_be_removed
            get_name = self.__get_name
            generate_validation_only_when_related = self.__generate_validation_only_when_related

            # executor 字段不是存在 misstaskdetail 表里的...
            required_executors = ["product_improve"]
            executors.set_value(Schema({
                **dict([
                    (Optional(get_executor_name(name)), And(lambda x: x is not None, Use(lambda x: get_cn_name(x))))
                    for name in [e for e in self.improvement_fields if e not in required_executors]
                ]),
                **dict([
                    # 如果是涉及，则为必填项，否则为选填，2024-09-26：目前就产品改进一个
                    # 2024-09-26：这里的代码太烂了，未来再有需求变动时，此处需要重构
                    #             不得不说，难怪《重构》不是一件专门做的事情，而且一种编程能力，在编程中无时无刻都要使用。。
                    (get_executor_name(name)
                     if self.request.data.get(name + "_related")
                     else Optional(get_executor_name(name)),
                     And(lambda x: x is not None, Use(lambda x: get_cn_name(x))))
                    for name in required_executors
                ])
            }, ignore_extra_keys=True).validate(self.request.data))

            # 【一】 required_fields 内的字段全部必填
            required_fields_schema = {}
            for name in required_fields:
                error_msg = f"{get_name(name)}是必填项，不允许为空"
                required_fields_schema[name] = And(lambda x: x is not None, error=error_msg)

            # 【二】 可选，校验一下类型，按道理来说应该不必校验吧。毕竟这是前后端联调的，又不是对外接口，难以交流。
            optional_fields_schema = {}
            # #(C)!: for name in optional_fields:
            # #(C)!:     error_msg = f"{get_name(name)}必须是字符串"
            # #(C)!:     optional_fields_schema[Optional(name)] = And(str, error=error_msg)

            # 【三】 improvement_fields 内的字段加上 _related 是可选字段
            improvement_fields_related_schema = {
                Optional("technical_reason_related"): And(bool),
                Optional("process_manage_reason_related"): And(bool),
            }
            for name in self.improvement_fields:
                improvement_fields_related_schema[Optional(name + "_related")] = And(bool)

            # 【四】 improvement_fields 内的字段，涉及则必填
            improvement_fields_when_related_schema = dict([
                generate_validation_only_when_related("technical_reason"),  # 技术根因
                generate_validation_only_when_related("process_manage_reason"),  # 流程/管理根因
            ])
            for name in self.improvement_fields:
                key, value = generate_validation_only_when_related(name)
                improvement_fields_when_related_schema[key] = value

            # 校验前端传来的字段中要存入 misstaskdetail 的那些
            detail_schema_obj = Schema({
                **required_fields_schema,
                **optional_fields_schema,
                **improvement_fields_related_schema,
                **improvement_fields_when_related_schema,
            }, ignore_extra_keys=True)
            detail_data = detail_schema_obj.validate(self.request.data)
            for e in keys_to_be_removed:
                detail_data.pop(e, None)
            return detail_data

        def _update_or_create_database_data(self, executors: OutputParameter[t.Dict], detail_data: dict):
            # 注意，表单有问题（不要 form.save()），不是更新有的字段，而是直接全部清空，生成一个新的？这个好危险。
            # #(C)!: form = NewMissTaskDetailForm(detail_data, instance=misstaskdetail_obj)
            # 目前此处仅充当校验功能，此时已经确认上面这一行是可以实现更新作用的！
            form = NewMissTaskDetailForm(detail_data)
            if not form.is_valid():
                return global_error_response(msg=NewMissTaskDetailForm.get_processed_form_errors(form))

            # 要先创建改进措施再更新 Detail 表的内容！！！
            task_type = self.task_type
            misstask_id = self.misstask_id
            dts_no = self.dts_no
            with transaction.atomic():
                for var_name in self.improvement_fields:
                    related_var_name = var_name + "_related"
                    related = bool(detail_data.get(related_var_name))  # 涉及与否
                    improvement = MissTaskImprove.IMPROVEMENT_NA if not related else detail_data.get(var_name, "")

                    detail_data[var_name] = improvement  # 无语了，这个 improvement 两张表都存了？

                    filter_data = dict(improvement_type=getattr(CnVar, var_name))
                    improve_qs = MissTaskImprove.get_queryset_by(misstask_id, dts_no, filter_data=filter_data)
                    validate_assumption(improve_qs.count() < 2, "查询到了两条记录")

                    if getattr(self.misstaskdetail_obj, related_var_name) and not related:
                        improve_qs.delete()

                    # 2024-09-25：此处当时的逻辑是，改进措施没有创建，则创建它，如果已经创建了，则只允许更新它
                    #             上面这个逻辑是有问题的。怎么处理呢？
                    #             在此之前加个判断？如果某条记录存在，但是现在是不涉及，则将其删掉！
                    unique_filter_data = dict(
                        misstask_id=misstask_id,
                        improvement_type=getattr(CnVar, var_name),
                        dts_no=[dts_no],
                        YN_delete=0,
                    )
                    if not improve_qs.exists():
                        # 如果不存在，即第一次提交，则创建
                        MissTaskImprove.objects.create(**dict(
                            **unique_filter_data,
                            improvement=improvement,
                            reform_executor=executors.get_value().get(get_executor_name(var_name)),
                            update_by=self.request.user_data.get("fullname"),
                        ))
                    else:
                        # (TD)!: 注意，只要提交过了，改进措施将不允许再变化了，除非加一个重新分析的按钮！

                        # 不能更新改进措施的涉及和不涉及关系，只能修改内容
                        # #(C)!: if related != getattr(self.misstaskdetail_obj, related_var_name):
                        # #(C)!:     raise CustomException("不允许在分析完成后，修改改进措施的涉及关系，只允许修改内容！")
                        # 2024-09-25：上面这个逻辑是有问题的，应该是允许的，但是这就相对复杂一点了

                        # 不能更新已经闭环的改进措施
                        improve_obj = MissTaskImprove.objects.get(**unique_filter_data)
                        if improve_obj.close_status == MissTaskImprove.CloseStatus.CLOSE:
                            # 之所以不 raise 了，是因为，用 continue 只是没有提示而已，改动会失败就行了！
                            # #(C)!: raise CustomException("不允许修改已经闭环的改进措施的内容")
                            continue

                        MissTaskImprove.objects.filter(**unique_filter_data).update(**dict(
                            improvement=improvement,
                            reform_executor=executors.get_value().get(get_executor_name(var_name)),
                        ))

                # 执行到此处代表必填项都填完了
                detail_data["analyze_status"] = 1
                executor_obj, _ = (MissTaskReformExecutor.objects
                                   .update_or_create(defaults=executors.get_value(),
                                                     pk=self.misstaskdetail_obj.misstaskreformexecutor_id))
                # 2024-09-19：update 可以传 executor_obj.id，create 的时候只能传 executor_obj
                NewMissTaskDetail.objects.filter(pk=self.request.data.get("id")).update(**{
                    **detail_data,
                    "reform_executor": list(executors.get_value().values()),
                    "misstaskreformexecutor": executor_obj.id
                })
                return executors, detail_data

        def submit_analysis_result(self):
            # 需要尽量将原有数据表之间的复杂关系封装起来
            try:
                # Single Level of Abstraction Principle, SLAP（抽象层次一致性原则）
                # 1. 提前校验
                # 2. 校验接口参数并处理生成用于存储的数据
                # 3. 更新数据库数据
                # 4. 判断当前状态

                self._check_editing()  # 检查是否正在被编辑
                self._check_permissions()  # 只有管理员和分析责任人即测试经理才可以分析

                # 校验 request.data 的内容，里面的内容必须全能存入 misstaskdetail 表中！
                executors: OutputParameter[t.Dict] = OutputParameter()
                detail_data = self._validate_misstaskdetail_data(executors)
                # 需要我处理的其他字段，这个地方问题很大。目前来说只能这样，但是肯定不能只是这样。
                if detail_data.get("analyze_executor"):
                    detail_data["analyze_executor"] = get_cn_name(detail_data.get("analyze_executor"))
                else:
                    detail_data["analyze_executor"] = ""
                detail_data["analyze_status"] = self.misstaskdetail_obj.analyze_status
                detail_data["confirmed_status"] = self.misstaskdetail_obj.confirmed_status
                detail_data["description"] = self.misstaskdetail_obj.description
                detail_data["detail_desc"] = self.misstaskdetail_obj.detail_desc
                detail_data["update_time"] = timezone.now()

                # (TD)!: 校验一下参数的值，但是我觉得这显然可以给 Excel 加下拉框限制

                # (Q)!: 前后端不分离，Form 很有用，但是分离之后，Form 还需要用吗？
                # 2024-09-09：这个函数重构的很符合《重构》这本书，将临时变量变成整个类的变量，这样就可以缩减参数长度！
                #            返回了值，这代表传进去的参数被修改了！但是我不能将其隐藏起来，这种隐藏的副作用不好！
                executors, detail_data = self._update_or_create_database_data(executors, detail_data)

                # 这个也是个关键，需要重构...
                judge_improve_status(self.misstask_id, [self.dts_no])
                return global_success_response(data={
                    **detail_data,
                    **executors.get_value(),
                    "allow_analyze": True
                }, msg="提交分析结果成功")
            except SchemaMissingKeyError as e:
                # (Q)!: SchemaWrongKeyError SchemaForbiddenKeyError SchemaOnlyOneAllowedError SchemaUnexpectedTypeError
                return global_error_response(msg=f"提交分析结果失败，原因：存在必填项未填写，请检查！")  # #(C)!: {e}
            except SchemaError as e:
                return global_error_response(msg=f"提交分析结果失败，原因：{e}")
            except CustomException as e:
                return global_error_response(data=e.data, msg=f"提交分析结果失败，原因：{e}")
            except Exception as e:
                return ns_utils.unexpected_error_occurred(e, where="提交分析结果")

    @audit_to_local
    def new_update_misstask_detail(self, request):
        return self.SubmitAnalysisResult(self, request).submit_analysis_result()

    @audit_to_local
    def distribute_test_manager(self, request: Request):
        """ 分发测试经理 """
        validator = DistributeTestManagerValidator
        try:
            data = validator(**request.data)
            data.test_manager = get_cn_name(data.test_manager)
            with transaction.atomic():
                inst = NewMissTaskDetail.objects.get(pk=data.id)
                # 添加个校验：管理员和原测试经理和改进措施责任人才能分发
                is_administrator = "管理员" in request.user_data.get("roles", [])
                if not is_administrator:
                    login_person = get_cn_name(request.user_data.get("fullname", ""))
                    if login_person != inst.analyze_executor:
                        raise CustomException(f"无法分发，原测试经理({inst.analyze_executor})才能分发")
                    if login_person not in inst.reform_executor:
                        raise CustomException(f"无法分发，改进措施责任人({inst.reform_executor})才能分发")
                inst.analyze_executor = data.test_manager
                inst.save()  # commit
            user_list = [data.test_manager]
            context = {
                "dts_no": inst.dts_no,
                "level": inst.level,
                "yn_common": inst.yn_common,
                "control_point": inst.control_point,
                "description": inst.description,
                "id": inst.id,
                "task_type": inst.misstask.task_type,
            }
            logger.info("%s", f"{pprint.pformat(context)}")
            NotificationManager.get_instance().notify_when_distribute_test_manager(user_list, context)
            return global_success_response(msg="分发测试经理成功")
        except pydantic.ValidationError as e:
            error = PydanticCustomBaseModel.errors_formatting(e)
            return global_error_response(msg=f"分发测试经理失败，原因：{error}")
        except CustomException as e:
            return global_error_response(data=e.data, msg=f"分发测试经理失败，原因：{e}")
        except Exception as e:
            return ns_utils.unexpected_error_occurred(e, where="分发测试经理功能")

    class CreateMissTaskDetailInstance:

        @staticmethod
        def chinese_character_exists(a_str):
            return any(["CJK" in unicodedata.name(char) for char in a_str])

        def __init__(self, source: "MissTaskViewSet", request: Request):
            self.source = source
            self.request = request
            self.validator = CreateMissTaskDetailInstanceValidator
            self.validate_data = self._schema_validator()

            self.task_type = self.validate_data.get("task_type")
            self.is_sj = self.task_type == MissTaskModel.TASK_TYPES.sj
            self.is_xw = self.task_type == MissTaskModel.TASK_TYPES.xw

            if self.is_sj:
                self.mapping1 = dict(constants.SJ_ONE_MAPPING)
                self.mapping2 = dict(constants.SJ_TWO_MAPPING)
                self.improvement_measures = [v[1] for v in constants.SJ_IMPROVEMENT_MEASURES]
            elif self.is_xw:
                self.mapping1 = dict(constants.XW_ONE_MAPPING)
                self.mapping2 = dict(constants.XW_TWO_MAPPING)
                self.improvement_measures = [v[1] for v in constants.XW_IMPROVEMENT_MEASURES]
            else:
                raise TypeError(f"任务类型目前只有两种：{MissTaskModel.TASK_TYPES}")

        def _schema_validator(self):
            error_msgs = collections.namedtuple("error_msgs", ("task_type",))(**dict(
                task_type=f"{MissTaskModel.get_verbose_name('task_type')} 为必填字符串"
            ))

            res = Schema({
                "task_type": And(str, error=error_msgs.task_type),
                "file": And(dict),
            }).validate(self.request.data)
            return res

        def create_one(self, reversed_header: t.Dict[int, t.Any], row_data: t.List[t.Any]):
            """ 创建 misstaskdetail 和 misstask 两条记录，且二者是一一对应关系 """
            login_person = self.request.user_data.get("fullname")

            with transaction.atomic():
                # 创建 MissTaskModel
                create_time = timezone.now()
                # project 需要动态生成，但是这个 project 是现网用的字段，送检用的是 version，这该如何处理呢？
                project = self.task_type + "-" + f"{create_time.strftime('%Y%m')}"
                misstask_data = {
                    "task_type": self.task_type,
                    "creator": login_person,
                    "create_time": create_time,
                    "project": project
                }
                misstask_obj = MissTaskModel.objects.create(**misstask_data)

                # 创建 NewMissTaskDetail
                detail_data = {}
                for i, v in enumerate(row_data):
                    cn = reversed_header.get(i)
                    # 因为是两行表头，而且第二行有些不用，所以需要以这种方式获取，太难命名了，只能用注释来解释了
                    key = self.mapping1.get(cn) or self.mapping2.get(cn)
                    if not bool(key):
                        raise RuntimeError(f"出现异常：`cn = {cn}, key = {key}`")
                    detail_data[key] = v

                # 此处创建的时候不需要存责任人（其实主要还是历史遗留的问题，暂且如此吧）
                detail_data.update({
                    "misstask": misstask_obj
                })
                # 注意，detail_data 的数据还需要处理，比如：是否重犯数据库存的是 bool，而 excel 中是中文
                detail_data = self._process_detail_data(detail_data)
                NewMissTaskDetail.objects.create(**detail_data)  # create 时 misstask 存的 instance，update 时是 id

                # #(C)!: logger.info("%s", f"{pprint.pformat(detail_data)}")

        def _sj_get_auto_filled_field_values(self, detail_data, initial=None):
            auto_filled_field_values = initial if initial else {}

            dts_no = detail_data.get("dts_no")

            auto_filled_fields_mapping = (
                # 问题描述
                ("description", "sBriefDescription"),
                # 问题时间、级别
                ("dts_create_time", "createAt"), ("level", "serverityNoName"),
                # 类型、问题来源、版本、应用、部门
                ("problem_type", None), ("dts_come", None),
                ("version", None), ("service", None), ("subproduct", None), ("product", None),
            )

            for dts_detail_data in QueryDTSDetailControl().get_dts_detail([dts_no], extra_fields=[
                "prodInfo",
                "sBriefDescription",  # 简要描述
            ]):
                logger.info("%s", f"{pprint.pformat(dts_detail_data)}")
                for value in auto_filled_fields_mapping:
                    k_name, v_name = value[0], value[1]
                    # v_name 不存在时，需要特别处理，单纯的 if else 语义并不明了
                    if v_name:
                        if not detail_data.get(k_name):
                            auto_filled_field_values[k_name] = dts_detail_data.get(v_name)

                # 【2024-09-25】
                # 类型：从简要描述中筛出来，类型是第三个【】内的内容
                if not detail_data.get("problem_type"):
                    brief_desc = dts_detail_data.get("sBriefDescription")
                    problem_type_mapping = [
                        ("A1", "红线A1"),
                        ("A2", "红线A2"),
                        ("B类", "红线B类"),
                        ("TOPN", "TOPN类"),
                        ("隐私", "隐私基线"),
                    ]
                    problem_type = "其他问题"
                    pattern = re.compile(r"【.*?】【.*?】【(.*?)】")
                    match = re.search(pattern, brief_desc)
                    if match:
                        raw_problem_type = match.group(1)
                        for v2 in problem_type_mapping:
                            k_name, v_name = v2[0], v2[1]
                            if k_name in raw_problem_type:
                                problem_type = v_name
                                break
                    auto_filled_field_values["problem_type"] = problem_type

                # 问题来源：从简要描述中筛出来，来源是 ICSL 或 IT ICSL，正常情况是必有的！
                if not detail_data.get("dts_come"):
                    brief_desc = dts_detail_data.get("sBriefDescription")
                    dts_come_list = ["ICSL", "IT ICSL"]
                    for e in dts_come_list:
                        if f"{e}" in brief_desc:
                            dts_come = e + "送检"
                            auto_filled_field_values["dts_come"] = dts_come
                            break

                # 部门、应用、版本、子产品
                for k, v in {
                    "product": "sProdXdtNoName",
                    "service": "sServiceName",
                    "version": "sServiceVerName",
                    "subproduct": "sProdNoName",
                }.items():
                    if not detail_data.get(k):
                        auto_filled_field_values[k] = dts_detail_data.get(v)

                break  # 只要一条，但是 get_dts_detail 是生成器，所以放到 for 循环中用 break 方便一点
            return auto_filled_field_values

        def _xw_get_auto_filled_field_values(self, detail_data, initial: t.Optional[t.Dict] = None):
            this = self

            auto_filled_field_values = copy.deepcopy(initial) if initial else {}

            is_vulnerability_tracking_task = (ReverseImprovementAndCombatPlatform
                                              .GetCombatPlatformData
                                              .is_vulnerability_tracking_task)

            dts_no = detail_data.get("dts_no")

            try:
                # 此处可以运用模板函数重构法，抽成两个类，但是这应该也要看情况吧？假如这个类抽取之后也只会用一次的话。。。
                if is_vulnerability_tracking_task(dts_no):
                    def _get_auto_filled_fields_mapping():
                        return [
                            # 问题描述
                            ("description", "tracingTaskName"),
                            # 问题时间、级别
                            ("dts_create_time", "vulnerabilityCreateTime"), ("level", "vulnerabilitySeverity"),
                            # 类型、问题来源
                            ("problem_type", "vulnerabilityCategory"), ("dts_come", None),
                            # 版本、应用、子产品、部门
                            ("version", None), ("service", "service"),
                            ("subproduct", "subproduct"), ("product", "product"),
                        ]

                    def _get_inst():
                        if dts_no.startswith("2"):
                            inst = VulnerabilityTrackingTask.objects.get(vulnerabilityId=dts_no)
                        else:
                            inst = VulnerabilityTrackingTask.objects.get(_id=dts_no)
                        return inst

                    def execute():
                        inst = _get_inst()
                        for value in _get_auto_filled_fields_mapping():
                            k_name, v_name = value[0], value[1]
                            if v_name and not detail_data.get(k_name):
                                auto_filled_field_values[k_name] = getattr(inst, v_name)

                    execute()
                else:
                    def _get_auto_filled_fields_mapping():
                        return [
                            # 问题描述
                            ("description", "vulnerabilityDescription"),
                            # 问题时间、级别
                            ("dts_create_time", "discoveryTime"), ("level", None),
                            # 类型、问题来源
                            ("problem_type", None), ("dts_come", None),
                            # 版本、应用、子产品、部门
                            ("version", None), ("service", "service"),
                            ("subproduct", "subproduct"), ("product", "product"),
                        ]

                    def _get_inst():
                        return DesktopVulnerability.objects.get(_id=dts_no)

                    def execute():
                        inst = _get_inst()
                        for value in _get_auto_filled_fields_mapping():
                            k_name, v_name = value[0], value[1]
                            if v_name and not detail_data.get(k_name):
                                auto_filled_field_values[k_name] = getattr(inst, v_name)

                    execute()
            except mongoengine.DoesNotExist as e:
                logger.error("%s", f"{e}")
            return auto_filled_field_values

        def _get_auto_filled_field_values(self, detail_data):
            # 问题描述
            # 问题时间、级别、类型、问题来源、版本、应用、部门

            # 如果表中有这些信息，则以用户的为主
            auto_filled_field_values = {}
            product_info = ["product", "subproduct", "service", "version"]
            auto_filled_field_values.update({
                "description": detail_data.get("description"),
                **{name: detail_data.get(name) for name in product_info},
            })

            if self.is_sj:
                res = self._sj_get_auto_filled_field_values(detail_data, initial=auto_filled_field_values)
            elif self.is_xw:
                res = self._xw_get_auto_filled_field_values(detail_data, initial=auto_filled_field_values)
            else:
                raise TypeError("超出类型 [is_sj, is_xw]")
            return res

        def _process_detail_data(self, detail_data: t.Dict) -> t.Dict:
            this = self

            # 2024-09-25：这些内部函数，规定：_ 开头的函数是需要用到临时变量的函数，没有 _ 的函数必须可以无成本移出去！

            def log_analyze_executor(_analyze_executor):
                logger.info("%s", f"analyze_executor: {_analyze_executor}")

            dts_no = detail_data.get("dts_no")

            # 2024-09-25：请注意，这个函数里面生成了 filter_data_of_analyze_executor 的内容，这导致代码的执行顺序受限制
            #             这是违背《重构》原则的，查询和修改应该拆分开来，此处因为是我刚刚实现的，所以我才能发现这个问题！
            auto_filled_field_values = self._get_auto_filled_field_values(detail_data)

            # 2024-09-29：找机会拆出来了
            filter_data_of_analyze_executor = {}
            for name in ["product", "subproduct", "service"]:
                filter_data_of_analyze_executor[name] = detail_data.get(name)
                if not detail_data.get(name):
                    filter_data_of_analyze_executor[name] = auto_filled_field_values.get(name)
            logger.info("%s", f"filter_data: {filter_data_of_analyze_executor}")

            # -------------------------------------------------------------------------------------------------------- #
            # 2024-09-25：此处是特别处理（修 BUG 的），将 _related 添加进来
            for name in self.improvement_measures:
                if detail_data.get(name):
                    detail_data[name + "_related"] = True

            # 任务信息要注意，目前 ICSL 送检用的是 version、现网用的是 MissTaskModel 里的 project

            # 分析责任人、验收负责人需要单独处理，验收责任人暂且不处理，因为涉及的代码分布过于零散，需要时间（2024-09-19）
            # 1. 至少能够将英文工号转为中文工号
            # 2. 如果没有填写，则自动去数据库查询（实现这个功能的前提是部门的值不为空）
            analyze_executor = detail_data.get("analyze_executor")
            if not analyze_executor:
                # 2024-10-12：需要注意的是，测试环境这两张表很多信息没有，所以导入的时候必须填写分析责任人。
                def _get_approver_in_gyapprovemanager():
                    approver = None
                    try:
                        # - res = (GYApproveManager.objects.get(**filter_data_of_analyze_executor)
                        # -        .get_info.get("approver"))
                        approver = GYApproveManager.objects.get(**filter_data_of_analyze_executor).approver
                        logger.info("%s", f"approver: {approver}")
                    except GYApproveManager.DoesNotExist as e:
                        # \n因为ICSL 送检版本管理或质量红线表中不存在如下 {filter_data_of_analyze_executor} 记录
                        msg = f"表格中的问题单号为 {dts_no} 的记录的分析责任人为必填项！"
                        if settings.DEBUG:
                            msg += "            "
                            msg += "（当前为测试环境，正式环境不会出现这种报错，这是因为测试环境的数据库表数据不全）"
                        raise CustomException(msg) from e
                    except GYApproveManager.MultipleObjectsReturned as e:
                        # #(C)!: raise CustomException(f"通过 {self.filter_data_of_analyze_executor} 查表，"
                        # #(C)!:                      f"查询到了多个值！") from e
                        pass
                    return str(approver)

                if self.is_sj:
                    # 直接查送检表
                    analyze_executor = _get_approver_in_gyapprovemanager()
                elif self.is_xw:
                    # 按顺序去查找质量红线、送检表中的项目经理
                    try:
                        # - analyze_executor = (RLTaskApproveManager.objects.get(**filter_data_of_analyze_executor)
                        # -                     .get_info.get("approver").get("fullname"))
                        analyze_executor = (RLTaskApproveManager.objects
                                            .get(**filter_data_of_analyze_executor)
                                            .get_info.get("approver").get("fullname"))
                    except RLTaskApproveManager.DoesNotExist:
                        analyze_executor = _get_approver_in_gyapprovemanager()
                    except RLTaskApproveManager.MultipleObjectsReturned as e:
                        # #(C)!: raise CustomException(f"通过 {filter_data_of_analyze_executor} 查表，"
                        # #(C)!:                       f"查询到了多个值！") from e
                        pass

            if not analyze_executor:
                raise CustomException(f"自动填充分析责任人字段失败，问题单号 {dts_no} 这条记录需要手动填写分析责任人")

            # 这个必不可少！
            if not self.chinese_character_exists(analyze_executor):
                analyze_executor = get_cn_name(analyze_executor)

            log_analyze_executor(analyze_executor)
            # -------------------------------------------------------------------------------------------------------- #

            # 改进措施责任人有点特别，暂且如此
            reform_executor = "[]"

            # 是否共性问题需要单独处理 -> 因为传来的是中文或者空字符串
            yn_common = detail_data.get("yn_common")
            if not yn_common:
                yn_common = NewMissTaskDetail.YNEnum.NO.value
            else:
                yn_common = {v: k for k, v in NewMissTaskDetail.YNEnum.to_mapping().items()}.get(yn_common)

            # 改进状态、分析状态、验收状态需要单独处理
            # 先处理 分析状态 -> 因为传来的是中文或者空字符串
            analyze_status = detail_data.get("analyze_status")
            if not analyze_status:
                analyze_status = NewMissTaskDetail.AnalyzeStatusEnum.PENDING.value
            else:
                mapping = NewMissTaskDetail.AnalyzeStatusEnum.to_mapping().items()
                analyze_status = {v: k for k, v in mapping}.get(analyze_status)
            # 2024-09-19：暂且如此，默认都是分析中、待改进、待验收，不论填什么！后续分析中可能需要处理，比如直接分析完成了。
            analyze_status = NewMissTaskDetail.AnalyzeStatusEnum.PENDING.value
            improvement_status = "待改进"
            acceptance_status = "待验收"

            # 是否重犯和确认状态为特殊字段，暂且如此特别处理
            try:
                repeated = fields_mapping(detail_data.get("repeated"), "repeated", reverse=True)
            except ValueError:
                repeated = None

            try:
                confirmed_status = fields_mapping(detail_data.get("confirmed_status"), "confirmed_status", reverse=True)
            except ValueError:
                confirmed_status = 0

            detail_data.update({
                "reform_executor": reform_executor,
                "improvement_status": improvement_status,
                "acceptance_status": acceptance_status,
                "analyze_status": analyze_status,
                "analyze_executor": analyze_executor,
                "yn_common": yn_common,
                "repeated": repeated,
                "confirmed_status": confirmed_status,
                **auto_filled_field_values
            })
            return detail_data

        def create_misstaskdetail_instance(self):
            request = self.request
            try:
                file_info = request.data.get("file")
                file_id = file_info.get("file_id")
                file_name = file_info.get("file_name")
                unique_file_name = str(uuid.uuid4()) + os.path.splitext(file_name)[1]
                temporary_file_path = os.path.join(settings.TEMPORARY, unique_file_name)

                fdfs_client = FdfsClient()
                fdfs_client.download_to_file(temporary_file_path, file_id)

                reader = ExcelReader(ExcelHandler(temporary_file_path))
                reader.load_workbook()

                # 此处需要增加一个校验，由于用户的输入是不可信的，所以此处应该判断一下模板的正确性
                target_headers = []
                if self.task_type == MissTaskModel.TASK_TYPES.sj:
                    target_headers = [constants.SJ_HEADER_OF_FIRST_LINE, constants.SJ_HEADER_OF_SECOND_LINE]
                elif self.task_type == MissTaskModel.TASK_TYPES.xw:
                    target_headers = [constants.XW_HEADER_OF_FIRST_LINE, constants.XW_HEADER_OF_SECOND_LINE]
                if not reader.is_valid_excel_header(target_headers):
                    return global_error_response(msg=f"请检查当前的模板是否是`{self.task_type}`的模板")

                excel_data = reader.read_data(min_row=3)
                # 2024-09-24：这个参数命名不合适，但是暂且如此吧
                reversed_header = reader.get_reversed_table_header()

                # 2024-09-19：此处可以使用线程池，分片处理

                error_msgs = []
                cnt = 2
                for row in excel_data:
                    # 注意，存在必填字段，问题单号
                    cnt += 1
                    dts_no = row[0]
                    if not dts_no:
                        error_msgs.append(f"第 {cnt} 行的问题单号为空，该行数据创建失败\n")
                        continue

                    # 注意，问题单号是 unique 的，应用层过滤一下
                    # #(C)!: if NewMissTaskDetail.objects.filter(dts_no=dts_no).exists():
                    # #(C)!:     error_msgs.append(f"问题单号为 {dts_no} 的记录已经存在，请勿重复创建\n")
                    # #(C)!:     continue

                    self.create_one(reversed_header, row)

                reader.close_workbook()
                msg = "新建成功！"
                if error_msgs:
                    msg += "\n" + "".join(error_msgs)
                return global_success_response(msg=msg)
            except CustomException as e:
                return global_error_response(msg=f"逆向改进的新建功能发生错误，原因：{e}")
            except Exception as e:
                return ns_utils.unexpected_error_occurred(e, where="逆向改进的新建功能")

    @audit_to_local
    def create(self, request, *args, **kwargs):
        # #(C)!: return self.create_misstaskdetail_instance(request)
        return self.CreateMissTaskDetailInstance(self, request).create_misstaskdetail_instance()

    class ImproveAndAccept:
        """ 重构 之 以函数对象取代函数 """

        def __init__(self, source: "MissTaskViewSet", request: Request):
            self.source = source  # 源对象，且不可变，如果需要调用源对象的任何函数，请通过此字段调用
            self.request = request

            # 针对原函数的每个临时变量和每个参数，在新类中建立一个对应的字段保存之，这样就可以避免传参了

        @staticmethod
        def _compare(o1, o2):
            # 2024-08-08：改进措施列表需要将不涉及放在后面
            if o2.get("improvement", "").strip() == MissTaskImprove.IMPROVEMENT_NA:
                return -1
            return 1

        def __get_misstaskimprove_res(self, misstask_id, dts_no, parameters: SimpleNamespace):
            this = self

            second_querydict = parameters.second_querydict
            improve_exclude = parameters.improve_exclude

            # 新需求，is_timeout 是计算出来的，我得在应用层处理一下，而且必须删掉这个字段，因为数据库里没有这个字段
            is_timeout = second_querydict.pop("is_timeout", None)

            filter_data = {"misstask_id": misstask_id, "dts_no__icontains": dts_no, "YN_delete": 0}

            query_conditions = []
            if second_querydict:
                fuzzy_query = {k + "__icontains": v for k, v in second_querydict.items()}

                # 修复通过 dts_no 进行模糊查询时的问题
                dts_no_key = "dts_no__icontains"
                if fuzzy_query.get(dts_no_key):
                    conditions = [fuzzy_query.pop(dts_no_key), filter_data.pop(dts_no_key)]
                    query_conditions.append(Q(**{dts_no_key: conditions[0]}) & Q(**{dts_no_key: conditions[1]}))

                filter_data.update(fuzzy_query)

            misstaskimprove_only_values = (
                "id", "dts_no", "improvement", "reform_executor", "close_progress",
                "close_status", "update_by", "close_plan_time", "final_close_datetime",
                "acceptance_status", "update_time", "improvement_type", "attachment_id__id",
            )

            res = (MissTaskImprove.objects
                   .filter(*query_conditions, **filter_data)
                   .exclude(**improve_exclude)
                   .annotate(**MissTaskImprove.get_condition_of_is_timeout())
                   .values(*misstaskimprove_only_values,
                           "is_timeout",
                           file_id=F("attachment_id__fileid"),
                           file_name=F("attachment_id__filename")))

            if is_timeout is not None:
                res = [e for e in res if e.get("is_timeout") == is_timeout]
            return res

        def __get_misstaskacceptrecord_res(self, misstask_id, dts_no):
            this = self

            misstaskimprove_qs_in_acceptance_status = (
                MissTaskImprove
                .get_queryset_by(misstask_id, dts_no,
                                 filter_data={
                                     "acceptance_status__in": [
                                         MissTaskImprove.AcceptanceStatusEnum.TO_BE_ACCEPT.value,
                                         MissTaskImprove.AcceptanceStatusEnum.PASS.value,
                                         MissTaskImprove.AcceptanceStatusEnum.REJECT.value,
                                     ]
                                 }))
            res = []
            for improve_obj in misstaskimprove_qs_in_acceptance_status:
                detail_obj = improve_obj.get_misstaskdetail_obj()

                misstaskacceptrecord_qs = (MissTaskImproveAcceptRecord.objects
                                           .filter(misstask_improve_id=improve_obj.id, operation_type=2)
                                           .order_by("-id"))

                misstaskacceptrecord_only_values = (
                    "file_id", "file_name", "conclusion", "misstask_improve_id",
                    "misstask_improve__acceptance_status", "create_time",
                )
                misstaskacceptrecord_dict = (
                    misstaskacceptrecord_qs
                    .values(*misstaskacceptrecord_only_values,
                            acceptance_owner=Value(detail_obj.analyze_executor, output_field=models.CharField()),
                            final_close_datetime=F("misstask_improve__final_close_datetime"))
                    .first())

                if misstaskacceptrecord_dict:
                    misstaskacceptrecord_dict["is_reject"] = (misstaskacceptrecord_qs
                                                              .filter(acceptance_status=2, operation_type=2)
                                                              .exists())
                    misstaskacceptrecord_dict["id"] = misstaskacceptrecord_dict.pop("misstask_improve_id")
                    misstaskacceptrecord_dict["acceptance_status"] = misstaskacceptrecord_dict.pop(
                        "misstask_improve__acceptance_status")
                else:
                    misstaskacceptrecord_dict = dict(file_id=None, file_name="", conclusion="", id=improve_obj.id,
                                                     final_close_datetime=improve_obj.final_close_datetime,
                                                     acceptance_status=improve_obj.acceptance_status, create_time="",
                                                     acceptance_owner=detail_obj.analyze_executor)
                res.append(misstaskacceptrecord_dict)
            return res

        def _get_one(self, misstask_id, dts_no, second_querydict=None, improve_exclude=None):
            second_querydict = second_querydict if second_querydict else {}  # 请确保需要模糊查询的
            improve_exclude = improve_exclude if improve_exclude else {}  # 额外需要排除

            # 查找改进措施
            misstaskimprove_res = self.__get_misstaskimprove_res(misstask_id, dts_no, SimpleNamespace(
                second_querydict=second_querydict,
                improve_exclude=improve_exclude,
            ))
            misstaskimprove_res = sorted(misstaskimprove_res, key=functools.cmp_to_key(self._compare))

            # 优化速度，第二种类型不需要查询验收任务
            is_get_all_branch = second_querydict or improve_exclude
            if is_get_all_branch:
                return {"improve_task": misstaskimprove_res, "accept_task": []}

            # 查询验收任务
            misstaskacceptrecord_res = self.__get_misstaskacceptrecord_res(misstask_id, dts_no)

            return {"improve_task": misstaskimprove_res, "accept_task": misstaskacceptrecord_res}

        def _get_all_by_task_info(self):
            data = Schema({
                "task_type": And(str),
                "project": And(str),
                "querydict": And(dict),
            }, ignore_extra_keys=True).validate(self.request.data)

            page, limit = 1, sys.maxsize  # 不要分页

            task_type = data.get("task_type")
            project = data.get("project")

            second_querydict = data.get("querydict")

            # 查询条件
            querydict = {"misstask__task_type": task_type, }
            if task_type == MissTaskModel.TASK_TYPES.xw:
                querydict["misstask__project"] = project
            else:
                querydict["version"] = project
            objs, limit, page = get_miss_objs(limit, page, querydict, NewMissTaskDetail)
            total, instances, page = do_paginator.get_paginator_dict(objs, limit, page)

            res = []
            for inst in instances:
                item = self._get_one(inst.misstask_id, inst.dts_no,
                                     second_querydict=copy.deepcopy(second_querydict),
                                     improve_exclude={"improvement": MissTaskImprove.IMPROVEMENT_NA})
                for e in item.get("improve_task", []):
                    res.append(e)

            return Response({
                "code": 1000,
                "msg": '查询逆向改进问题列表成功',
                "data": res,
                "pagination": {"total": len(res)}
            }, status.HTTP_200_OK)

        def get_improvement_and_acceptance_tasks(self):
            """ 获得改进任务和验收任务 """
            if self.request.data.get("interface_type") == 2:
                try:
                    return self._get_all_by_task_info()
                except SchemaError as e:
                    return global_error_response(msg=f"获得改进任务和验收任务失败，原因：{e}")
                except Exception as e:
                    return ns_utils.unexpected_error_occurred(e, where="获得改进任务和验收任务")

            try:
                # 获得改进任务和验收任务
                _id, dts_no = self.request.data.get("id"), self.request.data.get("dts_no")
                detail_obj = NewMissTaskDetail.objects.get(pk=_id)
                is_analyze_finish = detail_obj.analyze_status == NewMissTaskDetail.AnalyzeStatusEnum.FINISH.value
                is_confirmed = detail_obj.confirmed_status == NewMissTaskDetail.ConfirmedStatusEnum.CONFIRMED.value
                if is_analyze_finish and not is_confirmed:
                    status_cn = NewMissTaskDetail.ConfirmedStatusEnum.to_mapping().get(detail_obj.confirmed_status)
                    return global_error_response(data={
                        "accept_task": [],
                        "improve_task": [],
                    }, msg=f"当前记录是{status_cn}状态，不允许操作！")
                return global_success_response(data=self._get_one(detail_obj.misstask_id, dts_no))
            except Exception as e:
                return ns_utils.unexpected_error_occurred(e, where="获得改进任务和验收任务")

    @audit_to_local
    def improve_and_accept(self, request):
        return self.ImproveAndAccept(self, request).get_improvement_and_acceptance_tasks()

    @decorator_refactored
    @audit_to_local
    def export_it_icsl_misstask2(self, request):
        # 创建这个新类的一个新对象，而后调用其中的 apply() 方法
        return MissTaskViewSetExportIcslMisstask(self, request).apply()

    @audit_to_local
    @check_admin_role
    def update_confirmed_status_of_miss_task_detail(self, request):
        """更新逆向改进详情分析表的确认状态字段"""
        this = self

        def unexpected_exception_handler(exception, data_var=None):
            logger.error(traceback.format_exc())
            return global_error_response(data=data_var, msg=f"出乎意料的异常发生：{exception}")

        try:
            schema_obj = Schema({
                "id": And(Use(str), error="参数 id 必须是能够强制转换为 str 的类型"),
                "confirmed_status": And(Use(str), error="参数 confirmed_status 必须是能够强制转换为 str 的类型")
            })
            data = schema_obj.validate(request.data)
            id_var, confirmed_status = data.get("id"), data.get("confirmed_status")
            NewMissTaskDetail.objects.filter(pk=id_var).update(confirmed_status=confirmed_status)
            # 在浏览器看不是字符串呀？为什么我打印出来确实是字符串类型？
            if int(confirmed_status) == NewMissTaskDetail.ConfirmedStatusEnum.CONFIRMED.value:
                inst = NewMissTaskDetail.objects.get(pk=id_var)
                user_list = ast.literal_eval(inst.reform_executor)
                context = {
                    "dts_no": inst.dts_no
                }
                NotificationManager.get_instance().notify_when_analysis_completed_and_confirmed(user_list, context)

            return global_success_response(msg=f"更新成功")
        except SchemaError as e:
            logger.error(traceback.format_exc())
            return global_error_response(msg=f"参数错误，原因：{e}")
        except Exception as e:
            return unexpected_exception_handler(e)

    @audit_to_local
    def import_review_minute_file(self, request):
        """导入评审纪要文件"""
        try:
            Schema({
                "id": And(str, error="id 必须是 str 类型"),
                Optional("filetype"): And(str),
            }, ignore_extra_keys=True).validate(request.data.dict())
            detail_id = request.data.get("id")
            task_detail_obj = NewMissTaskDetail.objects.get(id=detail_id)
            misstask_id = task_detail_obj.misstask.id

            creator = request.user_data.get("fullname", [])
            filetype = request.data.get("filetype")

            file_obj = request.FILES.get("file")
            filename = file_obj.name

            fdfs_obj = FdfsClient()
            fileid = fdfs_obj.upload_by_buffer(file_obj)

            file_data = {
                "file_type": filetype,
                "fileid": fileid,
                "filename": filename,
                "author": creator,
                "misstask_id": misstask_id
            }
            miss_task_file_obj = MissTaskFile.objects.create(**file_data)
            task_detail_obj.review_minute_file = miss_task_file_obj
            task_detail_obj.save()
            return global_success_response(data=MissFileSerializer(miss_task_file_obj).data, msg="上传评审纪要成功！")
        except SchemaError as e:
            return global_error_response(msg=f"参数错误，原因：{e}")
        except Exception as e:
            logger.error(traceback.format_exc())
            return global_success_response(msg=f"上传评审纪要失败，原因：{e}")
