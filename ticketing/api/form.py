from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..api.permissions import HasTicketingAccess
from ..api.serializers import (
    DeviceOptionSerializer,
    TicketCreateUpdateSerializer,
    TicketFormOptionsSerializer,
)
from ..services import TicketFormService


class TicketFormOptionsAPIView(APIView):
    """Returns form field options for ticket create/edit forms."""

    permission_classes = [IsAuthenticated, HasTicketingAccess]

    def get(self, request):
        service = TicketFormService(request.user)
        options = service.get_form_options()
        serializer = TicketFormOptionsSerializer(options)
        return Response(serializer.data)


class TicketDeviceOptionsAPIView(APIView):
    """Returns device options for a given site, optionally filtered by device_type and subgroup (for sub-devices)."""

    permission_classes = [IsAuthenticated, HasTicketingAccess]

    def get(self, request):
        site_code = request.query_params.get("site")
        if not site_code:
            return Response({"devices": []})

        # Support device_type, subgroup, and location parameters
        device_type = request.query_params.get("type")
        subgroup = request.query_params.get("subgroup")
        location = request.query_params.get("location")

        service = TicketFormService(request.user)
        devices = service.get_device_options(site_code, device_type=device_type, subgroup=subgroup, location=location)
        serializer = DeviceOptionSerializer(devices, many=True)
        return Response({"devices": serializer.data})


class TicketLocationOptionsAPIView(APIView):
    """Returns location options for a given site."""

    permission_classes = [IsAuthenticated, HasTicketingAccess]

    def get(self, request):
        site_code = request.query_params.get("site")
        if not site_code:
            return Response({"locations": []})

        service = TicketFormService(request.user)
        locations = service.get_location_options(site_code)
        return Response({"locations": locations})


class TicketCreateAPIView(APIView):
    """Creates a new ticket."""

    permission_classes = [IsAuthenticated, HasTicketingAccess]

    def post(self, request):
        serializer = TicketCreateUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        service = TicketFormService(request.user)
        ip_address = request.META.get("REMOTE_ADDR")

        try:
            ticket = service.create_ticket(serializer.validated_data, ip_address=ip_address)
            # Send notification
            from ..tasks import send_ticket_created_notification

            send_ticket_created_notification.delay(str(ticket.id))
            return Response(
                {
                    "id": str(ticket.id),
                    "ticket_number": ticket.ticket_number,
                    "success": True,
                },
                status=201,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class TicketUpdateAPIView(APIView):
    """Updates an existing ticket."""

    permission_classes = [IsAuthenticated, HasTicketingAccess]

    def put(self, request, pk):
        serializer = TicketCreateUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        service = TicketFormService(request.user)
        ip_address = request.META.get("REMOTE_ADDR")

        try:
            ticket = service.update_ticket(pk, serializer.validated_data, ip_address=ip_address)
            return Response(
                {
                    "id": str(ticket.id),
                    "ticket_number": ticket.ticket_number,
                    "success": True,
                },
                status=200,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=400)

