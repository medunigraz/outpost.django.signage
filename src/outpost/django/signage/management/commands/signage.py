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
        self.scheduler = AsyncIOScheduler(
            jobstores=settings.SIGNAGE_SCHEDULER_JOB_STORES
        )
        self.scheduler.start()
        self.schedules = dict()
        self.powers = dict()
        now = timezone.localtime()
        for s in models.Schedule.objects.all():
            trigger = s.get_next_trigger(now)
            if not trigger:
                logger.info(f"No more scheduled items for {s}")
                if s.pk in self.schedules:
                    del self.schedules[s.pk]
                continue
            logger.debug(f"Updating schedule {s} at {trigger}")
            self.schedules[s.pk] = self.scheduler.add_job(
                self.schedule,
                "date",
                run_date=trigger,
                kwargs={"schedule": s, "after": trigger},
            )
        for p in models.Power.objects.all():
            trigger = p.get_next_trigger(now)
            if not trigger:
                logger.info(f"No more power items for {p}")
                if p.pk in self.powers:
                    del self.powers[p.pk]
                continue
            logger.debug(f"Updating power {p} at {trigger}")
            self.powers[p.pk] = self.scheduler.add_job(
                self.power,
                "date",
                run_date=trigger,
                kwargs={"power": p, "after": trigger},
            )

    async def schedule(self, schedule, after):
        self.schedules.get(schedule.pk).remove()
        logger.debug(f"Updating schedule {schedule} after {after}")
        trigger = schedule.get_next_trigger(after)
        if not trigger:
            logger.info(f"No more events for {schedule} after {after}")
            if schedule.pk in self.schedules:
                del self.schedules[schedule.pk]
            return
        logger.debug(f"Next update for schedule {schedule} at {trigger}")
        p = schedule.get_active_playlist(after)
        logger.debug(f"Starting playlist {p} from {schedule}")
        await self.channel_layer.group_send(
            schedule.channel, {"type": "playlist.update", "playlist": p.pk}
        )
        self.schedules[schedule.pk] = self.scheduler.add_job(
            self.schedule,
            "date",
            run_date=trigger,
            kwargs={"schedule": schedule, "after": trigger},
        )

    async def power(self, power, after):
        self.powers.get(power.pk).remove()
        logger.debug(f"Updating power {power} after {after}")
        trigger = power.get_next_trigger(after)
        if not trigger:
            logger.info(f"No more events for {power} after {after}")
            if power.pk in self.powers:
                del self.powers[power.pk]
            return
        logger.debug(f"Next update for power {power} at {trigger}")
        p = power.get_active_state(after)
        logger.debug(f"Setting power to {p} for {power}")
        await self.channel_layer.group_send(
            power.channel, {"type": "power.on" if p else "power.off"}
        )
        self.powers[power.pk] = self.scheduler.add_job(
            self.power,
            "date",
            run_date=trigger,
            kwargs={"power": power, "after": trigger},
        )

    async def handle(self):
        now = timezone.localtime()
        for s in models.Schedule.objects.all():
            p = s.get_active_playlist(now)
            await self.channel_layer.group_send(
                s.channel, {"type": "playlist.update", "playlist": p.pk}
            )
        for p in models.Power.objects.all():
            await self.channel_layer.group_send(
                s.channel,
                {"type": "power.on" if p.get_active_state(now) else "power.off"},
            )
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

    async def handle_schedule(self, message):
        pk = message.get("schedule")
        try:
            schedule = models.Schedule.objects.get(pk=pk)
        except models.Schedule.DoesNotExist:
            logger.error("Unknown schedule {pk}")
            return
        await self.schedule(schedule, timezone.localtime())

    async def handle_power(self, message):
        pk = message.get("power")
        try:
            power = models.Power.objects.get(pk=pk)
        except models.Power.DoesNotExist:
            logger.error("Unknown power {pk}")
            return
        await self.power(power, timezone.localtime())

    async def handle_ping(self, message):
        print("Pong!")


class Command(BaseCommand):
    help = "Manages communication with Signage frontend displays."
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
