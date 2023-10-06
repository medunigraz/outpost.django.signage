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
    PDF_RENDER_MIN_WIDTH = 3840
    PDF_RENDER_MIN_HEIGHT = 2160
    PDF_RENDER_FORMAT = "webp"
    PDF_RENDER_QUALITY = 70

    class Meta:
        prefix = "signage"
