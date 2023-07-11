from guardian.shortcuts import get_objects_for_user
from outpost.django.api.permissions import ExtendedDjangoObjectPermissions
from outpost.django.base.decorators import docstring_format
from rest_flex_fields.views import FlexFieldsMixin
from rest_framework.viewsets import ReadOnlyModelViewSet

from . import (
    models,
    serializers,
)
from .conf import settings


class PlaylistViewSet(FlexFieldsMixin, ReadOnlyModelViewSet):
    queryset = models.Playlist.objects.all()
    serializer_class = serializers.PlaylistSerializer
    permission_classes = (ExtendedDjangoObjectPermissions,)
    filter_fields = ()

    def get_queryset(self):
        qs = super().get_queryset()
        view = f"{qs.model._meta.app_label}.view_{qs.model._meta.model_name}"
        change = f"{qs.model._meta.app_label}.change_{qs.model._meta.model_name}"
        return get_objects_for_user(
            self.request.user,
            (view, change),
            qs,
            accept_global_perms=True,
            any_perm=True,
        )
