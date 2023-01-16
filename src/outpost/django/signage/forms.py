from django import forms
from django.contrib.postgres.forms import DateTimeRangeField
from django.contrib.admin.widgets import AdminSplitDateTime
from django.contrib.postgres.forms.ranges import DateTimeRangeField, RangeWidget

from . import models


class SplitDateTimeRangeField(DateTimeRangeField):
    base_field = forms.SplitDateTimeField


class ScheduleItemAdminForm(forms.ModelForm):
    range = SplitDateTimeRangeField(widget=RangeWidget(AdminSplitDateTime()))

    class Meta:
        model = models.ScheduleItem
        fields = "__all__"
