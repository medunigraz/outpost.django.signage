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


class ScheduleItemAdminInlineFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()

        def overlap(x1, x2, y1, y2):
            return max(x1, y1) <= min(x2, y2)

        def recurrences(r, start, stop):
            return set(
                [
                    t.date()
                    for t in r.between(
                        start,
                        stop,
                        inc=True,
                        dtstart=datetime.combine(
                            start.date(), time(), tzinfo=start.tzinfo
                        ),
                    )
                ]
            )

        for a, b in combinations(filter(lambda f: f.has_changed(), self.forms), 2):
            if not overlap(
                a.instance.range.lower,
                a.instance.range.upper,
                b.instance.range.lower,
                b.instance.range.upper,
            ):
                continue
            if not overlap(
                a.instance.start, a.instance.stop, b.instance.start, b.instance.stop
            ):
                continue
            start = max(a.instance.range.lower, b.instance.range.lower)
            stop = min(a.instance.range.upper, b.instance.range.upper)
            if recurrences(a.instance.recurrences, start, stop) & recurrences(
                b.instance.recurrences, start, stop
            ):
                a.add_error(
                    None,
                    _("{scheduleitem} would overlap").format(scheduleitem=b.instance),
                )
