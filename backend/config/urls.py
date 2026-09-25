from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/agencies/", include("apps.agencies.urls")),
    path("api/properties/", include("apps.properties.urls")),
    path("api/leads/", include("apps.leads.urls")),
    path("api/live-viewing/", include("apps.live_viewing.urls")),
    path("api/config/", include("apps.core.urls")),
    path("api/web-search/", include("apps.web_search.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
