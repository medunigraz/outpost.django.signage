from django.urls import reverse_lazy as reverse
from drf_haystack.serializers import HaystackSerializer
from rest_framework.serializers import ModelSerializer, SerializerMethodField
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from outpost.django.campusonline import serializers as campusonline

from . import models, search_indexes


class BackgroundSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = models.Background
        geo_field = "outline"


class LevelSerializer(ModelSerializer):
    class Meta:
        model = models.Level
        exclude = ("order",)


class RoomCategorySerializer(ModelSerializer):
    campusonline = campusonline.RoomSerializer(many=False, read_only=True)

    class Meta:
        model = models.RoomCategory


class RoomSerializer(GeoFeatureModelSerializer):
    campusonline = campusonline.RoomSerializer(many=False, read_only=True)

    class Meta:
        model = models.Room
        geo_field = "layout"
        exclude = ("polymorphic_ctype", "origin", "virtual", "deprecated")
        id_field = "id"


class RoomSearchSerializer(HaystackSerializer):
    campusonline = campusonline.RoomSerializer(many=False, read_only=True)

    class Meta:
        index_classes = [search_indexes.RoomIndex]
        fields = ["text"]


class FloorSerializer(GeoFeatureModelSerializer):
    campusonline = campusonline.FloorSerializer(many=False, read_only=True)

    class Meta:
        model = models.Floor
        geo_field = "outline"
        exclude = ("origin",)
        extra_kwargs = {"level": {"write_only": True}}


class BuildingSerializer(GeoFeatureModelSerializer):
    campusonline = campusonline.BuildingSerializer(many=False, read_only=True)

    class Meta:
        model = models.Building
        geo_field = "outline"
        exclude = ("origin",)


class DoorSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = models.Door
        geo_field = "layout"
        exclude = ("polymorphic_ctype", "origin", "deprecated")
        extra_kwargs = {"level": {"write_only": True}}
        id_field = "id"


class NodeSerializer(GeoFeatureModelSerializer):

    ctype = SerializerMethodField()

    class Meta:
        model = models.Node
        geo_field = "center"
        exclude = ("polymorphic_ctype",)

    def get_ctype(self, obj):
        return obj.polymorphic_ctype.name


class NestedNodeSerializer(NodeSerializer):
    class Meta(NodeSerializer.Meta):
        exclude = ("polymorphic_ctype",)
        extra_kwargs = {}


class EdgeCategorySerializer(ModelSerializer):
    class Meta:
        model = models.EdgeCategory


class EdgeSerializer(GeoFeatureModelSerializer):
    source_node = NestedNodeSerializer(source="source", many=False, read_only=True)
    destination_node = NestedNodeSerializer(
        source="destination", many=False, read_only=True
    )
    length = SerializerMethodField()

    class Meta:
        model = models.Edge
        geo_field = "path"

    def get_length(self, obj):
        return obj.path.length


class RoutingEdgeSerializer(EdgeSerializer):
    pass


class PointOfInterestSerializer(ModelSerializer):
    class Meta:
        model = models.PointOfInterest


class PointOfInterestInstanceSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = models.PointOfInterestInstance
        geo_field = "center"
        exclude = ("polymorphic_ctype",)
        extra_kwargs = {"level": {"write_only": True, "required": False}}
        id_field = "id"
