from rest_flex_fields import FlexFieldsModelSerializer
from rest_framework.serializers import SerializerMethodField

from . import models


class PlaylistSerializer(FlexFieldsModelSerializer):
    message = SerializerMethodField()

    class Meta:
        model = models.Playlist
        fields = (
            "id",
            "name",
            "message",
        )

    def get_message(selfi, obj):
        return obj.get_message().dict()
