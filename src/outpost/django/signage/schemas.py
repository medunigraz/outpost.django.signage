from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Annotated,
    Literal,
    Optional,
    Union,
)

from django.utils.translation import gettext as _
from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
)


class Point(BaseModel):
    x: float = Field(..., description=_("EPSG:3857 longitude coordinate"))
    y: float = Field(..., description=_("EPSG:3857 latitude coordinate"))


class WeatherPageSchema(BaseModel):
    page: Literal["HTML"] = Field(..., description=_("Type of page to display"))
    id: int = Field(..., description=_("Primary key"))
    name: str = Field(..., description=_("Name of the page, only used for debugging"))
    runtime: timedelta = Field(
        ...,
        description=_(
            "Time in seconds that this page should be visible before transitioning to the next page"
        ),
    )
    content: str = Field(..., description=_("Raw HTML code to be shown for this page"))


class HTMLPageSchema(BaseModel):
    page: Literal["HTML"] = Field(..., description=_("Type of page to display"))
    id: int = Field(..., description=_("Primary key"))
    name: str = Field(..., description=_("Name of the page, only used for debugging"))
    runtime: timedelta = Field(
        ...,
        description=_(
            "Time in seconds that this page should be visible before transitioning to the next page"
        ),
    )
    content: str = Field(..., description=_("Raw HTML code to be shown for this page"))


class RichTextPageSchema(BaseModel):
    page: Literal["RichText"] = Field(..., description=_("Type of page to display"))
    id: int = Field(..., description=_("Primary key"))
    name: str = Field(..., description=_("Name of the page, only used for debugging"))
    runtime: timedelta = Field(
        ...,
        description=_(
            "Time in seconds that this page should be visible before transitioning to the next page"
        ),
    )
    content: str = Field(..., description=_("Raw HTMl code to be shown for this page"))


class ImagePageSchema(BaseModel):
    page: Literal["Image"] = Field(..., description=_("Type of page to display"))
    id: int = Field(..., description=_("Primary key"))
    name: str = Field(..., description=_("Name of the page, only used for debugging"))
    runtime: timedelta = Field(
        ...,
        description=_(
            "Time in seconds that this page should be visible before transitioning to the next page"
        ),
    )
    url: str = Field(
        ...,
        description=_("Relative URL to the image that should be displayed on the page"),
    )


class VideoPageSchema(BaseModel):
    page: Literal["Video"] = Field(..., description=_("Type of page to display"))
    id: int = Field(..., description=_("Primary key"))
    name: str = Field(..., description=_("Name of the page, only used for debugging"))
    runtime: timedelta = Field(
        ...,
        description=_(
            "Time in seconds that this page should be visible before transitioning to the next page"
        ),
    )
    url: str = Field(
        ...,
        description=_("Relative URL to the video that should be displayed on the page"),
    )


class WebsitePageSchema(BaseModel):
    page: Literal["Website"] = Field(..., description=_("Type of page to display"))
    id: int = Field(..., description=_("Primary key"))
    name: str = Field(..., description=_("Name of the page, only used for debugging"))
    runtime: timedelta = Field(
        ...,
        description=_(
            "Time in seconds that this page should be visible before transitioning to the next page"
        ),
    )
    url: HttpUrl = Field(
        ...,
        description=_(
            "Absolute URL to the website that should be displayed on the page"
        ),
    )


class PDFPageSchema(BaseModel):
    page: Literal["PDF"] = Field(..., description=_("Type of page to display"))
    id: int = Field(..., description=_("Primary key"))
    name: str = Field(..., description=_("Name of the page, only used for debugging"))
    runtime: timedelta = Field(
        ...,
        description=_(
            "Time in seconds that this page should be visible before transitioning to the next page"
        ),
    )
    url: str = Field(
        ...,
        description=_(
            "Relative URL to the PDF document that should be displayed on the page"
        ),
    )
    pages: list[str] = Field(..., description=_("Relative URL to rendered page image"))
    page_runtime: timedelta = Field(
        ...,
        description=_(
            "Time in seconds that each page of the PDF document should be visible on the page before flipping to the next page"
        ),
    )


class CampusOnlineEventItem(BaseModel):
    room: str = Field(
        ..., description=_("Name of the room the event is taking place in")
    )
    start: datetime = Field(..., description=_("Date and time of event start"))
    end: datetime = Field(..., description=_("Date and time of event end"))
    title: str = Field(..., description=_("Title of event"))
    category: str = Field(..., description=_("Category of event"))


