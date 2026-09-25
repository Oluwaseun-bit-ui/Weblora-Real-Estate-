from rest_framework.routers import DefaultRouter

from .views import LeadCreateViewSet

router = DefaultRouter()
router.register("", LeadCreateViewSet, basename="lead")

urlpatterns = router.urls
