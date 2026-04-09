from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..services import TicketDashboardService
from .permissions import HasTicketingAccess
from .serializers import (
    AnalyticsResponseSerializer,
    RecentTicketsResponseSerializer,
    TicketDashboardFiltersSerializer,
    TicketDashboardSummarySerializer,
)


class TicketDashboardSummaryView(APIView):
    """Returns aggregated ticket dashboard metrics for the React client."""

    permission_classes = [IsAuthenticated, HasTicketingAccess]

    def get(self, request):
        service = TicketDashboardService(request.user)
        payload = service.build_react_payload(request.query_params)
        serializer = TicketDashboardSummarySerializer(payload)
        return Response(serializer.data)


class TicketDashboardFiltersView(APIView):
    """Exposes filter metadata for the React dashboard."""

    permission_classes = [IsAuthenticated, HasTicketingAccess]

    def get(self, request):
        service = TicketDashboardService(request.user)
        options = service.get_filter_options()
        serializer = TicketDashboardFiltersSerializer(options)
        return Response(serializer.data)


class TicketDashboardRecentView(APIView):
    """Returns recent ticket rows honouring current filters."""

    permission_classes = [IsAuthenticated, HasTicketingAccess]

    def get(self, request):
        service = TicketDashboardService(request.user)
        limit = int(request.query_params.get("limit", 10))
        limit = max(1, min(limit, 100))

        filters = {
            "status": request.query_params.get("status"),
            "priority": request.query_params.get("priority"),
            "category": request.query_params.get("category"),
            "site": request.query_params.get("site"),
            "date_from": request.query_params.get("date_from"),
            "date_to": request.query_params.get("date_to"),
        }
        filter_by = request.query_params.get("filter_by")
        filter_value = request.query_params.get("filter_value")

        queryset = service.get_recent_ticket_queryset_with_filters(
            raw_filters=filters,
            filter_by=filter_by,
            filter_value=filter_value,
            limit=None,
        )

        total_count = queryset.count()
        results = list(service.serialize_recent_tickets(queryset, limit=limit))

        serializer = RecentTicketsResponseSerializer({
            "count": total_count,
            "results": results,
        })
        return Response(serializer.data)


class TicketDashboardAnalyticsView(APIView):
    """Returns analytics widget dataset (no HTML)."""

    permission_classes = [IsAuthenticated, HasTicketingAccess]

    def get(self, request):
        service = TicketDashboardService(request.user)
        view_by = request.query_params.get("view_by", "device_tickets")
        per_page = int(request.query_params.get("per_page", request.query_params.get("top_n", 10)))
        page = int(request.query_params.get("page", 1))
        trend_days = int(request.query_params.get("trend_days", 7))

        filters = {
            "status": request.query_params.get("status"),
            "priority": request.query_params.get("priority"),
            "category": request.query_params.get("category"),
            "site": request.query_params.get("site"),
            "date_from": request.query_params.get("date_from"),
            "date_to": request.query_params.get("date_to"),
        }

        try:
            dataset = service.get_analytics_dataset(
                raw_filters=filters,
                view_by=view_by,
                page=page,
                per_page=per_page,
                trend_days=trend_days,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

        serializer = AnalyticsResponseSerializer(dataset)
        return Response(serializer.data)