class CampusOnlineEventPageSchema(BaseModel):
    page: Literal["CampusOnlineEvent"] = Field(
        ..., description=_("Type of page to display")
    )
    id: int = Field(..., description=_("Primary key"))
    name: str = Field(..., description=_("Name of the page, only used for debugging"))
    runtime: timedelta = Field(
        ...,
        description=_(
            "Time in seconds that this page should be visible before transitioning to the next page"
        ),
    )
    items: list[CampusOnlineEventItem] = Field(
        ...,
        description=_("Ordered list of events in this building for the current day"),
    )


class LiveChannelPageSchema(BaseModel):
    page: Literal["LiveChannel"] = Field(..., description=_("Type of page to display"))
    id: int = Field(..., description=_("Primary key"))
    name: str = Field(..., description=_("Name of the page, only used for debugging"))
    runtime: timedelta = Field(
        ...,
        description=_(
            "Time in seconds that this page should be visible before transitioning to the next page"
        ),
    )
    url: str = Field(..., description=_("Relative URL to stream metadata"))


class TYPO3Media(BaseModel):
    url: str = Field(..., description=_("Relative URL to the file"))
    mimetype: str = Field(..., description=_("MIME type"))
    size: int = Field(..., description=_("File size in bytes"))
    title: Optional[str] = Field(description=_("Title of file"))
    description: Optional[str] = Field(description=_("Description of file"))
    alternative: Optional[str] = Field(description=_("Alternative description of file"))
    preview: bool = Field(
        ..., description=_("Indicator if file is the main preview asset")
    )


class TYPO3NewsPageSchema(BaseModel):
    page: Literal["TYPO3News"] = Field(..., description=_("Type of page to display"))
    id: int = Field(..., description=_("Primary key"))
    name: str = Field(..., description=_("Name of the page, only used for debugging"))
    runtime: timedelta = Field(
        ...,
        description=_(
            "Time in seconds that this page should be visible before transitioning to the next page"
        ),
    )
    title: str
    teaser: str
    body: str
    media: list[TYPO3Media]
    datetime: datetime
    author: str


class TYPO3EventPageSchema(BaseModel):
    page: Literal["TYPO3Event"] = Field(..., description=_("Type of page to display"))
    id: int = Field(..., description=_("Primary key"))
    name: str = Field(..., description=_("Name of the page, only used for debugging"))
    runtime: timedelta = Field(
        ...,
        description=_(
            "Time in seconds that this page should be visible before transitioning to the next page"
        ),
    )
    title: str
    teaser: str
    body: str
    media: list[TYPO3Media]
    start: datetime
    end: datetime
    allday: bool
    registration: bool
    registration_end: Optional[datetime]
    location: str
    organizer: str
    contact: str


class Meal(BaseModel):
    description: str
    price: float
    diet: str


class Restaurant(BaseModel):
    name: str
    address: str
    zipcode: str
    city: str
    phone: str
    url: Optional[str]
    position: Optional[Point]
    meals: list[Meal]


class RestaurantPageSchema(BaseModel):
    page: Literal["Restaurant"] = Field(..., description=_("Type of page to display"))
    id: int = Field(..., description=_("Primary key"))
    name: str = Field(..., description=_("Name of the page, only used for debugging"))
    runtime: timedelta = Field(
        ...,
        description=_(
            "Time in seconds that this page should be visible before transitioning to the next page"
        ),
    )
    restaurant_runtime: Optional[timedelta] = Field(
        ...,
        description=_(
            "Time in seconds that each restaurant for this page should be visible before transitioning to the next restaurant"
        ),
    )
    restaurants: list[Restaurant]


Page = Annotated[
    Union[
        WeatherPageSchema,
        HTMLPageSchema,
        RichTextPageSchema,
        ImagePageSchema,
        VideoPageSchema,
        WebsitePageSchema,
        PDFPageSchema,
        CampusOnlineEventPageSchema,
        LiveChannelPageSchema,
        TYPO3NewsPageSchema,
        TYPO3EventPageSchema,
        RestaurantPageSchema,
    ],
    Field(discriminator="page"),
]


class PlaylistMessage(BaseModel):
    id: int
    pages: list[Page]


class PowerMessage(BaseModel):
    power: bool
    scale: float
