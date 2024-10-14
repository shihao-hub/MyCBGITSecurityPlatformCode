from django.forms.models import ModelForm
from measure.models import MissTaskOverallTop, MissTaskModel, NewMissTaskDetail, MissTaskImprove


class BaseMixin:
    @staticmethod
    def get_processed_form_errors(form):
        return form.errors.as_json().encode("utf-8").decode("unicode_escape")

    def validate_non_empty_fields_and_return(self, name):
        value = self.cleaned_data.get(name)  # NOQA
        if value is None:
            raise RuntimeError(f"表单中的 {name} 字段不允许为空")
        return value


class MissTaskOverallTopForm(BaseMixin, ModelForm):
    class Meta:
        model = MissTaskOverallTop
        fields = "__all__"

    # schema 库简单又好用！


class MissTaskModelForm(BaseMixin, ModelForm):
    class Meta:
        model = MissTaskModel
        fields = "__all__"


class MissTaskImproveForm(BaseMixin, ModelForm):
    class Meta:
        model = MissTaskImprove
        fields = "__all__"

    # 由于 MissTaskImprove 表中滥用 blank 和 null，因此我将在 Form 中添加限制

    # #(C)!: def clean_dts_no(self):
    # #(C)!:     return self.validate_non_empty_fields_and_return("dts_no")


class NewMissTaskDetailForm(BaseMixin, ModelForm):
    class Meta:
        model = NewMissTaskDetail
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        return cleaned_data
