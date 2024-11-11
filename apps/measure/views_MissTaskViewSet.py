class MissTaskViewSet(OldMissTaskViewSet):
    """ 逆向改进管理页的接口--原漏测管理 create_time: 2022.10 """

    def _get_control_points_constants(self, request: Request):
        """
        逆向改进管理-最佳控制点下拉框返回值
        """
        this = self
        try:
            cleaned_data = Schema({
                "task_type": object
            }, ignore_extra_keys=True).validate({k: v for k, v in request.query_params.items()})
            logger.info("%s", f"{cleaned_data}")

            task_type = cleaned_data.get("task_type")
            if task_type == MissTaskModel.TASK_TYPES.sj:
                data = constants.SJ_EXCEL_DATA_VALIDATION_FORMULA_OF_CONTROL_POINT
            elif task_type == MissTaskModel.TASK_TYPES.xw:
                data = constants.XW_EXCEL_DATA_VALIDATION_FORMULA_OF_CONTROL_POINT
            else:
                raise ValueError(f"task_type的值错误，{task_type}")

            return global_success_response(data=ast.literal_eval(data).split(','), msg="查询最佳控制点成功")

        except SchemaError as e:
            return global_error_response(msg=f"查询最佳控制点发生错误，原因是：{e}")
        except ValueError as e:
            return global_error_response(msg=f"查询最佳控制点发生错误，原因是：{e}")
        except Exception as e:
            logger.error("%s", f"{e}\n{traceback.format_exc()}")
            return global_error_response(msg=f"查询最佳控制点发生错误")

    def get_constants(self, request: Request):
        return self._get_control_points_constants(request)

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

    def export_improvements_under_same_task(self, request: Request):
        """ 导出任务信息 tab 页的改进措施列表 """
        try:
            exported_data: t.List[t.Dict] = self.ImproveAndAccept(self, request).get_all_by_task_info()
            # SimpleNamespace ns 可以类似 ns.dts_no 的方式访问数据，这样的话方便太多了！
            sio = export_improvements_under_same_task_sio([SimpleNamespace(**e) for e in exported_data])
            today = timezone.now()
            response = HttpResponse(content_type="application/vnd.ms-excel")
            response["Content-Disposition"] = (f"attachment;filename="
                                               f"improvements_under_same_task_{today.strftime('%Y%m%d%H%M%S')}.xlsx")
            response["Access-Control-Expose-Headers"] = "Content-Disposition"
            response.write(sio.getvalue())
            return response
        except Exception as e:
            logger.error("%s", f"{e}\n{traceback.format_exc()}")
            return ns_utils.unexpected_error_occurred(e, "导出任务信息 tab 页的改进措施列表")

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
                **required_fields_schema, **optional_fields_schema,
                **improvement_fields_related_schema, **improvement_fields_when_related_schema,
            }, ignore_extra_keys=True)
            detail_data = detail_schema_obj.validate(self.request.data)
            for e in keys_to_be_removed:
                detail_data.pop(e, None)

            # 修 BUG：技术根因和流程/管理根因不涉及时，填充不涉及
            if not detail_data.get("technical_reason_related"):
                detail_data["technical_reason"] = MissTaskImprove.IMPROVEMENT_NA
            if not detail_data.get("process_manage_reason_related"):
                detail_data["process_manage_reason"] = MissTaskImprove.IMPROVEMENT_NA

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
                    # 加这个校验的原因是：此处逻辑是重构而不是重写... 遗留代码用的是 first()，当时我也困惑。
                    validate_assumption(improve_qs.count() < 2, "查询到了两条相同的改进措施，请联系负责人。")

                    # 如果之前是涉及，但是现在不涉及，则删掉
                    if getattr(self.misstaskdetail_obj, related_var_name) and not related:
                        improve_qs.delete()

                    unique_filter_data = dict(
                        misstask_id=misstask_id,
                        improvement_type=getattr(CnVar, var_name),
                        dts_no=[dts_no],
                        YN_delete=0,
                    )
                    # 如果不存在，即第一次提交，则创建。否则在原来的基础上更新
                    if not improve_qs.exists():
                        MissTaskImprove.objects.create(**dict(
                            **unique_filter_data,
                            improvement=improvement,
                            reform_executor=executors.get_value().get(get_executor_name(var_name)),
                            update_by=self.request.user_data.get("fullname"),
                        ))
                    else:
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
                try:
                    # 成功后需要刷一下数据，此处模拟一下
                    url = f"http://127.0.0.1:8000/measure/miss/reset_analyzing/{self.request.data.get('id')}/"
                    response = requests.post(url, data=None, headers={
                        "Authorization": self.request.META.get("HTTP_AUTHORIZATION")
                    }, verify=False, timeout=5)
                    logger.info("%s", f"response: {response}")
                except Exception as e:
                    logger.error("%s", f"{e}\n{traceback.format_exc()}")

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
                logger.error("%s", f"{e}\n{traceback.format_exc()}")
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
                "control_point": inst.control_point,
                "description": inst.description,
                "dts_no": inst.dts_no,
                "id": inst.id,
                "level": inst.level,
                "task_type": inst.misstask.task_type,
                "yn_common": inst.yn_common,
            }
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

        def __init__(self, request: Request):
            self.request = request
            self.validator = CreateMissTaskDetailInstanceValidator
            # 注意，在这里执行逻辑是错的，这里崩溃了就是 500 了。。。
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
            # #(C)!: error_msgs = collections.namedtuple("error_msgs", ("task_type",))(**dict(
            # #(C)!:      task_type=f"{MissTaskModel.get_verbose_name('task_type')} 为必填字符串"
            # #(C)!:  ))
            # #(C)!:
            # #(C)!:  res = Schema({
            # #(C)!:      "task_type": And(str, error=error_msgs.task_type),
            # #(C)!:      Optional("file"): And(dict),
            # #(C)!:      Optional("_local_filepath"): And(str),
            # #(C)!:  }, ignore_extra_keys=True).validate(self.request.data)
            # 2024-10-21：之所以注释掉，是因为 beat.py 文件中的 _create 函数中发送请求的时候，校验会提示：
            #             1、Exception Type: AttributeError at /measure/misstask/
            #             2、Exception Value: This QueryDict instance is immutable

            res = self.request.data
            return res

        def create_one(self, reversed_header: t.Dict[int, t.Any], row_data: t.List[t.Any], file_info=None):
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

                # 2024-10-16：将 file_id 存入数据库
                misstaskfile_id = None
                if file_info:
                    file_info["misstask"] = misstask_obj
                    misstaskfile_id = MissTaskFile.objects.create(**file_info)

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
                    "misstask": misstask_obj,
                    "improvement_problem_file": misstaskfile_id
                })
                # 注意，detail_data 的数据还需要处理，比如：是否重犯数据库存的是 bool，而 excel 中是中文
                detail_data = self._process_detail_data(detail_data)
                NewMissTaskDetail.objects.create(**detail_data)  # create 时 misstask 存的 instance，update 时是 id

                # #(C)!: logger.info("%s", f"{pprint.pformat(detail_data)}")

        def _sj_get_auto_filled_field_values(self, detail_data, initial=None):
            this = self
            auto_filled_field_values = initial if initial else {}

            dts_no = detail_data.get("dts_no")

            auto_filled_fields_mapping = (
                # 问题描述、问题时间、级别
                ("description", "sBriefDescription"), ("dts_create_time", "createAt"), ("level", "serverityNoName"),
                # 类型、问题来源、版本、应用、部门
                ("problem_type", None), ("dts_come", None),
                ("version", None), ("service", None), ("subproduct", None), ("product", None),
            )

            for dts_detail_data in QueryDTSDetailControl().get_dts_detail([dts_no], extra_fields=[
                "prodInfo", "sBriefDescription",  # 简要描述
            ]):
                logger.info("%s", f"{pprint.pformat(dts_detail_data)}")
                for value in auto_filled_fields_mapping:
                    k_name, v_name = value[0], value[1]
                    # v_name 不存在时，需要特别处理，单纯的 if else 语义并不明了
                    if v_name and not detail_data.get(k_name):
                        auto_filled_field_values[k_name] = dts_detail_data.get(v_name)

                # 【2024-09-25】
                # 类型：从简要描述中筛出来，类型是第三个【】内的内容
                if not detail_data.get("problem_type"):
                    brief_desc = dts_detail_data.get("sBriefDescription")
                    problem_type_mapping = [
                        ("A1", "红线A1"), ("A2", "红线A2"), ("B类", "红线B类"),
                        ("TOPN", "TOPN类"), ("隐私", "隐私基线"),
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
                    "product": "sProdXdtNoName", "service": "sServiceName",
                    "version": "sServiceVerName", "subproduct": "sProdNoName",
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

                    if not detail_data.get("problem_type"):
                        # 2024-10-21：作战平台说，漏洞桌面全是安全漏洞类
                        auto_filled_field_values["problem_type"] = "漏洞类"
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

        def _generate_analyze_executor(self, detail_data, filter_data_of_analyze_executor):

            # 分析责任人、验收负责人需要单独处理，验收责任人暂且不处理，因为涉及的代码分布过于零散，需要时间（2024-09-19）
            # 1. 至少能够将英文工号转为中文工号
            # 2. 如果没有填写，则自动去数据库查询（实现这个功能的前提是部门的值不为空）
            analyze_executor = detail_data.get("analyze_executor")
            if not analyze_executor:
                # 2024-10-12：需要注意的是，测试环境这两张表很多信息没有，所以导入的时候必须填写分析责任人。
                def _get_approver_in_gyapprovemanager():
                    try:
                        approver = GYApproveManager.objects.get(**filter_data_of_analyze_executor).approver
                        logger.info("%s", f"approver: {approver}")
                        return str(approver)
                    except GYApproveManager.DoesNotExist:
                        pass
                    except Exception as e:
                        logger.error("%s", f"{e}\n{traceback.format_exc()}")
                    return None

                if self.is_sj:
                    # 直接查送检表
                    analyze_executor = _get_approver_in_gyapprovemanager()
                elif self.is_xw:
                    # 按顺序去查找质量红线、送检表中的项目经理
                    try:
                        analyze_executor = (RLTaskApproveManager.objects
                                            .get(**filter_data_of_analyze_executor)
                                            .get_info.get("approver").get("fullname"))
                    except RLTaskApproveManager.DoesNotExist:
                        analyze_executor = _get_approver_in_gyapprovemanager()
                    except RLTaskApproveManager.MultipleObjectsReturned:
                        pass
                    except Exception as e:
                        logger.error("%s", f"{e}\n{traceback.format_exc()}")

            # #(C)!: if not analyze_executor:
            # #(C)!:     raise CustomException(f"自动填充分析责任人字段失败，问题单号 {dts_no} 这条记录需要手动填写分析责任人")

            # 这个必不可少！
            if analyze_executor and not self.chinese_character_exists(analyze_executor):
                analyze_executor = get_cn_name(analyze_executor)

            return analyze_executor

        def _process_detail_data(self, detail_data: t.Dict) -> t.Dict:
            this = self

            auto_filled_field_values = self._get_auto_filled_field_values(detail_data)

            filter_data_of_analyze_executor = {}
            for name in ["product", "subproduct", "service"]:
                filter_data_of_analyze_executor[name] = detail_data.get(name)
                if not detail_data.get(name):
                    filter_data_of_analyze_executor[name] = auto_filled_field_values.get(name)
            logger.info("%s", f"filter_data: {filter_data_of_analyze_executor}")

            # 2024-09-25：此处是特别处理（修 BUG 的），将 _related 添加进来
            for name in self.improvement_measures:
                if detail_data.get(name):
                    detail_data[name + "_related"] = True

            for name in ["technical_reason", "process_manage_reason"]:
                if detail_data.get(name):
                    detail_data[name + "_related"] = True

            # 任务信息要注意，目前 ICSL 送检用的是 version、现网用的是 MissTaskModel 里的 project

            # 分析责任人、验收负责人需要单独处理，验收责任人暂且不处理，因为涉及的代码分布过于零散，需要时间（2024-09-19）
            analyze_executor = self._generate_analyze_executor(detail_data, filter_data_of_analyze_executor)

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
                local_filepath = request.data.get("_local_filepath")
                if not local_filepath:
                    file_info = request.data.get("file")
                    file_id = file_info.get("file_id")
                    file_name = file_info.get("file_name")
                    unique_file_name = str(uuid.uuid4()) + os.path.splitext(file_name)[1]
                    temporary_file_path = os.path.join(settings.TEMPORARY, unique_file_name)

                    fdfs_client = FdfsClient()
                    fdfs_client.download_to_file(temporary_file_path, file_id)
                else:
                    logger.info("%s", f"local_filepath: {local_filepath}")
                    temporary_file_path = local_filepath
                    file_id = None
                    file_name = None

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
                        # #(C)!: error_msgs.append(f"第 {cnt} 行的问题单号为空，该行数据创建失败\n")
                        # #(C)!: continue
                        raise CustomException(f"第 {cnt} 行的问题单号为空，该行数据创建失败")

                    # 注意，问题单号是 unique 的，应用层过滤一下
                    if NewMissTaskDetail.objects.filter(dts_no=dts_no).exists():
                        # #(C)!: error_msgs.append(f"问题单号为 {dts_no} 的记录已经存在，请勿重复创建\n")
                        # #(C)!: continue
                        raise CustomException(f"问题单号为 {dts_no} 的记录已经存在，请勿重复创建")

                    self.create_one(reversed_header, row, file_info=dict(
                        fileid=file_id,
                        filename=file_name,
                        upload_time=timezone.now(),
                        author=self.request.user_data.get("fullname"),
                        create_time=timezone.now(),
                    ))

                reader.close_workbook()
                msg = "新建成功！"
                # #(C)!: if error_msgs:
                # #(C)!:     msg += "\n" + "".join(error_msgs)
                return global_success_response(msg=msg)
            except CustomException as e:
                return global_error_response(msg=f"逆向改进的新建功能发生错误，原因：{e}")
            except Exception as e:
                return ns_utils.unexpected_error_occurred(e, where="逆向改进的新建功能")

    @audit_to_local
    def create(self, request, *args, **kwargs):
        # 2024-10-16：此处实例化不需要第一个参数了，最主要的原因是 CreateMissTaskDetailInstance 类我需要在 beat 文件中使用了
        return self.CreateMissTaskDetailInstance(request).create_misstaskdetail_instance()

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

        def _get_merged_displayed_data(self):
            # 2024-10-29：US20240920565291，该需求存在问题，不必实现了。
            res = []
            improve_tasks = self.get_all_by_task_info()

            mapping = {}
            common_fields = ("reform_executor", "improvement_type", "improvement",)
            for improve_task_item in improve_tasks:
                key = tuple([improve_task_item.get(e) for e in common_fields])
                mapping.setdefault(key, [])
                mapping.get(key).append(improve_task_item)

            for improve_task_items in mapping.values():
                dts_no_list = [e.get("dts_no")[0] for e in improve_task_items]
                first_improve_task_item = improve_task_items[0]
                first_improve_task_item["dts_no"] = [", ".join(dts_no_list)]
                res.append(first_improve_task_item)

            return res

        def get_all_by_task_info(self, data_merged_display=False):
            if data_merged_display:
                return self._get_merged_displayed_data()

            # 2024-10-15：这个命名也不算合适，因为这里还有 querydict 字段！筛选功能也支持呢！
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

            return res

        def apply(self):
            """ 获得改进任务和验收任务 """
            if self.request.data.get("interface_type") == 2:
                try:
                    # 2024-10-29：暂时的需求
                    res = self.get_all_by_task_info()
                    return Response({
                        "code": 1000,
                        "msg": '查询逆向改进问题列表成功',
                        "data": res,
                        "pagination": {"total": len(res)}
                    }, status.HTTP_200_OK)
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
        return self.ImproveAndAccept(self, request).apply()

    @decorator_refactored
    @audit_to_local
    def export_it_icsl_misstask2(self, request):
        # 创建这个新类的一个新对象，而后调用其中的 apply() 方法
        return MissTaskViewSetExportIcslMisstask(self, request).apply()

    @audit_to_local
    @check_admin_role
    def update_confirmed_status_of_miss_task_detail(self, request):
        """ 更新逆向改进详情分析表的确认状态字段 """
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
                # 这个要改成仅涉及的人才行
                inst = NewMissTaskDetail.objects.get(pk=id_var)
                improve_qs = (MissTaskImprove
                              .get_queryset_by(inst.misstask_id, inst.dts_no)
                              .exclude(improvement=MissTaskImprove.IMPROVEMENT_NA))
                user_list = [e.reform_executor for e in improve_qs if e.reform_executor]
                context = {
                    "control_point": inst.control_point,
                    "description": inst.description,
                    "dts_no": inst.dts_no,
                    "id": inst.id,
                    "level": inst.level,
                    "task_type": inst.misstask.task_type,
                    "yn_common": inst.yn_common,
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
