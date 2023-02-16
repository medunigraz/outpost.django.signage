import logging
from datetime import timedelta

import isodate
from celery import shared_task
from django.utils import timezone

from . import models

logger = logging.getLogger(__name__)


class ScheduleTask:
    @shared_task(bind=True, ignore_result=True, name=f"{__name__}.Schedule:cleanup")
    def cleanup(task, interval: str) -> None:
        threshold = timezone.now() - isodate.parse_duration(interval)
        for si in models.ScheduleItem.objects.exclude(range__endswith=None).filter(
            range__fully_lt=threshold
        ):
            si.delete()
