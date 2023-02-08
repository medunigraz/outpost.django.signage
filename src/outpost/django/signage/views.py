import logging
from dataclasses import dataclass

from braces.views import JSONResponseMixin
from django.conf import settings
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
from outpost.django.video.models import (
    LiveEvent,
    LiveViewer,
)
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
