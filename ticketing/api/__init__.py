"""REST API views for the ticketing application."""

from .dashboard import (
    TicketDashboardAnalyticsView,
    TicketDashboardFiltersView,
    TicketDashboardRecentView,
    TicketDashboardSummaryView,
)
from .detail import (
    TicketAssignAPIView,
    TicketAttachmentsAPIView,
    TicketCommentsAPIView,
    TicketDeleteAPIView,
    TicketDetailAPIView,
    TicketTimelineAPIView,
    TicketWatchersAPIView,
)
from .form import (
    TicketCreateAPIView,
    TicketDeviceOptionsAPIView,
    TicketFormOptionsAPIView,
    TicketLocationOptionsAPIView,
    TicketUpdateAPIView,
)
from .list import TicketListAPIView

__all__ = [
    "TicketDashboardAnalyticsView",
    "TicketDashboardFiltersView",
    "TicketDashboardRecentView",
    "TicketDashboardSummaryView",
    "TicketAssignAPIView",
    "TicketAttachmentsAPIView",
    "TicketCommentsAPIView",
    "TicketDeleteAPIView",
    "TicketDetailAPIView",
    "TicketTimelineAPIView",
    "TicketWatchersAPIView",
    "TicketListAPIView",
    "TicketFormOptionsAPIView",
    "TicketDeviceOptionsAPIView",
    "TicketLocationOptionsAPIView",
    "TicketCreateAPIView",
    "TicketUpdateAPIView",
]
