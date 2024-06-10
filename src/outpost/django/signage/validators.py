import json
import subprocess
from collections.abc import Iterable
from enum import Enum
from fractions import Fraction
from typing import (
    Any,
    Optional,
)

from django.core.exceptions import ValidationError
from django.core.files.base import File
from django.utils.deconstruct import deconstructible
from django.utils.translation import ugettext_lazy as _
from popplerqt5 import Poppler


class PDFOrientation(Enum):
    LANDSCAPE = Poppler.Page.Orientation.Landscape
    PORTRAIT = Poppler.Page.Orientation.Portrait
    SEASCAPE = Poppler.Page.Orientation.Seascape
    UPSIDEDOWN = Poppler.Page.Orientation.UpsideDown


@deconstructible
class PDFValidator(object):
    """
    Validate PDF properties
    """

    code = "invalid"

    def __init__(self, orientation=None, pages=None):
        self._orientation = orientation
        self._pages = pages

    def __call__(self, data):
        doc = Poppler.Document.loadFromData(data.open().read())
        if not doc:
            raise ValidationError(_("File is not a valid PDF document"), self.code)
        if self._pages:
            if isinstance(self._pages, int):
                if doc.numPages() > self._pages:
                    raise ValidationError(
                        _(
                            "Document contains more pages than allowed ({found} > {allowed})"
                        ).format(found=doc.numPages(), allowed=self._pages)
                    )
            if isinstance(self._pages, range):
                if not (self._pages.start < doc.numPages() < self._pages.stop):
                    if self._pages.start > doc.numPages():
                        raise ValidationError(
                            _(
                                "Document contains less pages than allowed ({found} < {allowed})"
                            ).format(found=doc.numPages(), allowed=self._pages.start)
                        )
                    if self._pages.stop < doc.numPages():
                        raise ValidationError(
                            _(
                                "Document contains more pages than allowed ({found} > {allowed})"
                            ).format(found=doc.numPages(), allowed=self._pages.stop)
                        )

        if self._orientation:
            wrong = [
                n
                for n, p in enumerate(doc)
                if p.orientation() != self._orientation.value
            ]
            if wrong:
                raise ValidationError(
                    _("Pages have wrong orientation ({wrong})").format(
                        wrong=", ".join(map(str, wrong))
                    )
                )


