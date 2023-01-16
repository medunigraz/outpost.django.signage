import reversion
import asyncssh
from base64 import b64encode
from hashlib import sha256
from datetime import timedelta
from popplerqt5 import Poppler
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db import models
from django.contrib.postgres.fields import DateTimeRangeField
from django.contrib.gis.geos import (
    LineString,
    Point,
)
from django.utils import timezone
from django.db.models import Q
from django_extensions.db.models import TimeStampedModel
from ordered_model.models import OrderedModel
from channels.layers import get_channel_layer
from polymorphic.models import PolymorphicModel
from recurrence.fields import RecurrenceField
from ckeditor_uploader.fields import RichTextUploadingField
from shortuuid.django_fields import ShortUUIDField

from outpost.django.base.decorators import signal_connect
from outpost.django.base.models import NetworkedDeviceMixin
from outpost.django.base.utils import Uuid4Upload

from .validators import PDFValidator, PDFOrientation
from . import schemas


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
    name = models.CharField(max_length=128, blank=False, null=False)
    runtime = models.DurationField(default=timedelta(seconds=20))

    def get_runtime(self):
        return self.runtime

    def __str__(self):
        return self.name

    def get_message(self):
        return self.get_real_instance().get_message()

    @property
    def page(self):
        return self.__class__.__name__


class HTMLPage(Page):
    content = models.TextField()

    def get_message(self):
        return schemas.HTMLPageSchema(
            page=self.page, name=self.name, runtime=self.get_runtime(), content=self.content
        )


class RichTextPage(Page):
    content = RichTextUploadingField()

    def get_message(self):
        return schemas.RichTextPageSchema(
            page=self.page, name=self.name, runtime=self.get_runtime(), content=self.content
        )


@signal_connect
class ImagePage(Page):
    image = models.ImageField(upload_to=Uuid4Upload)

    def get_message(self):
        return schemas.ImagePageSchema(
            page=self.page, name=self.name, runtime=self.get_runtime(), url=self.image.url
        )


@signal_connect
class MoviePage(Page):
    movie = models.FileField(upload_to=Uuid4Upload)

    def pre_save(self, *args, **kwargs):
        return

    def get_message(self):
        return schemas.MoviePageSchema(
            page=self.page, name=self.name, runtime=self.get_runtime(), url=self.movie.url
        )


class WebsitePage(Page):
    url = models.URLField()

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
        "campusonline.Building", on_delete=models.DO_NOTHING, db_constraint=False
    )


class LiveEventPage(Page):
    livetemplate = models.ForeignKey("video.LiveTemplate", on_delete=models.CASCADE)


class TYPO3NewsPage(Page):
    news = models.ForeignKey(
        "typo3.News", on_delete=models.DO_NOTHING, db_constraint=False
    )

    def get_message(self):
        return schemas.TYPO3NewsPageSchema(
            page=self.page,
            name=self.name,
            runtime=self.get_runtime(),
            title=self.news.title,
            teaser=self.news.teaser,
            body=self.news.body,
            datetime=self.datetime,
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
                for m in self.news.media_set.all()
            ],
            author=self.author,
        )


class TYPO3EventPage(Page):
    event = models.ForeignKey(
        "typo3.Event", on_delete=models.DO_NOTHING, db_constraint=False
    )

    def get_message(self):
        return schemas.TYPO3NewsPageSchema(
            page=self.page,
            name=self.name,
            runtime=self.get_runtime(),
            title=self.news.title,
            teaser=self.news.teaser,
            body=self.news.body,
            datetime=self.datetime,
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
                for m in self.news.media_set.all()
            ],
            location=self.location,
            organizer=self.organizer,
            contact=self.contact,
        )


class RestaurantPage(Page):
    restaurants = models.ManyToManyField("restaurant.Restaurant")

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
