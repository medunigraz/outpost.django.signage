from datetime import timedelta

from appconf import AppConf
from apscheduler.jobstores.memory import MemoryJobStore
from django.conf import settings


class SignageAppConf(AppConf):
    SCHEDULER_JOB_STORES = {
        "default": MemoryJobStore(),
    }
    SCHEDULER_START = "SIGNAGE_SCHEDULER_START"
    SCHEDULER_CHANNEL = "signage-scheduler"
    TYPO3_NEWS_RETROSPECTIVE = timedelta(days=365)
    TYPO3_EVENT_RETROSPECTIVE = timedelta(days=31)

    class Meta:
        prefix = "signage"
