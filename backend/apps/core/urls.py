from django.urls import path

from .views import public_config

urlpatterns = [
    path("", public_config, name="public-config"),
]
