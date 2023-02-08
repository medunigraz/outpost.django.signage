from enum import Enum

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
                if not (self._pages.start <= doc.numPages() <= self._pages.stop):
                    if self._pages.start <= doc.numPages():
                        raise ValidationError(
                            _(
                                "Document contains less pages than allowed ({ found } < { allowed })"
                            ).format(found=doc.numPages(), allowed=self._pages.start)
                        )
                    if doc.numPages() >= self._pages.stop:
                        raise ValidationError(
                            _(
                                "Document contains more pages than allowed ({ found } < { allowed })"
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
