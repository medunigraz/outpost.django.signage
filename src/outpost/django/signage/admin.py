from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import admin
from django.contrib.admin.widgets import AdminSplitDateTime
from django.contrib.postgres.forms.ranges import (
    DateTimeRangeField,
    RangeWidget,
)
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from ordered_model.admin import (
    OrderedInlineModelAdminMixin,
    OrderedModelAdmin,
    OrderedTabularInline,
)
from polymorphic.admin import (
    PolymorphicChildModelAdmin,
    PolymorphicChildModelFilter,
    PolymorphicParentModelAdmin,
)
from reversion.admin import VersionAdmin

from . import (
    forms,
    models,
)
from .conf import settings


@admin.register(models.Resolution)
class ResolutionAdmin(admin.ModelAdmin):
    list_display = ("pk", "width", "height")


@admin.register(models.Display)
class DisplayAdmin(admin.ModelAdmin):
    list_display = ("name", "schedule", "room", "resolution", "enabled", "online")
    list_filter = ("schedule", "resolution", "enabled", "online")


class PageChildAdmin(PolymorphicChildModelAdmin):
    base_model = models.Page


@admin.register(models.Page)
class PageParentAdmin(PolymorphicParentModelAdmin):
    base_model = models.Page
    child_models = (
        models.HTMLPage,
        models.RichTextPage,
        models.ImagePage,
        models.MoviePage,
        models.WebsitePage,
        models.PDFPage,
        models.LiveEventPage,
        models.TYPO3NewsPage,
        models.TYPO3EventPage,
        models.CampusOnlineEventPage,
        models.RestaurantPage,
    )
    list_filter = (PolymorphicChildModelFilter,)


@admin.register(models.HTMLPage)
class HTMLPageAdmin(PageChildAdmin):
    base_model = models.HTMLPage
    show_in_index = False


@admin.register(models.RichTextPage)
class RichTextPageAdmin(PageChildAdmin):
    base_model = models.RichTextPage
    show_in_index = False


@admin.register(models.ImagePage)
class ImagePageAdmin(PageChildAdmin):
    base_model = models.ImagePage
    show_in_index = False


@admin.register(models.MoviePage)
class MoviePageAdmin(PageChildAdmin):
    base_model = models.MoviePage
    show_in_index = False


@admin.register(models.WebsitePage)
class WebsitePageAdmin(PageChildAdmin):
    base_model = models.WebsitePage
    show_in_index = False


@admin.register(models.PDFPage)
class PDFPageAdmin(PageChildAdmin):
    base_model = models.PDFPage
    show_in_index = False
    readonly_fields = ("runtime",)


@admin.register(models.CampusOnlineEventPage)
class CampusOnlineEventPageAdmin(PageChildAdmin):
    base_model = models.CampusOnlineEventPage
    show_in_index = False


@admin.register(models.LiveEventPage)
class LiveEventPageAdmin(PageChildAdmin):
    base_model = models.LiveEventPage
    show_in_index = False


@admin.register(models.TYPO3NewsPage)
class TYPO3NewsPageAdmin(PageChildAdmin):
    base_model = models.TYPO3NewsPage
    show_in_index = False


@admin.register(models.TYPO3EventPage)
class TYPO3EventPageAdmin(PageChildAdmin):
    base_model = models.TYPO3EventPage
    show_in_index = False


@admin.register(models.RestaurantPage)
class RestaurantPageAdmin(PageChildAdmin):
    base_model = models.RestaurantPage
    show_in_index = False


class PlaylistItemInline(OrderedTabularInline):
    model = models.PlaylistItem
    fields = (
        "page",
        "enabled",
        "move_up_down_links",
    )
    readonly_fields = (
        "order",
        "move_up_down_links",
    )
    ordering = ("order",)
    extra = 1


@admin.register(models.Playlist)
class PlaylistAdmin(OrderedInlineModelAdminMixin, admin.ModelAdmin):
    inlines = (PlaylistItemInline,)


class ScheduleItemInline(OrderedTabularInline):
    model = models.ScheduleItem
    extra = 1
    form = forms.ScheduleItemAdminForm


#    formfield_overrides = {
#        models.DateTimeRangeField: {'widget': RangeWidget(AdminSplitDateTime())},
#    }


@admin.register(models.Schedule)
class ScheduleAdmin(OrderedInlineModelAdminMixin, admin.ModelAdmin):
    inlines = (ScheduleItemInline,)


class PowerItemInline(OrderedTabularInline):
    model = models.PowerItem
    extra = 1
    formfield_overrides = {
        models.DateTimeRangeField: {"widget": RangeWidget(AdminSplitDateTime())},
    }


@admin.register(models.Power)
class PowerAdmin(OrderedInlineModelAdminMixin, admin.ModelAdmin):
    inlines = (PowerItemInline,)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # import pudb; pu.db
        channel_layer = get_channel_layer()
        msg_type = "power.on" if form.instance.status() else "power.off"
        async_to_sync(channel_layer.group_send)(
            form.instance.channel, {"type": msg_type}
        )
