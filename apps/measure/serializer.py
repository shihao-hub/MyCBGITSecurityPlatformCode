class NewMissTaskDetailserializer(ModelSerializer):
    detail_desc = serializers.SerializerMethodField()
    reform_executor = serializers.SerializerMethodField()
    dts_create_time = serializers.SerializerMethodField()
    accept_status = serializers.SerializerMethodField()
    improve_count = serializers.SerializerMethodField()
    accept_count = serializers.SerializerMethodField()
    improve_total_count = serializers.SerializerMethodField()
    accept_total_count = serializers.SerializerMethodField()
    misstaskreformexecutor = MissTaskReformExecutorSerializer()

    def __init__(self, *args, **kwargs):
        # Q: kwargs["context"] 放到此处不知为何会导致 to_representation 判断不生效...
        # 此处的代码也只是临时的
        kwargs["exclude_fields"] = ["detail_desc"]

        exclude_fields = kwargs.pop("exclude_fields", None)
        super().__init__(*args, **kwargs)
        if exclude_fields:
            for e in exclude_fields:
                self.fields.pop(e, None)

    class Meta:
        model = NewMissTaskDetail
        fields = (
            "id", "misstask_id", "dts_no", "description", "yn_common", "product", "subproduct", "service", "version",
            "control_point", "analyze_executor", "reform_executor", "detail_desc", "dts_come", "dts_class",
            "dts_subclass", "level", "problem_type", "technical_reason", "process_manage_reason",
            "improvement_situation", "security_architecture", "security_architecture_related", "secure_coding",
            "secure_coding_related", "secure_baseline", "secure_baseline_related", "case_baseline",
            "case_baseline_related", "open_source_governance", "open_source_governance_related", "auto",
            "auto_related", "security_measures", "security_measures_related", "security_tool", "repeated",
            "security_tool_related", "compliance_policies", "compliance_policies_related", "product_improve",
            "product_improve_related", "code_check", "code_check_related", "manage", "manage_related",
            "improvement_status", "acceptance_status", "analyze_status", "create_time", "update_time",
            'improve_count', 'accept_count', 'detail_desc', 'reform_executor', 'dts_create_time', 'accept_status',
            'improve_total_count', 'accept_total_count', "confirmed_status",
            "technical_reason_related", "process_manage_reason_related", "misstaskreformexecutor"
        )

    def _logic_of_first_engagement(self, instance):
        # 该函数是 2024-07 刚刚接手时加入的逻辑，暂且抽到此处吧，有时间再看看我之前这是在干嘛...
        if getattr(instance, "analyze_status", "") == 0:
            instance.improvement_status = "待改进"
            instance.acceptance_status = "待验收"
            instance.save()

        res = super().to_representation(instance)

        try:
            if instance.review_minute_file:
                res["review_minute_file"] = MissFileSerializer(instance.review_minute_file).data
            if instance.improvement_problem_file:
                res["improvement_problem_file"] = MissFileSerializer(instance.improvement_problem_file).data
        except Exception as e:
            logger.error("%s", f"{e} - detail_id: {instance.id}")

        context = getattr(self, "context", {})
        if not context.get("use_first_table_fields"):
            return res

        misstask = instance.misstask
        use_first_table_fields = context.get("use_first_table_fields")
        miss_task_dict = {}
        for e in use_first_table_fields:
            if hasattr(misstask, e):
                miss_task_dict[e] = getattr(misstask, e)
        res.update({"misstask": miss_task_dict})
        # 又打个补丁：为什么前端觉得 task_type 放在内层表里会麻烦？
        #   这样写代码以后怎么维护啊？
        res["task_type"] = res.get("misstask").get("task_type")
        return res

    def to_representation(self, instance):
        res = self._logic_of_first_engagement(instance)

        # 虽然不应该在查询的时候，修改状态，但是没办法了。
        # 2024-09-26：此处只需要执行一次的！而且即使出错了也可以忽略。
        if res.get("misstaskreformexecutor") is None:
            possible_error_msg = []
            try:
                data = {}
                for improve_inst in instance.get_misstaskimprove_queryset():
                    possible_error_msg.append(f"improve_inst.improvement_type: {improve_inst.improvement_type}")
                    data[get_executor_name_by_cn(improve_inst.improvement_type)] = improve_inst.reform_executor

                if data:
                    with transaction.atomic():
                        obj = MissTaskReformExecutor.objects.create(**data)
                        instance.misstaskreformexecutor = obj  # 2024-09-26：这里也只能存实例而不是 obj.id
                        instance.save()
                        logger.info("%s", f"NewMissTaskDetail {instance.id} 的 misstaskreformexecutor 创建成功！")
                        res["misstaskreformexecutor"] = data
            except Exception as e:
                msg = ("possible_error_msg: " + "，".join(possible_error_msg)) if possible_error_msg else ""
                logger.error("%s", f"{e} -> {msg}")

        return res

    def get_improve_count(self, obj):
        res = MissTaskImprove.objects.filter(~Q(improvement__exact="不涉及"), misstask_id=obj.misstask_id,
                                             dts_no__icontains=obj.dts_no, YN_delete=0,
                                             close_status="Open").count()
        return self.get_improve_total_count(obj) - res

    def get_accept_count(self, obj):
        res = MissTaskImprove.objects.filter(misstask_id=obj.misstask_id, dts_no__icontains=obj.dts_no, YN_delete=0,
                                             acceptance_status=0).count()
        return self.get_accept_total_count(obj) - res

    def get_detail_desc(self, obj):
        return obj.detail_desc.replace('src="', 'src="https://dts.huawei.com') if obj.detail_desc else ""

    def get_reform_executor(self, obj):
        return list(filter(None, ast.literal_eval(obj.reform_executor)))

    def get_dts_create_time(self, obj):
        return obj.dts_create_time if obj.dts_create_time else None

    def get_accept_status(self, obj):
        mti = MissTaskImprove.objects.filter(~Q(improvement="不涉及"),
                                             dts_no__icontains=obj.dts_no, YN_delete=0, misstask_id=obj.misstask_id)
        pass_query = mti.filter(acceptance_status=1)
        waiting_query = mti.filter(acceptance_status=0)
        no_need_query = mti.filter(acceptance_status__in=[2, 3])
        accept_status = "异常"
        if not mti and obj.misstask.task_type == "现网问题" and obj.analyze_status == 1:
            accept_status = "验收完成"
        elif not mti:
            accept_status = ""
        elif no_need_query and not pass_query and not waiting_query:
            accept_status = "待验收"
        elif not no_need_query and pass_query and not waiting_query:
            accept_status = "验收完成"
        elif not pass_query and waiting_query:
            accept_status = "验收中"
        elif pass_query and (no_need_query or waiting_query):
            accept_status = "部分已完成"
        if obj.acceptance_status != accept_status:
            obj.acceptance_status = accept_status
            obj.update_time = datetime.datetime.now()
            obj.save()
        try:
            judge_improve_status(obj.misstask_id, [obj.dts_no])
        except Exception as e:
            logger.error(f"misstask_id: {obj.misstask_id}, dts_no: {obj.dts_no} --- {e}")
            logger.error(traceback.format_exc())
        return accept_status

    def get_improve_total_count(self, obj):
        return MissTaskImprove.objects.filter(~Q(improvement__exact="不涉及"), misstask_id=obj.misstask_id,
                                              dts_no__icontains=obj.dts_no,
                                              YN_delete=0).count()

    def get_accept_total_count(self, obj):
        return MissTaskImprove.objects.filter(misstask_id=obj.misstask_id, dts_no__icontains=obj.dts_no, YN_delete=0,
                                              acceptance_status__in=[0, 1]).count()
