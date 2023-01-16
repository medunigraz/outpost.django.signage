from django.urls import path

from . import consumers


urls = (
    path("signage/websocket/power/<str:pk>/", consumers.DisplayConsumer.as_asgi()),
    path("signage/websocket/frontend/<str:pk>/", consumers.FrontendConsumer.as_asgi()),
)
