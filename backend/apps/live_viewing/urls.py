from rest_framework.routers import DefaultRouter

from .views import AgentLiveViewingViewSet, LiveViewingRequestViewSet

router = DefaultRouter()
router.register("requests", LiveViewingRequestViewSet, basename="live-viewing-request")
router.register("agent", AgentLiveViewingViewSet, basename="live-viewing-agent")

urlpatterns = router.urls
