import asyncio
import inspect
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from asgiref.server import StatelessServer
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.routing import get_default_application
from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.utils import timezone

from ... import models
from ...conf import settings

logger = logging.getLogger(__name__)


class SignageServer(StatelessServer):
    def __init__(self, application, channel_layer, channel, max_applications=1000):
        super().__init__(application, max_applications)
        self.channel_layer = channel_layer
        if self.channel_layer is None:
            raise ValueError("Channel layer is not valid")
        self.channel = channel
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()
        self.jobs = dict()
        now = timezone.now()
        for s in models.Schedule.objects.all():
            dt = s.get_next_datetime(now)
            if not dt:
                logger.info(f"No more scheduled items for {s}")
                if s.pk in self.jobs:
                    del self.jobs[s.pk]
                continue
            logger.debug(f"Updating schedule {s} at {dt}")
            self.jobs[s.pk] = self.scheduler.add_job(
                self.update, "date", run_date=dt, kwargs={"schedule": s}
            )

    async def update(self, schedule):
        logger.debug(f"Updating schedule {schedule}")
        now = timezone.now()
        dt = schedule.get_next_datetime(now)
        if not dt:
            logger.info(f"No more events for {schedule}")
            return
        logger.debug(f"Next update for schedule {schedule} at {dt}")
        p = schedule.get_current(now)
        logger.debug(f"Starting playlist {p} from {schedule}")
        self.channel_layer.group_send(
            schedule.channel, {"type": "playlist.update", "playlist": p.pk}
        )
        self.jobs[schedule.pk] = self.scheduler.add_job(
            self.update, "date", run_date=dt, kwargs={"schedule": schedule}
        )

    async def handle(self):
        while True:
            message = await self.channel_layer.receive(self.channel)
            print(message)
            t = message.get("type", None)
            if not t:
                raise ValueError("Worker received message with no type.")

            h = getattr(self, f"handle_{t}", None)
            if not inspect.iscoroutinefunction(h):
                raise ValueError(f"Worker received message with unsupported type {t}.")

            await h(message)

    async def handle_ping(self, message):
        print("Pong!")


class Command(BaseCommand):
    help = "Closes the specified poll for voting"
    leave_locale_alone = True
    server_class = SignageServer

    def handle(self, *args, **options):
        channel_layer = get_channel_layer()
        server = self.server_class(
            application=get_default_application(),
            channel_layer=channel_layer,
            channel=settings.SIGNAGE_SCHEDULER_CHANNEL,
        )
        server.run()
