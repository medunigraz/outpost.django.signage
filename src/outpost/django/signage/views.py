from pydantic.main import ModelMetaclass
from django.views import View
from django.utils.translation import gettext as _
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseBadRequest

from . import schemas


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
