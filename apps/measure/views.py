class AnalyzingUserViewSet(OldAnalyzingUserViewSet):
    ANALYSIS_PAGE_KEY_PREFIX = "measure_analysis_page_editing:"
    ANALYSIS_PAGE_EMPIRE_TIME = 300

    @classmethod
    def generate_cache_key(cls, unique_id):
        return f"{cls.ANALYSIS_PAGE_KEY_PREFIX}{unique_id}"

    @classmethod
    def set_cache_by(cls, key, value, expired_time=None):
        expired_time = expired_time if expired_time else cls.ANALYSIS_PAGE_EMPIRE_TIME
        cache.set(key, value, expired_time)

    @classmethod
    def get_cache_by(cls, key):
        return cache.get(key)

    @classmethod
    def delete_cache_by(cls, key):
        cache.delete(key)

    def _check_current_user_or_set_to_cache(self, request, pk=None):
        user_data = request.user_data
        analyzing_by = self.get_cache_by(self.generate_cache_key(pk))
        if analyzing_by and analyzing_by != user_data.get("fullname"):
            return global_success_response(data=dict(allow_analyze=False, analyzing_by=analyzing_by),
                                           msg="{}正在编辑".format(analyzing_by))
        else:
            self.set_cache_by(self.generate_cache_key(pk), user_data.get("fullname"))
            return global_success_response(data=dict(allow_analyze=True))

    def get_analyzing(self, request, pk=None):
        """ 获取当前分析中用户 """
        return self._check_current_user_or_set_to_cache(request, pk)

    def reset_analyzing(self, request, pk=None):
        """ 重置分析中用户 """
        user_data = request.user_data
        analyzing_by = self.get_cache_by(self.generate_cache_key(pk))
        msg = ""
        if user_data.get("fullname") == analyzing_by:
            msg = f"重置分析中的用户成功，被重置用户：{analyzing_by}"
            cache.delete(self.generate_cache_key(pk))
        return global_success_response(msg=msg)


