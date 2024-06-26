from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import admin
from django.contrib.admin.widgets import AdminSplitDateTime
from django.contrib.postgres.forms.ranges import RangeWidget
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from guardian.shortcuts import get_objects_for_user
from ordered_model.admin import (
    OrderedInlineModelAdminMixin,
    OrderedTabularInline,
)
from outpost.django.base.guardian import (
    GuardedModelAdminFilterMixin,
    GuardedModelAdminMixin,
    GuardedModelAdminObjectMixin,
)
from polymorphic.admin import (
    PolymorphicChildModelAdmin,
    PolymorphicChildModelFilter,
    PolymorphicParentModelAdmin,
)

from . import (
    forms,
    models,
)
from .conf import settings


@admin.register(models.Resolution)
class ResolutionAdmin(admin.ModelAdmin):
    list_display = ("pk", "width", "height", "dpi", "scale")


@admin.register(models.Display)
class DisplayAdmin(
    GuardedModelAdminFilterMixin,
    GuardedModelAdminObjectMixin,
    GuardedModelAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "name",
        "pk",
        "hostname",
        "schedule_link",
        "power_link",
        "room",
        "resolution",
        "enabled",
        "online",
        "power_state",
        "playlist_state",
    )
    list_filter = ("schedule", "power", "resolution", "enabled", "online")
    readonly_fields = ("pk", "config", "screenshot")

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["schedule"].queryset = get_objects_for_user(
            request.user, "signage.view_schedule", form.base_fields["schedule"].queryset
        )
        return form

    def schedule_link(self, obj):
        if not obj.schedule:
            return "-"
        url = reverse("admin:signage_schedule_change", args=(obj.schedule.pk,))
        return format_html("<a href='{}'>{}</a>", url, obj.schedule)

    schedule_link.admin_order_field = "schedule"
    schedule_link.short_description = _("Schedule")

    def power_link(self, obj):
        if not obj.power:
            return "-"
        url = reverse("admin:signage_power_change", args=(obj.power.pk,))
        return format_html("<a href='{}'>{}</a>", url, obj.power)

    power_link.admin_order_field = "power"
    power_link.short_description = _("Power")

    def power_state(self, obj):
        if not obj.power:
            return False
        return obj.power.get_active_state(timezone.now())

    power_state.short_description = _("Power state")
    power_state.boolean = True

    def playlist_state(self, obj):
        if not obj.schedule:
            return "-"
        return obj.schedule.get_active_playlist(timezone.now())

    playlist_state.short_description = _("Playlist state")

    def screenshot(self, obj):
        if obj.screenshot:
            return format_html(
                """<img style="max-width: 50%" class="submit-row" src="{}"/>""",
                reverse("signage:display-screenshot", kwargs={"pk": obj.pk}),
            )
        return "-"

    screenshot.short_description = _("Screenshot")


class PageChildAdmin(
    GuardedModelAdminFilterMixin,
    GuardedModelAdminObjectMixin,
    GuardedModelAdminMixin,
    PolymorphicChildModelAdmin,
):
    base_model = models.Page


@admin.register(models.Page)
class PageParentAdmin(
    GuardedModelAdminFilterMixin,
    GuardedModelAdminObjectMixin,
    PolymorphicParentModelAdmin,
):
    base_model = models.Page
    child_models = sorted(
        (
            models.WeatherPage,
            models.HTMLPage,
            models.RichTextPage,
            models.ImagePage,
            models.VideoPage,
            models.WebsitePage,
            models.PDFPage,
            models.LiveChannelPage,
            models.TYPO3NewsPage,
            models.TYPO3EventPage,
            models.CampusOnlineEventPage,
            models.RestaurantPage,
        ),
        key=lambda c: c._meta.verbose_name,
    )
    list_filter = (PolymorphicChildModelFilter,)
    list_display = ("name", "page", "created", "modified")


@admin.register(models.WeatherPage)
class WeatherPageAdmin(PageChildAdmin):
    base_model = models.WeatherPage
    show_in_index = False


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


@admin.register(models.VideoPage)
class VideoPageAdmin(PageChildAdmin):
    base_model = models.VideoPage
    show_in_index = False
    exclude = ("runtime",)


@admin.register(models.WebsitePage)
class WebsitePageAdmin(PageChildAdmin):
    base_model = models.WebsitePage
    show_in_index = False