class MediaAbstractValidator(object):
    def probe(self, media):
        proc = subprocess.run(
            [
                "ffprobe",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                media,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
        return json.loads(proc.stdout.decode("utf-8"))

    def __call__(self, data):
        info = self.probe(data.file.file.name)
        self.validate(info)

    def validate(self, info):
        pass


@deconstructible
class MediaContainerValidator(MediaAbstractValidator):
    """
    Validate media container properties
    """

    code = "invalid"

    def __init__(
        self,
        formats: Optional[Iterable] = None,
        video_streams: Optional[int] = None,
        audio_streams: Optional[int] = None,
        bitrate: Optional[range] = None,
        inlines: Optional[Iterable] = None,
    ):
        self._formats = formats
        self._video_streams = video_streams
        self._audio_streams = audio_streams
        self._bitrate = bitrate
        self._inlines = inlines

    def __call__(self, data: Any) -> None:
        info = self.probe(data.file.file.name)
        if self._formats is not None:
            format_name = info.get("format").get("format_name")
            if not set(format_name.split(",")) & set(self._formats):
                raise ValidationError(
                    _(
                        "Container of format {format} not allowed. Use one of these: {allowed}."
                    ).format(format=format_name, allowed=", ".join(self._formats))
                )
        if self._video_streams is not None:
            video_streams = len(
                list(
                    filter(
                        lambda s: s.get("codec_type") == "video", info.get("streams")
                    )
                )
            )
            if video_streams != self._video_streams:
                raise ValidationError(
                    _(
                        "Container has {video_streams} vide streams. Use only {allowed}."
                    ).format(video_streams=video_streams, allowed=self._video_streams)
                )
        if self._audio_streams is not None:
            audio_streams = len(
                list(
                    filter(
                        lambda s: s.get("codec_type") == "audio", info.get("streams")
                    )
                )
            )
            if audio_streams != self._audio_streams:
                raise ValidationError(
                    _(
                        "Container has {audio_streams} audio streams. Use only {allowed}."
                    ).format(audio_streams=audio_streams, allowed=self._audio_streams)
                )
        if self._bitrate is not None:
            bitrate = int(info.get("format").get("bitrate"))
            if bitrate not in self._bitrate:
                raise ValidationError(
                    _(
                        "Container has {bitrate} bitrate. Use a bitrate between {allowed.start} and {allowed.stop}."
                    ).format(bitrate=bitrate, allowed=self._bitrate)
                )

        if isinstance(self._inlines, Iterable):
            for inline in self._inlines:
                inline.validate(info)


@deconstructible
class MediaVideoValidator(MediaAbstractValidator):
    """
    Validate media video properties
    """

    code = "invalid"

    def __init__(
        self,
        display_aspect_ratio: Optional[Fraction] = None,
        sample_aspect_ratio: Optional[Fraction] = None,
        codecs: Optional[Iterable] = None,
        width: Optional[range] = None,
        height: Optional[range] = None,
    ) -> None:
        self._display_aspect_ratio = display_aspect_ratio
        self._sample_aspect_ratio = sample_aspect_ratio
        self._codecs = codecs
        self._width = width
        self._height = height

    def validate(self, info: dict):
        for s in filter(lambda s: s.get("codec_type") == "video", info.get("streams")):
            index = s.get("index")
            if self._display_aspect_ratio is not None:
                display_aspect_ratio = Fraction(
                    s.get("display_aspect_ratio").replace(":", "/")
                )
                if display_aspect_ratio != self._display_aspect_ratio:
                    raise ValidationError(
                        _(
                            "Video stream at position {index} has {display_aspect_ratio} display aspect ratio. Use a display aspect ratio of {allowed}."
                        ).format(
                            index=index,
                            display_aspect_ratio=display_aspect_ratio,
                            allowed=self._display_aspect_ratio,
                        )
                    )
            if self._display_aspect_ratio is not None:
                sample_aspect_ratio = Fraction(
                    s.get("sample_aspect_ratio").replace(":", "/")
                )
                if sample_aspect_ratio != self._sample_aspect_ratio:
                    raise ValidationError(
                        _(
                            "Video stream at position {index} has {sample_aspect_ratio} sample aspect ratio. Use a sample aspect ratio of {allowed}."
                        ).format(
                            index=index,
                            sample_aspect_ratio=sample_aspect_ratio,
                            allowed=self._sample_aspect_ratio,
                        )
                    )
            if self._codecs is not None:
                codec = s.get("codec_name")
                if codec not in self._codecs:
                    raise ValidationError(
                        _(
                            "Video stream at position {index} has {codec} codec. Use a codec of {allowed}."
                        ).format(
                            index=index, codec=codec, allowed=", ".join(self._codecs)
                        )
                    )
            if self._width is not None:
                width = int(s.get("width"))
                if width not in self._width:
                    raise ValidationError(
                        _(
                            "Video stream at position {index} is {width} pixels wide. Use a width between {allowed.start} and {allowed.stop} pixels."
                        ).format(index=index, width=width, allowed=self._width)
                    )
            if self._height is not None:
                height = int(s.get("height"))
                if height not in self._height:
                    raise ValidationError(
                        _(
                            "Video stream at position {index} is {height} pixels high. Use a width between {allowed.start} and {allowed.stop} pixels."
                        ).format(index=index, height=height, allowed=self._height)
                    )


@deconstructible
class MediaAudioValidator(MediaAbstractValidator):
    """
    Validate media audio properties
    """

    code = "invalid"

    def __init__(
        self,
        codecs: Optional[Iterable] = None,
        sample_rate: Optional[range] = None,
        channels: Optional[range] = None,
    ):
        self._codecs = codecs
        self._sample_rate = sample_rate
        self._channels = channels

    def validate(self, info: dict) -> None:
        for s in filter(lambda s: s.get("codec_type") == "audio", info.get("streams")):
            index = s.get("index")
            if self._codecs is not None:
                codec = s.get("codec_name")
                if codec not in self._codecs:
                    raise ValidationError(
                        _(
                            "Audio stream at position {index} has {codec} codec. Use a codec of {allowed}."
                        ).format(
                            index=index, codec=codec, allowed=", ".join(self._codecs)
                        )
                    )
            if self._sample_rate is not None:
                sample_rate = int(s.get("sample_rate"))
                if sample_rate not in self._sample_rate:
                    raise ValidationError(
                        _(
                            "Audio stream at position {index} is a sample rate of {sample_rate}. Use a sample rate between {allowed.start} and {allowed.stop}."
                        ).format(
                            index=index,
                            sample_rate=sample_rate,
                            allowed=self._sample_rate,
                        )
                    )
            if self._channels is not None:
                channels = int(s.get("channels"))
                if channels not in self._channels:
                    raise ValidationError(
                        _(
                            "Audio stream at position {index} has {channels} channels. Use a between {allowed.start} and {allowed.stop} channels."
                        ).format(index=index, channels=channels, allowed=self._channels)
                    )
