import logging
from dataclasses import dataclass

from braces.views import (
    JSONResponseMixin,
    LoginRequiredMixin,
)
from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotFound,
)
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import DetailView
from django_ical.views import ICalFeed
from outpost.django.video.models import LiveEvent
from PIL import Image
from pydantic.main import ModelMetaclass

from . import (
    models,
    schemas,
)

logger = logging.getLogger(__name__)


class SchemaView(View):
    def get(self, request, name):
        cls = getattr(schemas, name, None)
        if not cls:
            return HttpResponseNotFound(_("No such schema found"))
        if not isinstance(cls, ModelMetaclass):
            return HttpResponseBadRequest(_("Requested class is not a schema"))
        return HttpResponse(
            cls.schema_json(indent=2), content_type="application/schema+json"
        )


@dataclass
class Event:
    start: timezone.datetime
    stop: timezone.datetime
    name: str


class ScheduleFeed(ICalFeed):
    product_id = "-//api.medunigraz.at//Signage/Schedule//EN"
    timezone = settings.TIME_ZONE
    file_name = "schedule.ics"

    def get_object(self, request, pk):
        return models.Schedule.objects.get(pk=pk)

    def items(self, obj):
        for s in obj.scheduleitem_set.filter(range__endswith__gt=timezone.now()):
            for r in s.recurrences.between(
                s.range.lower, s.range.upper, inc=True, dtstart=timezone.now()
            ):
                yield Event(
                    timezone.datetime.combine(r.date(), s.start, tzinfo=r.tzinfo),
                    timezone.datetime.combine(r.date(), s.stop, tzinfo=r.tzinfo),
                    s.playlist.name,
                )

    def item_title(self, item):
        return item.name

    def item_description(self, item):
        return item.name

    def item_start_datetime(self, item):
        return item.start

    def item_end_datetime(self, item):
        return item.stop

    def item_link(self, item):
        return ""


class LiveChannelPageView(JSONResponseMixin, DetailView):
    model = models.LiveChannelPage

    def get(self, request, *args, **kwargs):
        lep = self.get_object()
        event = get_object_or_404(
            LiveEvent, channel=lep.channel, end__isnull=True, public=True
        )
        viewer = models.LiveViewer.objects.create(event=event)
        logger.info(f"Created new viewer {viewer}")
        data = {
            "viewer": viewer.pk,
            "streams": {s.type: s.viewer(viewer) for s in event.livestream_set.all()},
        }

        return self.render_json_response(data)


class DisplayScreenshotView(LoginRequiredMixin, DetailView):
    model = models.Display

    def get(self, request, pk, *args, **kwargs):
        screen = self.get_object().screenshot
        if not screen:
            screen = Image.open(finders.find("signage/placeholder/screenshot.webp"))
        response = HttpResponse(content_type=screen.get_format_mimetype())
        screen.save(response, format=screen.format)
        return response
