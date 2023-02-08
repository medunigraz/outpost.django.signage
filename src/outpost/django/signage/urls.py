from django.urls import path

from . import views

app_name = "signage"

urlpatterns = [
    path(
        "page/livechannel/<int:pk>/",
        views.LiveChannelPageView.as_view(),
        name="page-livechannel",
    ),
    path("schema/<str:name>/", views.SchemaView.as_view(), name="schema"),
]
