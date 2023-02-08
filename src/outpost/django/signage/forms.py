from datetime import (
    datetime,
    time,
)
from itertools import combinations

from django import forms
from django.contrib.admin.widgets import AdminSplitDateTime
from django.contrib.postgres.forms import DateTimeRangeField
from django.contrib.postgres.forms.ranges import (
    DateTimeRangeField,
    RangeWidget,
)
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from . import models


class SplitDateTimeRangeField(DateTimeRangeField):
    base_field = forms.SplitDateTimeField


class ScheduleItemAdminForm(forms.ModelForm):
    range = SplitDateTimeRangeField(widget=RangeWidget(AdminSplitDateTime()))

    class Meta:
        model = models.ScheduleItem
        fields = "__all__"