@admin.register(models.PDFPage)
class PDFPageAdmin(PageChildAdmin):
    base_model = models.PDFPage
    show_in_index = False
    exclude = ("runtime",)


@admin.register(models.CampusOnlineEventPage)
class CampusOnlineEventPageAdmin(PageChildAdmin):
    base_model = models.CampusOnlineEventPage
    show_in_index = False


@admin.register(models.LiveChannelPage)
class LiveChannelPageAdmin(PageChildAdmin):
    base_model = models.LiveChannelPage
    show_in_index = False


@admin.register(models.TYPO3NewsPage)
class TYPO3NewsPageAdmin(PageChildAdmin):
    base_model = models.TYPO3NewsPage
    show_in_index = False

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["news"].queryset = form.base_fields["news"].queryset.filter(
            datetime__gte=timezone.now() - settings.SIGNAGE_TYPO3_NEWS_RETROSPECTIVE
        )
        return form


@admin.register(models.TYPO3EventPage)
class TYPO3EventPageAdmin(PageChildAdmin):
    base_model = models.TYPO3EventPage
    show_in_index = False

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["event"].queryset = form.base_fields["event"].queryset.filter(
            start__gte=timezone.now() - settings.SIGNAGE_TYPO3_NEWS_RETROSPECTIVE
        )
        return form


@admin.register(models.RestaurantPage)
class RestaurantPageAdmin(PageChildAdmin):
    base_model = models.RestaurantPage
    show_in_index = False
    exclude = ("runtime",)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["restaurants"].queryset = form.base_fields[
            "restaurants"
        ].queryset.filter(enabled=True)
        return form


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

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields.get("page").queryset = get_objects_for_user(
            request.user,
            "signage.view_page",
            formset.form.base_fields.get("page").queryset,
        )
        return formset


@admin.register(models.Playlist)
class PlaylistAdmin(
    OrderedInlineModelAdminMixin,
    GuardedModelAdminFilterMixin,
    GuardedModelAdminObjectMixin,
    GuardedModelAdminMixin,
    admin.ModelAdmin,
):
    inlines = (PlaylistItemInline,)


class ScheduleItemInline(OrderedTabularInline):
    model = models.ScheduleItem
    extra = 1
    form = forms.ScheduleItemAdminForm
    formset = forms.ScheduleItemAdminInlineFormSet

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields.get("playlist").queryset = get_objects_for_user(
            request.user,
            "signage.view_playlist",
            formset.form.base_fields.get("playlist").queryset,
        )
        return formset


@admin.register(models.Schedule)
class ScheduleAdmin(
    OrderedInlineModelAdminMixin,
    GuardedModelAdminFilterMixin,
    GuardedModelAdminObjectMixin,
    GuardedModelAdminMixin,
    admin.ModelAdmin,
):
    inlines = (ScheduleItemInline,)
    list_display = ("name", "default", "ical")
    actions = ("publish",)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["default"].queryset = get_objects_for_user(
            request.user, "signage.view_playlist", form.base_fields["default"].queryset
        )
        return form

    def ical(self, obj):
        return format_html(
            _("""<a href="{}">Download</a>"""),
            reverse("signage:ical-schedule", kwargs={"pk": obj.pk}),
        )

    ical.short_description = _("Calendar")

    def publish(self, request, queryset):
        for s in queryset.all():
            s.publish()
            self.message_user(request, _("{s} successfully published.").format(s=s))

    publish.short_description = _("Publish schedule to connected displays")


class PowerItemInline(OrderedTabularInline):
    model = models.PowerItem
    extra = 1
    formfield_overrides = {
        models.DateTimeRangeField: {"widget": RangeWidget(AdminSplitDateTime())},
    }


@admin.register(models.Power)
class PowerAdmin(OrderedInlineModelAdminMixin, admin.ModelAdmin):
    inlines = (PowerItemInline,)
    actions = ("publish",)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # import pudb; pu.db
        now = timezone.now()
        channel_layer = get_channel_layer()
        msg_type = "power.on" if form.instance.get_active_state(now) else "power.off"
        async_to_sync(channel_layer.group_send)(
            form.instance.channel, {"type": msg_type}
        )

    def publish(self, request, queryset):
        for p in queryset.all():
            p.publish()
            self.message_user(request, _("{p} successfully published.").format(p=p))

    publish.short_description = _("Publish power to connected displays")
