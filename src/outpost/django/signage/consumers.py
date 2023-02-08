import json
from datetime import timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from asgiref.sync import async_to_sync
from channels.consumer import AsyncConsumer
from channels.generic.websocket import JsonWebsocketConsumer
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone

from . import (
    models,
    schemas,
)


class FrontendConsumer(JsonWebsocketConsumer):
    def connect(self):
        try:
            self.display = models.Display.objects.get(
                pk=self.scope["url_route"]["kwargs"]["pk"]
            )
        except models.Display.DoesNotExist:
            self.close()
            return
        if not self.display.enabled:
            self.close()
            return

        self.display.connected = timezone.now()
        self.display.save()

        self.accept()

        if self.display.schedule:
            async_to_sync(self.channel_layer.group_add)(
                self.display.schedule.channel, self.channel_name
            )
        self.send_json(self.display.schedule.get_current().get_message().dict())

    def receive_json(self, content):
        return

    def disconnect(self, close_code):
        if self.display.schedule:
            async_to_sync(self.channel_layer.group_discard)(
                self.display.schedule.channel, self.channel_name
            )
        self.display.connected = None
        self.display.save()

    @classmethod
    def encode_json(cls, content):
        return json.dumps(content, cls=DjangoJSONEncoder)


class DisplayConsumer(JsonWebsocketConsumer):
    def connect(self):
        try:
            self.display = models.Display.objects.get(
                pk=self.scope["url_route"]["kwargs"]["pk"]
            )
        except models.Display.DoesNotExist:
            self.close()
            return
        if not self.display.enabled:
            self.close()
            return

        self.accept()
        if not self.display.power:
            return
        async_to_sync(self.channel_layer.group_add)(
            self.display.power.channel, self.channel_name
        )
        self.send_json(schemas.PowerMessage(power=self.display.power.status()).dict())

    def disconnect(self, close_code):
        if self.display.power:
            async_to_sync(self.channel_layer.group_discard)(
                self.display.power.channel, self.channel_name
            )

    def receive_json(self, content):
        return

    def power_on(self, *args):
        self.send_json(schemas.PowerMessage(power=True).dict())

    def power_off(self, *args):
        self.send_json(schemas.PowerMessage(power=False).dict())
