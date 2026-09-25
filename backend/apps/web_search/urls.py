from django.urls import path

from .views import WebSearchView

urlpatterns = [
    path("", WebSearchView.as_view(), name="web-search"),
]
