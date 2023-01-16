from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class SignageConfig(AppConfig):
    name = "outpost.django.signage"
    verbose_name = _("Signage")
