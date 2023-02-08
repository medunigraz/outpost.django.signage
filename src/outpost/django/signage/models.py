import logging
from base64 import b64encode
from dataclasses import dataclass
from datetime import (
    datetime,
    time,
    timedelta,
)
from hashlib import sha256

import asyncssh
import reversion
from channels.layers import get_channel_layer
from ckeditor_uploader.fields import RichTextUploadingField
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db import models
from django.contrib.gis.geos import (
    LineString,
    Point,
)
from django.contrib.postgres.fields import DateTimeRangeField
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel
from ordered_model.models import OrderedModel
from outpost.django.base.decorators import signal_connect
from outpost.django.base.models import NetworkedDeviceMixin
from outpost.django.base.utils import Uuid4Upload
from outpost.django.base.validators import ImageValidator
from outpost.django.campusonline.models import Event as CampusOnlineEvent
from outpost.django.weather.models import Location as WeatherLocation
from polymorphic.models import PolymorphicModel
from popplerqt5 import Poppler
from recurrence.fields import RecurrenceField
from shortuuid.django_fields import ShortUUIDField

from . import schemas
from .validators import (
    PDFOrientation,
    PDFValidator,
)

logger = logging.getLogger(__name__)


class Resolution(models.Model):
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.width}x{self.height}"


@signal_connect
class Display(NetworkedDeviceMixin, models.Model):
    id = ShortUUIDField(
        length=10,
        max_length=10,
        primary_key=True,
        editable=False,
    )
    name = models.CharField(max_length=128, blank=False, null=False)
    schedule = models.ForeignKey(
        "Schedule", blank=True, null=True, on_delete=models.SET_NULL
    )
    power = models.ForeignKey("Power", blank=True, null=True, on_delete=models.SET_NULL)
    hostname = models.CharField(max_length=256, blank=False, null=False)
    username = models.CharField(max_length=128, blank=False, null=False)
    key = models.BinaryField(null=False, editable=False)
    room = models.ForeignKey(
        "campusonline.Room",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        db_constraint=False,
    )
    resolution = models.ForeignKey(Resolution, on_delete=models.CASCADE)
    dpi = models.PositiveIntegerField(null=True, blank=True)
    connected = models.DateTimeField(null=True, editable=False)

    def __str__(self):
        return f"{self.name} ({self.hostname})"

    def fingerprint(self):
        if not self.key:
            return None
        k = asyncssh.import_private_key(self.key.tobytes())
        d = sha256(k.public_data).digest()
        f = b64encode(d).replace(b"=", b"").decode("utf-8")
        return "SHA256:{}".format(f)

    def private_key(self):
        return self.key.tobytes().decode("ascii")

    def pre_save(self, *args, **kwargs):
        if self.key:
            return
        pk = asyncssh.generate_private_key("ssh-rsa", comment=self.name)
        # For compatibility with older SSH implementations
        self.key = pk.export_private_key("pkcs1-pem")
        self.save()


class Page(TimeStampedModel, PolymorphicModel):
    name = models.CharField(
        max_length=128,
        blank=False,
        null=False,
        help_text=_("A canonical name for this page."),
    )
    runtime = models.DurationField(
        default=timedelta(seconds=20),
        help_text=_(
            "The time this page should be visible before it is replaced with the next page."
        ),
    )

    def get_runtime(self):
        return self.runtime

    def __str__(self):
        return self.name

    def get_message(self):
        return self.get_real_instance().get_message()

    @property
    def page(self):
        return self.get_real_instance().__class__.__name__.removesuffix("Page")


