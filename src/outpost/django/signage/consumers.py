import json
import logging
from base64 import b64decode
from io import BytesIO

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from PIL import Image

from . import (
    models,
    schemas,
)

logger = logging.getLogger(__name__)


class FrontendConsumer(JsonWebsocketConsumer):
    def connect(self):
        pk = self.scope["url_route"]["kwargs"]["pk"]
        try:
            self.display = models.Display.objects.get(pk=pk)
        except models.Display.DoesNotExist:
            logger.warning(f"Connection for unknown display {pk}, closing websocket")
            self.close()
            return
        if not self.display.enabled:
            logger.info(
                f"Connection for disabled display {self.display}, closing websocket"
            )
            self.close()
            return

        self.display.connected = timezone.now()
        logger.info(f"Connection for display {self.display}, accepting websocket")
        self.display.save()

        self.accept()

        if self.display.schedule:
            logger.debug(
                f"Display {self.display} joins group {self.display.schedule.channel}"
            )
            async_to_sync(self.channel_layer.group_add)(
                self.display.schedule.channel, self.channel_name
            )
        self.send_json(
            self.display.schedule.get_active_playlist(timezone.now())
            .get_message()
            .dict()
        )

    def receive(self, text_data=None, bytes_data=None, **kwargs):
        if text_data:
            logger.warning(f"Display {self.display} received text message: {text_data}")
        if bytes_data:
            logger.warning(f"Display {self.display} received raw message: {bytes_data}")

    def disconnect(self, close_code):
        if self.display.schedule:
            logger.debug(
                f"Display {self.display} leaves group {self.display.schedule.channel}"
            )
            async_to_sync(self.channel_layer.group_discard)(
                self.display.schedule.channel, self.channel_name
            )
        logger.info(f"Connection for display {self.display} closed")
        self.display.connected = None
        self.display.save(update_fields=["connected"])

    def playlist_update(self, message):
        logger.debug(f"Sending update for display {self.display}: {message}")
        try:
            playlist = models.Playlist.objects.get(pk=message.get("playlist"))
        except models.Playlist.DoesNotExist:
            return
        self.send_json(playlist.get_message().dict())

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
            self.send_json(
                schemas.PowerMessage(
                    power=True, scale=self.display.resolution.scale
                ).dict()
            )
            return
        async_to_sync(self.channel_layer.group_add)(
            self.display.power.channel, self.channel_name
        )
        self.send_json(
            schemas.PowerMessage(
                power=self.display.power.get_active_state(timezone.now()),
                scale=self.display.resolution.scale,
            ).dict()
        )

    def disconnect(self, close_code):
        if self.display.power:
            async_to_sync(self.channel_layer.group_discard)(
                self.display.power.channel, self.channel_name
            )

    def receive_json(self, content):
        self.display.config = content.get("config")
        if (screen := content.get("screen")):
            try:
                self.display.screenshot = Image.open(BytesIO(b64decode(screen)))
            except Exception:
                logger.warn(f"Could not decode screenshot from display {self.display}")
                del self.display.screenshot
        self.display.save(update_fields=["config"])

    def power_on(self, *args):
        self.send_json(
            schemas.PowerMessage(power=True, scale=self.display.resolution.scale).dict()
        )

    def power_off(self, *args):
        self.send_json(
            schemas.PowerMessage(
                power=False, scale=self.display.resolution.scale
            ).dict()
        )
