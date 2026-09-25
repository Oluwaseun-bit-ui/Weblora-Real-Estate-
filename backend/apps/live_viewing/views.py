from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from apps.accounts.permissions import IsVerificationOfficerOrAbove

from . import services
from .models import AgencyRepresentative, LiveViewingRequest
from .serializers import (
    LiveViewingRequestCreateSerializer,
    LiveViewingRequestStatusSerializer,
    RoomTokenSerializer,
)


class LiveViewingRequestThrottle(AnonRateThrottle):
    scope = "live_viewing_request"


class LiveViewingRequestViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Customer-facing endpoints:
      POST /api/live-viewing/requests/            create a request
      GET  /api/live-viewing/requests/{id}/status/ poll status
      POST /api/live-viewing/requests/{id}/join/   join as customer (requires access_token)
    """

    queryset = LiveViewingRequest.objects.select_related("property", "agency", "session")
    permission_classes = [AllowAny]
    throttle_classes = [LiveViewingRequestThrottle]

    def get_serializer_class(self):
        if self.action == "create":
            return LiveViewingRequestCreateSerializer
        return LiveViewingRequestStatusSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        viewing_request = services.request_live_viewing(
            property_obj=serializer.validated_data["property"],
            customer_name=serializer.validated_data["customer_name"],
            customer_email=serializer.validated_data.get("customer_email", ""),
            customer_phone=serializer.validated_data.get("customer_phone", ""),
            requested_date=serializer.validated_data["requested_date"],
            requested_time=serializer.validated_data.get("requested_time"),
            message=serializer.validated_data.get("customer_message", ""),
        )
        out = LiveViewingRequestStatusSerializer(viewing_request)
        headers = {"X-Customer-Access-Token": viewing_request.customer_access_token}
        return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["get"], url_path="status")
    def status_view(self, request, pk=None):
        obj = self.get_object()
        return Response(LiveViewingRequestStatusSerializer(obj).data)

    @action(detail=True, methods=["post"], url_path="join")
    def join(self, request, pk=None):
        obj = self.get_object()
        access_token = request.data.get("access_token", "")
        try:
            session, token = services.join_as_customer(obj, access_token=access_token)
        except PermissionDenied as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(
            RoomTokenSerializer(
                {
                    "room_id": token.room_id,
                    "token": token.token,
                    "provider": token.provider,
                    "expires_in_seconds": token.expires_in_seconds,
                    "role": token.role,
                }
            ).data
        )

    @action(detail=True, methods=["post"], url_path="end")
    def end(self, request, pk=None):
        obj = self.get_object()
        services.end_session(obj, actor=request.user if request.user.is_authenticated else None)
        return Response(LiveViewingRequestStatusSerializer(obj).data)


class AgentLiveViewingViewSet(viewsets.GenericViewSet):
    """
    Endpoints used by an authenticated admin/staff acting on behalf of, or
    an assigned representative accepting/declining/joining, a live viewing
    request. For the MVP, representative authentication piggybacks on
    staff auth (an admin assigns + operates on behalf of a representative);
    a self-serve representative login can be added later without changing
    this interface.
    """

    queryset = LiveViewingRequest.objects.select_related("property", "agency", "session")
    permission_classes = [IsVerificationOfficerOrAbove]

    @action(detail=True, methods=["post"], url_path="accept")
    def accept(self, request, pk=None):
        obj = get_object_or_404(LiveViewingRequest, pk=pk)
        representative_id = request.data.get("representative_id")
        representative = get_object_or_404(AgencyRepresentative, pk=representative_id, agency=obj.agency) if representative_id else None
        session = services.accept_request(obj, representative=representative, actor=request.user)
        return Response({"status": obj.status, "session_id": str(session.id)})

    @action(detail=True, methods=["post"], url_path="decline")
    def decline(self, request, pk=None):
        obj = get_object_or_404(LiveViewingRequest, pk=pk)
        services.decline_request(obj, reason=request.data.get("reason", ""), actor=request.user)
        return Response({"status": obj.status})

    @action(detail=True, methods=["post"], url_path="join")
    def join(self, request, pk=None):
        obj = get_object_or_404(LiveViewingRequest, pk=pk)
        representative_id = request.data.get("representative_id")
        representative = get_object_or_404(AgencyRepresentative, pk=representative_id) if representative_id else None
        try:
            session, token = services.join_as_representative(obj, representative=representative)
        except PermissionDenied as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(
            RoomTokenSerializer(
                {
                    "room_id": token.room_id,
                    "token": token.token,
                    "provider": token.provider,
                    "expires_in_seconds": token.expires_in_seconds,
                    "role": token.role,
                }
            ).data
        )
