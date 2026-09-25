from rest_framework.routers import DefaultRouter

from .views import AgencyPublicViewSet

router = DefaultRouter()
router.register("", AgencyPublicViewSet, basename="agency")

urlpatterns = router.urls
