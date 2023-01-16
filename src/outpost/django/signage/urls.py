from django.urls import path

from . import views

app_name = "signage"

urlpatterns = [path("schema/<str:name>/", views.SchemaView.as_view(), name="schema")]