class PersonalMissTaskViewSet(OldPersonalMissTaskViewSet):
    # 2024-10-15：此处有两个 bug，懒得修复了，直接重构或重写。

    class CountAll:
        @staticmethod
        def get_condition_of_to_be_analyzed(login_person) -> t.Tuple[t.List, t.Dict]:
            return [], dict(
                analyze_executor=login_person,
                analyze_status=0
            )

        @staticmethod
        def get_condition_of_to_be_improved(login_person) -> t.Tuple[t.List, t.Dict]:
            # 涉及、登录人是责任人、闭环状态为打开、未被软删除
            return [
                ~Q(improvement="不涉及")
            ], dict(
                reform_executor=login_person,
                close_status=MissTaskImprove.CloseStatus.OPEN,
                YN_delete=0
            )

        @staticmethod
        def get_condition_of_to_be_improved_closed(login_person) -> t.Tuple[t.List, t.Dict]:
            # 涉及、登录人是责任人、闭环状态为关闭、未被软删除
            return [
                ~Q(improvement="不涉及")
            ], dict(
                reform_executor=login_person,
                close_status=MissTaskImprove.CloseStatus.CLOSE,
                YN_delete=0
            )

        @staticmethod
        def get_condition_of_to_be_accepted() -> t.Tuple[t.List, t.Dict]:
            # 涉及、闭环状态为关闭、是待验收状态、未被软删除
            return [
                ~Q(improvement="不涉及")
            ], dict(
                close_status=MissTaskImprove.CloseStatus.CLOSE,
                acceptance_status=MissTaskImprove.AcceptanceStatusEnum.TO_BE_ACCEPT.value,
                YN_delete=0
            )

        @classmethod
        def get_to_be_analyzed_misstaskdetail_qs(cls, login_person):
            condition = cls.get_condition_of_to_be_analyzed(login_person)
            return NewMissTaskDetail.objects.filter(*condition[0], **condition[1])

        @classmethod
        def get_to_be_improved_misstaskimprove_qs(cls, login_person):
            condition = cls.get_condition_of_to_be_improved(login_person)
            return MissTaskImprove.objects.filter(*condition[0], **condition[1])

        @classmethod
        def get_to_be_improved_closed_misstaskimprove_qs(cls, login_person):
            condition = cls.get_condition_of_to_be_improved_closed(login_person)
            return MissTaskImprove.objects.filter(*condition[0], **condition[1])

        @classmethod
        def get_to_be_accepted_misstaskimprove_qs(cls):
            condition = cls.get_condition_of_to_be_accepted()
            return MissTaskImprove.objects.filter(*condition[0], **condition[1])

        def __init__(self, request: Request):
            self.request = request

        def count_all(self):
            # 统计首先我的待办的 待分析任务数量、待改进任务数量、待验收任务数量，注意，是任务数量！不是改进措施的数量。
            try:
                login_person = self.request.user_data.get("fullname")

                # 待改进：通过改进措施筛选出任务的数量，注意一个任务旗下可能有多条改进措施
                to_be_improved_tasks_set = set()
                for obj in self.get_to_be_improved_misstaskimprove_qs(login_person):
                    # 2024-10-17：假设 dts_no 和 misstask_id 可以唯一确认一个任务，当然前提是不存在重复任务。
                    task_key = f"{obj.dts_no[0]}-{obj.misstask_id}"
                    if task_key not in to_be_improved_tasks_set:
                        to_be_improved_tasks_set.add(task_key)
                to_be_improved_count = len(to_be_improved_tasks_set)

                # 待验收：通过改进措施筛选出任务的数量，注意改进措施中没有存验收人，验收人在任务中存储的...
                to_be_accepted_misstaskimprove_qs = self.get_to_be_accepted_misstaskimprove_qs()
                logger.info("%s", f"to_be_accepted_misstaskimprove_qs: {len(to_be_accepted_misstaskimprove_qs)}")

                to_be_accepted_count = 0
                to_be_accepted_tasks_set = set()
                # 出现了 N+1 问题
                for obj in to_be_accepted_misstaskimprove_qs:
                    task_key = f"{obj.dts_no[0]}-{obj.misstask_id}"
                    if task_key not in to_be_accepted_tasks_set:
                        to_be_accepted_tasks_set.add(task_key)
                        detail_obj = obj.get_misstaskdetail_obj(only=["analyze_executor"])
                        if detail_obj.analyze_executor == login_person:
                            to_be_accepted_count += 1

                return global_success_response(data={
                    "wait_analyze_count": self.get_to_be_analyzed_misstaskdetail_qs(login_person).count(),
                    "wait_improve_count": to_be_improved_count,
                    "wait_accept_count": to_be_accepted_count
                }, msg="统计逆向改进待分析、待改进、待验收数量成功")
            except Exception as e:
                logger.error("查询失败，原因：{}".format(traceback.format_exc()))
                return ns_utils.unexpected_error_occurred(e, "统计逆向改进待分析、待改进、待验收数量失败")

    def _common_process_query_dict(self, querydict):
        this = self
        if querydict.get("dts_no") is not None:
            querydict["dts_no__icontains"] = querydict.pop("dts_no")
        if querydict.get("description") is not None:
            querydict["description__icontains"] = querydict.pop("description")
        if querydict.get("level") is not None:
            querydict["level__in"] = querydict.pop("level")
        if querydict.get("reform_executor") is not None:
            logger.info("%s", f'{querydict["reform_executor"]}')
            querydict["reform_executor__icontains"] = get_cn_name(querydict.pop("reform_executor")[0])
            logger.info("%s", f'{querydict["reform_executor__icontains"]}')
        return querydict

    def person_analyze(self, request):
        """ 个人待办 - 待分析 """
        this = self

        def process_query_dict(_querydict):
            _querydict = self._common_process_query_dict(_querydict)
            return _querydict

        try:
            # 2024-10-16：10 条任务，需要 729 ms，序列化耗时的吗？
            limit, page, querydict, order = get_request_parms(request)
            querydict = process_query_dict(querydict)
            querydict.update(self.CountAll.get_condition_of_to_be_analyzed(request.user_data.get("fullname"))[1])
            total, data, page = get_miss_list(limit, page, querydict, NewMissTaskDetail, order=order)
            serializer = NewMissTaskDetailserializer(data,
                                                     many=True,
                                                     context=new_miss_task_detail_serializer_context)
            result = {
                "code": 1000,
                "msg": '查询待分析逆向改进问题详情列表成功!',
                "data": serializer.data,
                "pagination": {
                    "total": total,
                    "page": page,
                },

            }
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("%s", f"{e}\n{traceback.format_exc()}")
            return ns_utils.unexpected_error_occurred(e)

    def _distinct_qs_by_dts_no_and_misstask_id(self, qs: t.List[MissTaskImprove]):
        """ 过滤 QuerySet """
        this = self
        res = []
        filter_set = set()
        for obj in qs:
            key = f"{obj.dts_no[0]}-{obj.misstask_id}"
            if key not in filter_set:
                filter_set.add(key)
                res.append(obj)
        return res

    def person_improve_lists(self, request):
        """ 个人待办 - 待改进 """

        def process_query_dict(_querydict):
            _querydict = self._common_process_query_dict(_querydict)
            return _querydict

        try:
            _, _, querydict, _ = get_request_parms(request)
            querydict = process_query_dict(querydict)

            qs = self.CountAll.get_to_be_improved_misstaskimprove_qs(request.user_data.get("fullname"))
            # 注意，distinct 函数的作用是去除重复改进措施，这样可以做到 improve 和 detail 能一一对应。
            to_be_improved_misstaskimprove_qs = self._distinct_qs_by_dts_no_and_misstask_id(qs)

            if settings.DEBUG:
                logger.info("%s", f"待改进的改进措施的个数为：{len(qs)}")
                logger.info("%s", f"待改进的去重改进措施的个数为：{len(to_be_improved_misstaskimprove_qs)}")

            res_objs = set()
            for improve_obj in to_be_improved_misstaskimprove_qs:
                detail_obj = improve_obj.get_misstaskdetail_obj(extra_filter_data=querydict)
                if detail_obj:
                    res_objs.add(detail_obj)

            serializer = NewMissTaskDetailserializer(res_objs,
                                                     many=True,
                                                     context=new_miss_task_detail_serializer_context)
            result = {
                "code": 1000,
                "msg": '查询逆向改进列表成功!',
                "data": serializer.data,
                "pagination": {
                    "total": len(res_objs),
                }
            }
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("%s", f"{e}\n{traceback.format_exc()}")
            return ns_utils.unexpected_error_occurred(e)

    def person_processed_lists(self, request):
        """ 个人待办 - 已处理 """
        def process_query_dict(_querydict):
            _querydict = self._common_process_query_dict(_querydict)
            return _querydict

        try:
            _, _, querydict, _ = get_request_parms(request)
            querydict = process_query_dict(querydict)

            qs = self.CountAll.get_to_be_improved_closed_misstaskimprove_qs(request.user_data.get("fullname"))
            # 注意，distinct 函数的作用是去除重复改进措施，这样可以做到 improve 和 detail 能一一对应。
            to_be_improved_misstaskimprove_qs = self._distinct_qs_by_dts_no_and_misstask_id(qs)

            if settings.DEBUG:
                logger.info("%s", f"已处理的改进措施的个数为：{len(qs)}")
                logger.info("%s", f"已处理的去重改进措施的个数为：{len(to_be_improved_misstaskimprove_qs)}")

            res_objs = set()
            for improve_obj in to_be_improved_misstaskimprove_qs:
                detail_obj = improve_obj.get_misstaskdetail_obj(extra_filter_data=querydict)
                if detail_obj:
                    res_objs.add(detail_obj)

            serializer = NewMissTaskDetailserializer(res_objs,
                                                     many=True,
                                                     context=new_miss_task_detail_serializer_context)
            result = {
                "code": 1000,
                "msg": '查询逆向改进列表成功!',
                "data": serializer.data,
                "pagination": {
                    "total": len(res_objs),
                }
            }
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("%s", f"{e}\n{traceback.format_exc()}")
            return ns_utils.unexpected_error_occurred(e)

    def person_accept_lists(self, request):
        """ 个人待办 - 待验收 """
        this = self
        acceptance_owner = "analyze_executor"

        def process_query_dict(_querydict):
            _querydict[acceptance_owner] = request.user_data.get("fullname")
            _querydict = self._common_process_query_dict(_querydict)
            return _querydict

        try:
            _, _, querydict, _ = get_request_parms(request)
            querydict = process_query_dict(querydict)

            qs = self.CountAll.get_to_be_accepted_misstaskimprove_qs()
            to_be_accepted_misstaskimprove_qs = self._distinct_qs_by_dts_no_and_misstask_id(qs)

            if settings.DEBUG:
                logger.info("%s", f"待验收的改进措施的个数为：{len(qs)}")
                logger.info("%s", f"待验收的去重改进措施的个数为：{len(to_be_accepted_misstaskimprove_qs)}")

            res_objs = set()
            for improve_obj in to_be_accepted_misstaskimprove_qs:
                detail_obj = improve_obj.get_misstaskdetail_obj(extra_filter_data=querydict)
                if detail_obj:
                    res_objs.add(detail_obj)

            serializer = NewMissTaskDetailserializer(res_objs,
                                                     many=True,
                                                     context=new_miss_task_detail_serializer_context)

            result = {
                "code": 1000,
                "msg": "查询逆向改进列表成功！",
                "data": serializer.data,
                "pagination": {
                    "total": len(res_objs),
                }
            }
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("%s", f"{e}\n{traceback.format_exc()}")
            return ns_utils.unexpected_error_occurred(e)


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
            return not str(_id).startswith("WARN")

        @staticmethod
        def is_desktop_vulnerability(_id: str):
            # 暂时这样判断
            return str(_id).startswith("WARN")

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