class WeatherPage(Page):
    location = models.ForeignKey(WeatherLocation, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Weather page")
        verbose_name_plural = _("Weather pages")

    def get_message(self):
        return schemas.WeatherPageSchema(
            page=self.page,
            name=self.name,
            runtime=self.get_runtime(),
            forecast=self.location.forecast,
        )


class HTMLPage(Page):
    content = models.TextField()

    class Meta:
        verbose_name = _("HTML page")
        verbose_name_plural = _("HTML pages")

    def get_message(self):
        return schemas.HTMLPageSchema(
            page=self.page, name=self.name, runtime=self.get_runtime(), content=self.content
        )


class RichTextPage(Page):
    content = RichTextUploadingField()

    class Meta:
        verbose_name = _("Rich text page")
        verbose_name_plural = _("Rich text pages")

    def get_message(self):
        return schemas.RichTextPageSchema(
            page=self.page,
            name=self.name,
            runtime=self.get_runtime(),
            content=self.content,
        )


@signal_connect
class ImagePage(Page):
    image = models.ImageField(
        upload_to=Uuid4Upload,
        validators=(
            ImageValidator(
                formats=("jpeg", "png", "webp"),
                width=range(1920, 4096),
                height=range(1080, 2160),
            ),
        ),
    )

    class Meta:
        verbose_name = _("Image page")
        verbose_name_plural = _("Image pages")

    def get_message(self):
        return schemas.ImagePageSchema(
            page=self.page, name=self.name, runtime=self.get_runtime(), url=self.image.url
        )


@signal_connect
class MoviePage(Page):
    movie = models.FileField(upload_to=Uuid4Upload)

    class Meta:
        verbose_name = _("Movie page")
        verbose_name_plural = _("Movie pages")

    def pre_save(self, *args, **kwargs):
        return

    def get_message(self):
        return schemas.MoviePageSchema(
            page=self.page, name=self.name, runtime=self.get_runtime(), url=self.movie.url
        )


class WebsitePage(Page):
    url = models.URLField(validators=(URLValidator(schemes=("https",)),))

    class Meta:
        verbose_name = _("Website page")
        verbose_name_plural = _("Website pages")

    def get_message(self):
        return schemas.WebsitePageSchema(
            page=self.page, name=self.name, runtime=self.get_runtime(), url=self.url
        )


@signal_connect
class PDFPage(Page):
    pdf = models.FileField(
        upload_to=Uuid4Upload,
        validators=(
            PDFValidator(
                orientation=PDFOrientation.LANDSCAPE,
                pages=range(1, 20),
            ),
        ),
    )
    pages = models.PositiveSmallIntegerField(editable=False)
    page_runtime = models.DurationField(blank=True, null=True)

    class Meta:
        verbose_name = _("PDF page")
        verbose_name_plural = _("PDF pages")

    def __str__(self):
        return f"{self.name} ({self.pdf.name})"

    def pre_save(self, *args, **kwargs):
        doc = Poppler.Document.loadFromData(self.pdf.open().read())
        self.pages = doc.numPages()

    def get_runtime(self):
        if self.page_runtime:
            return self.pages * self.page_runtime
        return super().get_runtime()

    def get_message(self):
        return schemas.PDFPageSchema(
            page=self.page,
            name=self.name,
            runtime=self.get_runtime(),
            url=self.pdf.url,
            pages=self.pages,
            page_runtime=int(self.page_runtime.total_seconds())
            if self.page_runtime
            else self.get_runtime() / self.pages,
        )


class CampusOnlineEventPage(Page):
    building = models.ForeignKey(
        "campusonline.Building",
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        help_text=_("The building for which all events should be displayed."),
    )

    class Meta:
        verbose_name = _("CAMPUSonline event page")
        verbose_name_plural = _("CAMPUSonline event pages")

    def get_message(self):
        return schemas.CampusOnlineEventPageSchema(
            page=self.page,
            name=self.name,
            runtime=self.get_runtime(),
            items=[
                schemas.CampusOnlineEventItem(
                    room=str(i.room),
                    start=i.start,
                    end=i.end,
                    title=i.title,
                    category=i.category,
                )
                for i in CampusOnlineEvent.objects.filter(building=self.building)
            ],
        )


class LiveChannelPage(Page):
    livechannel = models.ForeignKey(
        "video.LiveChannel",
        on_delete=models.CASCADE,
        help_text=_(
            "The streaming channel that should be displayed. Provided that a public stream is started in this location while this page is active."
        ),
    )

    class Meta:
        verbose_name = _("Live channel page")
        verbose_name_plural = _("Live channel pages")

    def get_message(self):
        return schemas.LiveChannelPageSchema(
            page=self.page,
            name=self.name,
            runtime=self.get_runtime(),
            url=reverse("signage:page-livechannel", kwargs={"pk": self.pk}),
        )


class TYPO3NewsPage(Page):
    news = models.ForeignKey(
        "typo3.News", on_delete=models.DO_NOTHING, db_constraint=False
    )

    class Meta:
        verbose_name = _("TYPO3 news page")
        verbose_name_plural = _("TYPO3 news pages")

    def get_message(self):
        return schemas.TYPO3NewsPageSchema(
            page=self.page,
            name=self.name,
            runtime=self.get_runtime(),
            title=self.news.title,
            teaser=self.news.teaser,
            body=self.news.body,
            datetime=self.news.datetime,
            media=[
                schemas.TYPO3Media(
                    url=m.media.url,
                    mimetype=m.media.mimetype,
                    size=m.media.size,
                    title=m.title,
                    description=m.description,
                    alternative=m.alternative,
                    preview=m.preview,
                )
                for m in self.news.media.all()
            ],
            author=self.news.author,
        )


class TYPO3EventPage(Page):
    event = models.ForeignKey(
        "typo3.Event", on_delete=models.DO_NOTHING, db_constraint=False
    )

    class Meta:
        verbose_name = _("TYPO3 event page")
        verbose_name_plural = _("TYPO3 event pages")

    def get_message(self):
        return schemas.TYPO3EventPageSchema(
            page=self.page,
            name=self.name,
            runtime=self.get_runtime(),
            title=self.event.title,
            teaser=self.event.teaser,
            body=self.event.body,
            start=self.event.start,
            end=self.event.end,
            allday=self.event.allday,
            registration=self.event.register,
            registration_end=self.event.registration_end,
            media=[
                schemas.TYPO3Media(
                    url=m.media.url,
                    mimetype=m.media.mimetype,
                    size=m.media.size,
                    title=m.title,
                    description=m.description,
                    alternative=m.alternative,
                    preview=m.preview,
                )
                for m in self.event.media.all()
            ],
            location=self.event.location,
            organizer=self.event.organizer,
            contact=self.event.contact,
        )


class RestaurantPage(Page):
    restaurants = models.ManyToManyField("restaurant.Restaurant")

    class Meta:
        verbose_name = _("Restaurant page")
        verbose_name_plural = _("Restaurant pages")

    def get_message(self):
        today = timezone.now().today()
        return schemas.RestaurantPageSchema(
            page=self.page,
            name=self.name,
            runtime=self.get_runtime(),
            restaurants=[
                schemas.Restaurant(
                    name=r.name,
                    address=r.address,
                    zipcode=r.zipcode,
                    city=r.city,
                    phone=r.phone,
                    url=r.url,
                    position=schemas.Point(x=r.position.x, y=r.position.y),
                    meals=[
                        schemas.Meal(
                            description=m.description, price=m.price, diet=m.diet.name
                        )
                        for m in r.meals.filter(available=today)
                    ],
                )
                for r in self.restaurants.filter(enabled=True)
            ]
        )


class Playlist(models.Model):
    name = models.CharField(max_length=128, blank=False, null=False)

    def __str__(self):
        return self.name

    def get_message(self):
        return schemas.PlaylistMessage(pages=[p.page.get_message() for p in self.playlistitem_set.filter(enabled=True)])


class PlaylistItem(OrderedModel):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE)
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    enabled = models.BooleanField(default=True)
    order_with_respect_to = "playlist"

    def __str__(self):
        return f"{self.page}@{self.playlist}[{self.order}]"


