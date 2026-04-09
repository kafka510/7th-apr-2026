from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from math import ceil
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from django.db.models import Count, QuerySet, Sum
from django.utils import timezone

from ..models import Ticket, TicketCategory, LossCategory
from ..utils import get_accessible_sites_for_user


@dataclass
class AvgCloseTime:
    days: int
    hours: int
    minutes: int
    total_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AnalyticsItem:
    label: str
    sub_label: Optional[str]
    value: float
    secondary: float
    entity_type: str
    entity_key: Any
    trend: Sequence[int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "subLabel": self.sub_label,
            "value": self.value,
            "secondary": self.secondary,
            "trend": list(self.trend),
            "entityType": self.entity_type,
            "entityKey": self.entity_key,
        }


class TicketDashboardService:
    """Encapsulates ticket dashboard calculations for reuse across views and APIs."""

    _FILTER_KEY_MAP: Dict[str, str] = {
        "status": "status",
        "priority": "priority",
        "category": "category",
        "category_id": "category",
        "categoryId": "category",
        "site": "site",
        "site_id": "site",
        "siteId": "site",
        "siteCode": "site_code",
        "date_from": "date_from",
        "dateFrom": "date_from",
        "date_to": "date_to",
        "dateTo": "date_to",
    }

    def __init__(self, user):
        self.user = user

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def get_accessible_sites(self):
        if not hasattr(self, "_accessible_sites"):
            self._accessible_sites = get_accessible_sites_for_user(self.user).order_by("asset_name")
        return self._accessible_sites

    def get_queryset(self, raw_filters: Optional[Mapping[str, Any]] = None) -> QuerySet:
        """Return base queryset filtered by the supplied filter mapping."""
        filters = self._normalise_filters(raw_filters or {})

        tickets = (
            Ticket.objects.filter(is_active=True, asset_code__in=self.get_accessible_sites())
            .select_related("asset_code", "device_id", "created_by", "assigned_to", "category", "loss_category")
            .order_by("-created_at")
        )

        status = filters.get("status")
        if status:
            tickets = tickets.filter(status=status)

        priority = filters.get("priority")
        if priority:
            tickets = tickets.filter(priority=priority)

        category = filters.get("category")
        if category:
            tickets = self._filter_by_category(tickets, category)

        site = filters.get("site")
        site_code = filters.get("site_code")
        if site or site_code:
            tickets = self._filter_by_site(tickets, site, site_code)

        date_from = filters.get("date_from")
        if date_from:
            parsed = self._parse_date(date_from)
            if parsed:
                tickets = tickets.filter(created_at__date__gte=parsed)

        date_to = filters.get("date_to")
        if date_to:
            parsed = self._parse_date(date_to)
            if parsed:
                tickets = tickets.filter(created_at__date__lte=parsed)

        return tickets

    # ------------------------------------------------------------------
    # Template context helpers
    # ------------------------------------------------------------------
    def build_template_context(self, raw_filters: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        tickets = self.get_queryset(raw_filters)
        closed_tickets = tickets.filter(status="closed", closed_at__isnull=False)
        avg_time = self.calculate_avg_time_to_close(closed_tickets)

        context: Dict[str, Any] = {
            "status_choices": Ticket.STATUS_CHOICES,
            "priority_choices": Ticket.PRIORITY_CHOICES,
            "categories": TicketCategory.objects.filter(is_active=True).order_by("display_order", "name"),
            "sites": self.get_accessible_sites(),
            "total_tickets": tickets.count(),
            "status_breakdown": list(self.get_status_breakdown(tickets)),
            "priority_breakdown": list(self.get_priority_breakdown(tickets)),
            "category_breakdown": list(self.get_category_breakdown(tickets)),
            "loss_category_breakdown": list(self.get_loss_category_breakdown(tickets)),
            "avg_time_to_close": avg_time.to_dict() if avg_time else None,
            "tickets_by_status": self.get_tickets_by_status_counts(tickets),
            "recent_tickets": tickets[:10],
            "open_tickets": self.get_open_tickets_count(tickets),
            "overdue_tickets": self.get_overdue_tickets_count(tickets),
            "unassigned_tickets": self.get_unassigned_tickets_count(tickets),
            "tickets_by_creator": self.get_tickets_by_creator(tickets),
            "tickets_by_assignee": self.get_tickets_by_assignee(tickets),
            "tickets_by_device": self.get_tickets_by_device_queryset(tickets),
            "tickets_by_make": self.get_tickets_by_make(tickets),
            "tickets_by_model": self.get_tickets_by_model(tickets),
            "total_loss_value": self.get_total_loss_value(tickets),
            "loss_by_category": self.get_loss_by_category_queryset(tickets),
            "loss_by_device": self.get_loss_by_device_queryset(tickets),
        }

        return context

    # ------------------------------------------------------------------
    # Serialization helpers for legacy AJAX and new React clients
    # ------------------------------------------------------------------
    def serialize_dashboard_payload(self, tickets: QuerySet) -> Dict[str, Any]:
        """Return payload matching legacy DashboardAPIView expectations."""
        return {
            "kpis": self.get_kpi_summary(tickets),
            "charts": self.get_chart_payload(tickets),
            "recent_tickets": self.serialize_recent_tickets(tickets),
            "tickets_by_device": self.serialize_tickets_by_device(tickets),
            "loss_by_category": self.serialize_loss_by_category(tickets),
            "loss_by_device": self.serialize_loss_by_device(tickets),
        }

    def serialize_ticket_stats(self, tickets: QuerySet) -> Dict[str, Any]:
        """Return condensed stats for api_get_ticket_stats compatibility."""
        closed_tickets = tickets.filter(status="closed", closed_at__isnull=False)
        avg_time = self.calculate_avg_time_to_close(closed_tickets)

        return {
            "total_tickets": tickets.count(),
            "status_breakdown": list(self.get_status_breakdown(tickets)),
            "priority_breakdown": list(self.get_priority_breakdown(tickets)),
            "category_breakdown": list(self.get_category_breakdown(tickets)),
            "avg_time_to_close": avg_time.to_dict() if avg_time else None,
            "recent_tickets": self.serialize_recent_tickets_for_stats(tickets, limit=10),
        }

    def build_react_payload(self, raw_filters: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        filters = self._normalise_filters(raw_filters or {})
        tickets = self.get_queryset(filters)
        closed_tickets = tickets.filter(status="closed", closed_at__isnull=False)
        avg_time = self.calculate_avg_time_to_close(closed_tickets)

        losses_by_category = self.serialize_loss_by_category(tickets)
        losses_by_device = self.serialize_loss_by_device(tickets)

        total_loss = sum(item.get("total_loss", 0.0) for item in losses_by_category)

        return {
            "meta": {
                "appliedFilters": self._serialize_applied_filters(filters),
                "generatedAt": timezone.now().isoformat(),
            },
            "filters": self.get_filter_options(),
            "kpis": self.get_kpi_summary(tickets),
            "charts": self.get_chart_payload(tickets),
            "recentTickets": self.serialize_recent_tickets(tickets),
            "ticketsByDevice": self.serialize_tickets_by_device(tickets),
            "ticketsByStatus": self.get_tickets_by_status_counts(tickets),
            "avgTimeToClose": avg_time.to_dict() if avg_time else None,
            "losses": {
                "total": total_loss,
                "byCategory": losses_by_category,
                "byDevice": losses_by_device,
            },
        }

    # ------------------------------------------------------------------
    # Aggregation helpers
    # ------------------------------------------------------------------
    def get_analytics_dataset(
        self,
        raw_filters: Optional[Mapping[str, Any]],
        view_by: str,
        page: int = 1,
        per_page: int = 10,
        trend_days: int = 7,
    ) -> Dict[str, Any]:
        filters = self._normalise_filters(raw_filters or {})
        base_qs = self.get_queryset(filters)

        items = self._build_analytics_items(base_qs, view_by)

        total_items = len(items)
        if per_page <= 0:
            per_page = 10
        if page <= 0:
            page = 1

        offset = (page - 1) * per_page
        paged_items = items[offset : offset + per_page]

        analytics_rows: List[AnalyticsItem] = []
        for item in paged_items:
            trend = self._get_trend_counts_for_entity(
                base_qs,
                item["entity_type"],
                item["entity_key"],
                days=trend_days,
            )
            analytics_rows.append(
                AnalyticsItem(
                    label=item["label"],
                    sub_label=item.get("sub_label"),
                    value=item["value"],
                    secondary=item["secondary"],
                    entity_type=item["entity_type"],
                    entity_key=item["entity_key"],
                    trend=trend,
                )
            )

        return {
            "labels": [row.label for row in analytics_rows],
            "values": [row.value for row in analytics_rows],
            "items": [row.to_dict() for row in analytics_rows],
            "pagination": {
                "page": page,
                "perPage": per_page,
                "totalItems": total_items,
                "totalPages": ceil(total_items / per_page) if per_page else 0,
            },
        }

    def get_kpi_summary(self, tickets: QuerySet) -> Dict[str, int]:
        return {
            "total_tickets": tickets.count(),
            "open_tickets": self.get_open_tickets_count(tickets),
            "unassigned_tickets": self.get_unassigned_tickets_count(tickets),
            "overdue_tickets": self.get_overdue_tickets_count(tickets),
        }

    def get_chart_payload(self, tickets: QuerySet) -> Dict[str, Dict[str, Iterable[Any]]]:
        status_breakdown = list(self.get_status_breakdown(tickets))
        priority_breakdown = list(self.get_priority_breakdown(tickets))
        category_breakdown = list(self.get_category_breakdown(tickets))

        return {
            "status": {
                "labels": [item["status"].replace("_", " ").title() for item in status_breakdown],
                "values": [item["count"] for item in status_breakdown],
            },
            "priority": {
                "labels": [item["priority"].title() for item in priority_breakdown],
                "values": [item["count"] for item in priority_breakdown],
            },
            "category": {
                "labels": [item["category__name"] for item in category_breakdown],
                "values": [item["count"] for item in category_breakdown],
            },
        }

    def get_status_breakdown(self, tickets: QuerySet):
        return tickets.values("status").annotate(count=Count("id")).order_by("status")

    def get_priority_breakdown(self, tickets: QuerySet):
        return tickets.values("priority").annotate(count=Count("id")).order_by("priority")

    def get_category_breakdown(self, tickets: QuerySet):
        return (
            tickets.values("category__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

    def get_loss_category_breakdown(self, tickets: QuerySet):
        return (
            tickets.exclude(loss_category__isnull=True)
            .values("loss_category__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

    def get_tickets_by_status_counts(self, tickets: QuerySet) -> Dict[str, int]:
        return {
            status_key: tickets.filter(status=status_key).count()
            for status_key, _ in Ticket.STATUS_CHOICES
        }

    def get_recent_tickets_queryset(self, tickets: QuerySet, limit: int = 10) -> QuerySet:
        return tickets.order_by("-created_at")[:limit]

    def serialize_recent_tickets(self, tickets: QuerySet, limit: int = 10) -> Iterable[Dict[str, Any]]:
        recent_qs = self.get_recent_tickets_queryset(tickets, limit=limit)
        return [
            {
                "id": str(ticket.id),
                "ticket_number": ticket.ticket_number,
                "title": ticket.title,
                "status": ticket.status,
                "status_display": ticket.get_status_display(),
                "priority": ticket.priority,
                "priority_display": ticket.get_priority_display(),
                "site_name": ticket.asset_code.asset_name if ticket.asset_code else "N/A",
                "created_at": ticket.created_at.strftime("%b %d, %Y"),
            }
            for ticket in recent_qs
        ]

    def serialize_recent_tickets_for_stats(self, tickets: QuerySet, limit: int = 10) -> Iterable[Dict[str, Any]]:
        recent_qs = self.get_recent_tickets_queryset(tickets, limit=limit)
        return [
            {
                "ticket_number": ticket.ticket_number,
                "title": ticket.title,
                "status": ticket.status,
                "priority": ticket.priority,
                "asset_name": ticket.asset_code.asset_name if ticket.asset_code else "N/A",
                "created_by": ticket.created_by.username if ticket.created_by else None,
                "assigned_to": ticket.assigned_to.username if ticket.assigned_to else None,
                "created_at": ticket.created_at.isoformat(),
            }
            for ticket in recent_qs
        ]

    def get_open_tickets_count(self, tickets: QuerySet) -> int:
        return tickets.exclude(status__in=["closed", "cancelled"]).count()

    def get_overdue_tickets_count(self, tickets: QuerySet) -> int:
        week_ago = timezone.now() - timedelta(days=7)
        return (
            tickets.exclude(status__in=["closed", "cancelled"])
            .filter(created_at__lt=week_ago)
            .count()
        )

    def get_unassigned_tickets_count(self, tickets: QuerySet) -> int:
        return (
            tickets.filter(assigned_to__isnull=True)
            .exclude(status__in=["closed", "cancelled"])
            .count()
        )

    def get_tickets_by_creator(self, tickets: QuerySet):
        return (
            tickets.values("created_by__username")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

    def get_tickets_by_assignee(self, tickets: QuerySet):
        return (
            tickets.exclude(assigned_to__isnull=True)
            .values("assigned_to__username")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

    def get_tickets_by_device_queryset(self, tickets: QuerySet):
        return (
            tickets.exclude(device_id__isnull=True)
            .values("device_id__device_name", "device_id__device_serial")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

    def serialize_tickets_by_device(self, tickets: QuerySet) -> Iterable[Dict[str, Any]]:
        return [
            {
                "device_name": item["device_id__device_name"],
                "device_serial": item["device_id__device_serial"] or "N/A",
                "count": item["count"],
            }
            for item in self.get_tickets_by_device_queryset(tickets)
        ]

    def get_tickets_by_make(self, tickets: QuerySet):
        return (
            tickets.exclude(device_id__isnull=True)
            .values("device_id__device_make")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

    def get_tickets_by_model(self, tickets: QuerySet):
        return (
            tickets.exclude(device_id__isnull=True)
            .values("device_id__device_model", "device_id__device_make")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

    def get_total_loss_value(self, tickets: QuerySet) -> float:
        total = tickets.aggregate(total=Sum("loss_value")).get("total")
        return float(total or 0.0)

    def get_loss_by_category_queryset(self, tickets: QuerySet):
        return (
            tickets.exclude(loss_category__isnull=True, loss_value__isnull=True)
            .values("loss_category__name")
            .annotate(total_loss=Sum("loss_value"), count=Count("id"))
            .order_by("-total_loss")
        )

    def serialize_loss_by_category(self, tickets: QuerySet) -> Iterable[Dict[str, Any]]:
        return [
            {
                "category_name": item["loss_category__name"],
                "total_loss": float(item["total_loss"] or 0.0),
                "count": item["count"],
            }
            for item in self.get_loss_by_category_queryset(tickets)
        ]

    def get_loss_by_device_queryset(self, tickets: QuerySet):
        return (
            tickets.exclude(device_id__isnull=True, loss_value__isnull=True)
            .values(
                "device_id__device_name",
                "device_id__device_make",
                "device_id__device_model",
            )
            .annotate(total_loss=Sum("loss_value"), count=Count("id"))
            .order_by("-total_loss")[:10]
        )

    def serialize_loss_by_device(self, tickets: QuerySet) -> Iterable[Dict[str, Any]]:
        return [
            {
                "device_name": item["device_id__device_name"],
                "device_make": item["device_id__device_make"] or "Unknown",
                "device_model": item["device_id__device_model"] or "Unknown",
                "total_loss": float(item["total_loss"] or 0.0),
                "count": item["count"],
            }
            for item in self.get_loss_by_device_queryset(tickets)
        ]

    def get_recent_ticket_queryset_with_filters(
        self,
        raw_filters: Optional[Mapping[str, Any]],
        filter_by: Optional[str] = None,
        filter_value: Optional[str] = None,
        limit: Optional[int] = 50,
    ) -> QuerySet:
        filters = self._normalise_filters(raw_filters or {})
        tickets = self.get_queryset(filters)

        if filter_by and filter_value:
            if filter_by in {"device_tickets", "device_loss"} or filter_by.startswith("device"):
                tickets = tickets.filter(device_id__device_name=filter_value)
            elif filter_by.startswith("category"):
                tickets = tickets.filter(category__name=filter_value)
            elif filter_by == "make_tickets":
                tickets = tickets.filter(device_id__device_make=filter_value)
            elif filter_by == "model_tickets":
                tickets = tickets.filter(device_id__device_model=filter_value)

        tickets = tickets.order_by("-created_at")
        if limit is not None:
            tickets = tickets[:limit]
        return tickets

    def calculate_avg_time_to_close(self, tickets: QuerySet) -> Optional[AvgCloseTime]:
        if not tickets.exists():
            return None

        total_seconds = 0.0
        counted = 0

        for ticket in tickets:
            if ticket.closed_at:
                delta = ticket.closed_at - ticket.created_at
                total_seconds += delta.total_seconds()
                counted += 1

        if counted == 0 or total_seconds <= 0:
            return None

        avg_seconds = total_seconds / counted
        days = int(avg_seconds // 86400)
        hours = int((avg_seconds % 86400) // 3600)
        minutes = int((avg_seconds % 3600) // 60)

        return AvgCloseTime(days=days, hours=hours, minutes=minutes, total_seconds=avg_seconds)

    # ------------------------------------------------------------------
    # Filter options / metadata
    # ------------------------------------------------------------------
    def get_filter_options(self) -> Dict[str, Iterable[Dict[str, Any]]]:
        return {
            "statusOptions": [
                {"value": value, "label": label} for value, label in Ticket.STATUS_CHOICES
            ],
            "priorityOptions": [
                {"value": value, "label": label} for value, label in Ticket.PRIORITY_CHOICES
            ],
            "categoryOptions": [
                {"value": category.id, "label": category.name, "description": category.description}
                for category in TicketCategory.objects.filter(is_active=True).order_by("display_order", "name")
            ],
            "lossCategoryOptions": [
                {"value": category.id, "label": category.name, "description": category.description}
                for category in LossCategory.objects.filter(is_active=True).order_by("display_order", "name")
            ],
            "siteOptions": [
                {
                    "value": site.asset_code,
                    "label": site.asset_name,
                    "assetCode": site.asset_code,
                    "country": getattr(site, "country", None),
                    "portfolio": getattr(site, "portfolio", None),
                }
                for site in self.get_accessible_sites()
            ],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _normalise_filters(self, filters: Mapping[str, Any]) -> Dict[str, Any]:
        normalised: Dict[str, Any] = {}

        for raw_key, value in filters.items():
            if value in (None, "", [], ()):
                continue

            mapped_key = self._FILTER_KEY_MAP.get(raw_key, raw_key)
            normalised[mapped_key] = value

        return normalised

    def _filter_by_category(self, tickets: QuerySet, category_value: Any) -> QuerySet:
        try:
            category_id = int(category_value)
        except (TypeError, ValueError):
            category_id = None

        if category_id:
            return tickets.filter(category_id=category_id)
        return tickets.filter(category__name=category_value)

    def _filter_by_site(self, tickets: QuerySet, site_value: Any, site_code_value: Any) -> QuerySet:
        site = site_value or site_code_value
        if site is None:
            return tickets

        try:
            site_id = int(site)
        except (TypeError, ValueError):
            site_id = None

        if site_id:
            return tickets.filter(asset_code_id=site_id)

        # Fallback to asset code match
        return tickets.filter(asset_code__asset_code=site)

    def _parse_date(self, value: Any) -> Optional[date]:
        if not value:
            return None

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned.endswith("Z"):
                cleaned = cleaned[:-1] + "+00:00"

            # Try YYYY-MM-DD
            try:
                return datetime.strptime(cleaned[:10], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass

            try:
                return datetime.fromisoformat(cleaned).date()
            except (ValueError, TypeError):
                return None

        return None

    def _serialize_applied_filters(self, filters: Mapping[str, Any]) -> Dict[str, Any]:
        applied = {
            "status": filters.get("status"),
            "priority": filters.get("priority"),
            "categoryId": self._safe_int(filters.get("category")),
            "siteId": self._safe_int(filters.get("site")),
            "siteCode": filters.get("site_code"),
            "dateFrom": filters.get("date_from"),
            "dateTo": filters.get("date_to"),
        }

        return {key: value for key, value in applied.items() if value is not None}

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _build_analytics_items(self, base_qs: QuerySet, view_by: str) -> List[Dict[str, Any]]:
        view_by = (view_by or "device_tickets").strip().lower()

        items: List[Dict[str, Any]] = []

        if view_by == "device_tickets":
            qs = (
                base_qs.exclude(device_id__isnull=True)
                .values(
                    "device_id",
                    "device_id__device_name",
                    "device_id__device_make",
                    "device_id__device_model",
                )
                .annotate(count=Count("id"), total_loss=Sum("loss_value"))
                .order_by("-count")
            )
            for record in qs:
                items.append(
                    {
                        "entity_key": record.get("device_id"),
                        "entity_type": "device",
                        "label": record.get("device_id__device_name") or "Unknown",
                        "sub_label": record.get("device_id__device_model")
                        or record.get("device_id__device_make")
                        or "",
                        "value": int(record.get("count") or 0),
                        "secondary": float(record.get("total_loss") or 0.0),
                    }
                )
        elif view_by == "device_loss":
            qs = (
                base_qs.exclude(device_id__isnull=True)
                .exclude(loss_value__isnull=True)
                .values("device_id", "device_id__device_name")
                .annotate(total_loss=Sum("loss_value"), count=Count("id"))
                .order_by("-total_loss")
            )
            for record in qs:
                items.append(
                    {
                        "entity_key": record.get("device_id"),
                        "entity_type": "device",
                        "label": record.get("device_id__device_name") or "Unknown",
                        "sub_label": "",
                        "value": float(record.get("total_loss") or 0.0),
                        "secondary": int(record.get("count") or 0),
                    }
                )
        elif view_by == "category_tickets":
            qs = (
                base_qs.values("category__id", "category__name")
                .annotate(count=Count("id"), total_loss=Sum("loss_value"))
                .order_by("-count")
            )
            for record in qs:
                items.append(
                    {
                        "entity_key": record.get("category__id"),
                        "entity_type": "category",
                        "label": record.get("category__name") or "Unclassified",
                        "sub_label": "",
                        "value": int(record.get("count") or 0),
                        "secondary": float(record.get("total_loss") or 0.0),
                    }
                )
        elif view_by == "category_loss":
            qs = (
                base_qs.exclude(loss_value__isnull=True)
                .values("category__id", "category__name")
                .annotate(total_loss=Sum("loss_value"), count=Count("id"))
                .order_by("-total_loss")
            )
            for record in qs:
                items.append(
                    {
                        "entity_key": record.get("category__id"),
                        "entity_type": "category",
                        "label": record.get("category__name") or "Unclassified",
                        "sub_label": "",
                        "value": float(record.get("total_loss") or 0.0),
                        "secondary": int(record.get("count") or 0),
                    }
                )
        elif view_by == "make_tickets":
            qs = (
                base_qs.exclude(device_id__isnull=True)
                .values("device_id__device_make")
                .annotate(count=Count("id"), total_loss=Sum("loss_value"))
                .order_by("-count")
            )
            for record in qs:
                make_value = record.get("device_id__device_make") or "Unknown"
                items.append(
                    {
                        "entity_key": make_value,
                        "entity_type": "make",
                        "label": make_value,
                        "sub_label": "",
                        "value": int(record.get("count") or 0),
                        "secondary": float(record.get("total_loss") or 0.0),
                    }
                )
        elif view_by == "model_tickets":
            qs = (
                base_qs.exclude(device_id__isnull=True)
                .values("device_id__device_model")
                .annotate(count=Count("id"), total_loss=Sum("loss_value"))
                .order_by("-count")
            )
            for record in qs:
                model_value = record.get("device_id__device_model") or "Unknown"
                items.append(
                    {
                        "entity_key": model_value,
                        "entity_type": "model",
                        "label": model_value,
                        "sub_label": "",
                        "value": int(record.get("count") or 0),
                        "secondary": float(record.get("total_loss") or 0.0),
                    }
                )
        else:
            raise ValueError("Invalid analytics view")

        return items

    def _get_trend_counts_for_entity(
        self,
        base_qs: QuerySet,
        entity_type: str,
        identifier: Any,
        days: int = 7,
    ) -> List[int]:
        today = timezone.now().date()
        results: List[int] = []

        for i in range(days - 1, -1, -1):
            query_date = today - timedelta(days=i)
            qs = base_qs.filter(created_at__date=query_date)

            if entity_type == "device":
                qs = qs.filter(device_id=identifier)
            elif entity_type == "category":
                try:
                    qs = qs.filter(category__id=int(identifier))
                except (ValueError, TypeError):
                    qs = qs.filter(category__name=identifier)
            elif entity_type == "make":
                qs = qs.filter(device_id__device_make=identifier)
            elif entity_type == "model":
                qs = qs.filter(device_id__device_model=identifier)

            results.append(qs.count())

        return results


