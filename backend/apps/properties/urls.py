from rest_framework.routers import DefaultRouter

from .views import PropertySearchViewSet

router = DefaultRouter()
router.register("", PropertySearchViewSet, basename="property")

urlpatterns = router.urls