class Schedule(models.Model):
    name = models.CharField(max_length=128, blank=False, null=False)
    default = models.ForeignKey("Playlist", on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    @property
    def channel(self):
        return f"{__name__}.{self.__class__.__name__}.{self.pk}"

    def get_current(self):
        now = timezone.now()
        scheduleitems = self.scheduleitem_set.filter(
            start__lte=now,
            stop__gte=now,
        ).order_by("-start", "stop")
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        for s in scheduleitems:
            if bool(s.recurrences.between(today, today, dtstart=today, inc=True)):
                return s.playlist
        return self.default


class ScheduleItem(models.Model):
    schedule = models.ForeignKey("Schedule", on_delete=models.CASCADE)
    range = DateTimeRangeField()
    start = models.TimeField()
    stop = models.TimeField()
    recurrences = RecurrenceField(include_dtstart=False)
    playlist = models.ForeignKey("Playlist", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.playlist} ({self.range.lower} - {self.range.upper})"

    def clean(self):
        if self.start > self.stop:
            raise ValidationError(
                _("Start time must be less then end"),
            )


@signal_connect
class Power(models.Model):
    name = models.CharField(max_length=128, blank=False, null=False)

    def __str__(self):
        return self.name

    @property
    def channel(self):
        return f"{__name__}.{self.__class__.__name__}.{self.pk}"

    @property
    def current(self):
        return {}

    def status(self):
        now = timezone.now()
        poweritems = self.poweritem_set.filter(
            on__lte=now,
            off__gte=now,
        )
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        for p in poweritems:
            if bool(p.recurrences.between(today, today, dtstart=today, inc=True)):
                return True
        return False


class PowerItem(models.Model):
    power = models.ForeignKey("Power", on_delete=models.CASCADE)
    on = models.TimeField()
    off = models.TimeField()
    recurrences = RecurrenceField(include_dtstart=False)

    def __str__(self):
        return f"{self.power} ({self.on} - {self.off})"
