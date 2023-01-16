from functools import reduce

import django_filters
from django.db.models import Q

from . import models


class BuildingFilter(django_filters.FilterSet):
    class Meta:
        model = models.Building
        fields = ["campusonline"]


class FloorFilter(django_filters.FilterSet):
    class Meta:
        model = models.Floor
        fields = ["level", "campusonline"]


class NodeFilter(django_filters.FilterSet):
    class Meta:
        model = models.Node
        fields = ["level"]


class RoomFilter(NodeFilter):
    class Meta(NodeFilter.Meta):
        model = models.Room
        fields = ["campusonline", "category"] + NodeFilter.Meta.fields


class DoorFilter(NodeFilter):
    class Meta(NodeFilter.Meta):
        model = models.Door


class PointOfInterestInstanceFilter(NodeFilter):
    class Meta(NodeFilter.Meta):
        model = models.PointOfInterestInstance
        fields = ["name"] + NodeFilter.Meta.fields


class EdgeFilter(django_filters.FilterSet):
    level = django_filters.NumberFilter(
        method=lambda q, n, v: EdgeFilter.filter_level(q, v)
    )
    source_level = django_filters.NumberFilter(name="source__level")
    destination_level = django_filters.NumberFilter(name="destination__level")

    class Meta:
        model = models.Edge
        fields = ("level", "source_level", "destination_level")

    @staticmethod
    def filter_level(queryset, value):
        fields = ["source__level__exact", "destination__level__exact"]
        levels = reduce(lambda x, y: x | y, [Q(**{field: value}) for field in fields])
        return queryset.filter(levels)
