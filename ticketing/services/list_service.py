from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from ..models import Ticket, TicketCategory, TicketSubCategory
from ..utils import get_accessible_sites_for_user, get_user_display_name
from main.permissions import user_has_capability

User = get_user_model()


class TicketListService:
    """Encapsulates ticket list filtering, sorting, and metadata generation."""

    SORT_MAP: Dict[str, str] = {
        "ticket": "ticket_number",
        "site": "asset_code__asset_name",
        "category": "category__name",
        "priority": "priority",
        "status": "status",
        "created": "created_at",
        "assigned": "assigned_to__username",
        "closed": "closed_at",
    }

    def __init__(self, user):
        self.user = user
        self._accessible_sites = None

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def get_queryset(self, params: Optional[Mapping[str, Any]] = None) -> QuerySet:
        params = params or {}
        queryset = (
            Ticket.objects.filter(is_active=True)
            .select_related(
                "asset_code",
                "device_id",
                "created_by",
                "assigned_to",
                "sub_category",
                "category",
                "loss_category",
            )
            .prefetch_related("watchers")
        )

        queryset = self._apply_access_controls(queryset)
        queryset = self._apply_filters(queryset, params)
        queryset = self._apply_search(queryset, params.get("search"))
        queryset = self._apply_sort(queryset, params.get("sort"), params.get("order"))

        return queryset

    # ------------------------------------------------------------------
    # Filter metadata
    # ------------------------------------------------------------------
    def get_filter_options(self) -> Dict[str, Iterable[Dict[str, Any]]]:
        categories = TicketCategory.objects.filter(is_active=True).order_by("display_order", "name")
        assignees = (
            Ticket.objects.filter(
                is_active=True,
                assigned_to__isnull=False,
                asset_code__in=self._accessible_sites_queryset(),
            )
            .values(
                "assigned_to_id",
                "assigned_to__username",
                "assigned_to__first_name",
                "assigned_to__last_name",
            )
            .distinct()
        )

        # Get unique asset numbers from accessible sites
        accessible_sites = self._accessible_sites_queryset()
        asset_numbers = (
            accessible_sites.values("asset_number")
            .distinct()
            .exclude(asset_number__isnull=True)
            .exclude(asset_number="")
        )

        return {
            "statusOptions": [
                {"value": value, "label": label}
                for value, label in Ticket.STATUS_CHOICES
            ],
            "priorityOptions": [
                {"value": value, "label": label}
                for value, label in Ticket.PRIORITY_CHOICES
            ],
            "categoryOptions": [
                {"value": str(category.id), "label": category.name}
                for category in categories
            ],
            "subCategoryOptions": [
                {
                    "value": str(sub.id),
                    "label": sub.name,
                    "category": str(sub.category_id),
                }
                for sub in TicketSubCategory.objects.filter(is_active=True, category__is_active=True).order_by("category__display_order", "display_order", "name")
            ],
            "siteOptions": [
                {
                    "value": site.asset_code,
                    "label": site.asset_name,
                    "assetCode": site.asset_code,
                    "assetNumber": site.asset_number if hasattr(site, 'asset_number') and site.asset_number else None,
                    "country": getattr(site, "country", None),
                    "portfolio": getattr(site, "portfolio", None),
                }
                for site in accessible_sites
            ],
            "assigneeOptions": [
                {
                    "value": str(entry["assigned_to_id"]),
                    "label": self._format_user_name(entry),
                }
                for entry in assignees
            ],
            "assetNumberOptions": [
                {
                    "value": entry["asset_number"],
                    "label": entry["asset_number"],
                }
                for entry in asset_numbers
            ],
        }

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------
    def serialize_ticket_list_items(self, tickets: Iterable[Ticket]) -> List[Dict[str, Any]]:
        data: List[Dict[str, Any]] = []
        for ticket in tickets:
            data.append(
                {
                    "id": ticket.id,
                    "ticket_number": ticket.ticket_number,
                    "title": ticket.title,
                    "status": ticket.status,
                    "status_display": ticket.get_status_display(),
                    "priority": ticket.priority,
                    "priority_display": ticket.get_priority_display(),
                    "category": ticket.category.name if ticket.category else None,
                    "sub_category": ticket.sub_category.name if ticket.sub_category else None,
                    "asset_code": ticket.asset_code_id if ticket.asset_code_id else None,
                    "asset_name": ticket.asset_code.asset_name if ticket.asset_code else None,
                    "asset_number": ticket.asset_code.asset_number if ticket.asset_code else None,
                    "assigned_to_id": ticket.assigned_to_id,
                    "assigned_to": get_user_display_name(ticket.assigned_to)
                    if ticket.assigned_to
                    else None,
                    "created_at": ticket.created_at,
                    "updated_at": ticket.updated_at,
                }
            )
        return data

    def build_summary(self, queryset: QuerySet) -> Dict[str, Any]:
        aggregates = queryset.aggregate(
            total=Count("id"),
            open=Count("id", filter=~Q(status__in=["closed", "cancelled"])),
            awaiting_approval=Count("id", filter=Q(status="waiting_for_approval")),
            unassigned=Count("id", filter=Q(assigned_to__isnull=True)),
            critical=Count("id", filter=Q(priority="critical")),
        )

        status_counts = {
            entry["status"]: entry["count"]
            for entry in queryset.values("status").annotate(count=Count("id"))
        }

        status_breakdown = [
            {
                "status": status_key,
                "label": label,
                "count": status_counts.get(status_key, 0),
            }
            for status_key, label in Ticket.STATUS_CHOICES
        ]

        return {
            "generatedAt": timezone.now().isoformat(),
            "total": aggregates.get("total", 0) or 0,
            "open": aggregates.get("open", 0) or 0,
            "awaitingApproval": aggregates.get("awaiting_approval", 0) or 0,
            "unassigned": aggregates.get("unassigned", 0) or 0,
            "critical": aggregates.get("critical", 0) or 0,
            "statusBreakdown": status_breakdown,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _accessible_sites_queryset(self):
        if self._accessible_sites is None:
            self._accessible_sites = get_accessible_sites_for_user(self.user)
        return self._accessible_sites

    def _apply_access_controls(self, queryset: QuerySet) -> QuerySet:
        if user_has_capability(self.user, "ticketing.view_all_tickets"):
            return queryset

        accessible_sites = self._accessible_sites_queryset()
        return queryset.filter(
            Q(created_by=self.user)
            | Q(assigned_to=self.user)
            | Q(watchers=self.user)
        ).filter(asset_code__in=accessible_sites).distinct()

    def _apply_filters(self, queryset: QuerySet, params: Mapping[str, Any]) -> QuerySet:
        status_list = self._as_list(params.get("statuses") or params.get("status"))
        if status_list:
            queryset = queryset.filter(status__in=status_list)

        priority_list = self._as_list(params.get("priorities") or params.get("priority"))
        if priority_list:
            queryset = queryset.filter(priority__in=priority_list)

        category_list = self._as_list(params.get("categories") or params.get("category"))
        if category_list:
            queryset = queryset.filter(category_id__in=category_list)

        site_list = self._as_list(params.get("sites") or params.get("site"))
        if site_list:
            queryset = queryset.filter(asset_code_id__in=site_list)

        assignees = self._as_list(params.get("assignees") or params.get("assigned_to"))
        if assignees:
            queryset = queryset.filter(assigned_to_id__in=assignees)

        asset_number_list = self._as_list(params.get("asset_numbers") or params.get("asset_number"))
        if asset_number_list:
            queryset = queryset.filter(asset_code__asset_number__in=asset_number_list)

        date_from = params.get("date_from") or params.get("dateFrom")
        if date_from:
            parsed = self._parse_date(date_from)
            if parsed:
                queryset = queryset.filter(created_at__date__gte=parsed)

        date_to = params.get("date_to") or params.get("dateTo")
        if date_to:
            parsed = self._parse_date(date_to)
            if parsed:
                queryset = queryset.filter(created_at__date__lte=parsed)

        return queryset

    def _apply_search(self, queryset: QuerySet, search: Optional[str]) -> QuerySet:
        if not search:
            return queryset

        search = search.strip()
        if not search:
            return queryset

        return queryset.filter(
            Q(ticket_number__icontains=search)
            | Q(title__icontains=search)
            | Q(description__icontains=search)
        )

    def _apply_sort(self, queryset: QuerySet, sort: Optional[str], order: Optional[str]) -> QuerySet:
        if not sort:
            return queryset.order_by("-created_at")

        sort_key = self.SORT_MAP.get(sort)
        if not sort_key:
            return queryset.order_by("-created_at")

        if order == "desc":
            sort_key = f"-{sort_key}"

        return queryset.order_by(sort_key)

    @staticmethod
    def _as_list(value: Any) -> Iterable[str]:
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return [str(value)]

    @staticmethod
    def _parse_date(input_value: Any):
        if not input_value:
            return None
        if isinstance(input_value, datetime):
            return input_value.date()
        try:
            return datetime.fromisoformat(str(input_value)).date()
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _format_user_name(entry: Mapping[str, Any]) -> str:
        first = (entry.get("assigned_to__first_name") or "").strip()
        last = (entry.get("assigned_to__last_name") or "").strip()
        if first or last:
            return f"{first} {last}".strip()
        return entry.get("assigned_to__username") or ""


