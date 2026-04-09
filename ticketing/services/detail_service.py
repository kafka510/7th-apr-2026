from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Iterable, Optional

from django.contrib.auth import get_user_model
from django.db.models import Prefetch

from ..models import (
    Ticket,
    TicketActivity,
    TicketAttachment,
    TicketComment,
    TicketMaterial,
    TicketManpower,
)
from ..utils import can_user_assign_ticket, can_user_edit_ticket, can_user_manage_watchers, get_user_display_name
from main.permissions import user_has_capability

if TYPE_CHECKING:
    from django.contrib.auth.models import User
else:
    User = get_user_model()


class TicketDetailService:
    """Provides ticket detail payloads for React detail view."""

    def __init__(self, user: User, ticket: Ticket):
        self.user = user
        self.ticket = ticket

    @classmethod
    def from_ticket_id(cls, user: User, ticket_id: str) -> Optional["TicketDetailService"]:
        try:
            ticket = (
                Ticket.objects.filter(pk=ticket_id, is_active=True)
                .select_related(
                    "created_by",
                    "assigned_to",
                    "updated_by",
                    "asset_code",
                    "category",
                    "sub_category",
                    "loss_category",
                )
                .prefetch_related(
                    Prefetch("watchers", queryset=User.objects.only("id", "username", "first_name", "last_name"))
                )
                .get()
            )
        except Ticket.DoesNotExist:
            return None

        return cls(user, ticket)

    # ------------------------------------------------------------------
    # Core payload builders
    # ------------------------------------------------------------------
    def get_ticket_detail(self) -> Dict[str, Any]:
        ticket = self.ticket

        return {
            "id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "title": ticket.title,
            "description": ticket.description,
            "status": ticket.status,
            "status_display": ticket.get_status_display(),
            "priority": ticket.priority,
            "priority_display": ticket.get_priority_display(),
            "category": ticket.category.name if ticket.category else None,
            "sub_category": self._subcategory_payload(ticket.sub_category),
            "loss_category": ticket.loss_category.name if ticket.loss_category else None,
            "asset_code": ticket.asset_code.asset_code if ticket.asset_code else None,
            "asset_name": ticket.asset_code.asset_name if ticket.asset_code else None,
            "assigned_to": self._user_payload(ticket.assigned_to),
            "created_by": self._user_payload(ticket.created_by),
            "updated_by": self._user_payload(ticket.updated_by),
            "watchers": [self._user_payload(watcher) for watcher in ticket.watchers.all()],
            "created_at": ticket.created_at.isoformat(),
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
            "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
            "metadata": ticket.metadata or {},
            "permissions": {
                "canEdit": can_user_edit_ticket(self.user, ticket),
                "canAssign": can_user_assign_ticket(self.user) or ticket.created_by == self.user,
                "canManageWatchers": can_user_manage_watchers(self.user) or ticket.created_by == self.user,
                "canComment": (
                    can_user_edit_ticket(self.user, ticket) or
                    ticket.assigned_to == self.user or
                    ticket.watchers.filter(id=self.user.id).exists()
                ),
                "canRemoveAssignee": user_has_capability(self.user, 'ticketing.remove_assignee') or self.user.is_superuser,
                "canRemoveWatchers": user_has_capability(self.user, 'ticketing.remove_watchers') or self.user.is_superuser,
                "canDelete": self.user.is_superuser,
            },
            "materials": self.get_materials(),
            "manpower": self.get_manpower(),
        }

    def get_timeline(self) -> Iterable[Dict[str, Any]]:
        activities = (
            TicketActivity.objects.filter(ticket=self.ticket)
            .select_related("user")
            .order_by("-timestamp")
        )

        return [
            {
                "id": activity.id,
                "user": self._user_payload(activity.user),
                "action": activity.action_type,
                "field": activity.field_changed,
                "old_value": activity.old_value,
                "new_value": activity.new_value,
                "notes": activity.notes,
                "created_at": activity.timestamp.isoformat(),
            }
            for activity in activities
        ]

    def get_comments(self) -> Iterable[Dict[str, Any]]:
        comments = (
            TicketComment.objects.filter(ticket=self.ticket)
            .select_related("user")
            .order_by("-created_at")
        )

        return [
            {
                "id": comment.id,
                "user": self._user_payload(comment.user),
                "comment": comment.comment,
                "created_at": comment.created_at.isoformat(),
                "is_internal": comment.is_internal,
            }
            for comment in comments
        ]

    def get_attachments(self) -> Iterable[Dict[str, Any]]:
        attachments = TicketAttachment.objects.filter(ticket=self.ticket).order_by("-uploaded_at")
        return [
            {
                "id": attachment.id,
                "file_name": attachment.file_name,
                "file_url": attachment.file.url if attachment.file else "",
                "file_size": attachment.file_size,
                "file_type": attachment.file_type,
                "uploaded_by": self._user_payload(attachment.uploaded_by),
                "created_at": attachment.uploaded_at.isoformat(),
            }
            for attachment in attachments
        ]

    def get_materials(self) -> Iterable[Dict[str, Any]]:
        materials = TicketMaterial.objects.filter(ticket=self.ticket).order_by("-created_at")
        return [
            {
                "id": str(material.id),
                "material_name": material.material_name,
                "quantity": str(material.quantity),
                "unit_price": str(material.unit_price),
                "created_at": material.created_at.isoformat(),
                "updated_at": material.updated_at.isoformat(),
            }
            for material in materials
        ]

    def get_manpower(self) -> Iterable[Dict[str, Any]]:
        entries = TicketManpower.objects.filter(ticket=self.ticket).order_by("-created_at")
        return [
            {
                "id": str(entry.id),
                "person_name": entry.person_name,
                "hours_worked": str(entry.hours_worked),
                "hourly_rate": str(entry.hourly_rate),
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat(),
            }
            for entry in entries
        ]

    # ------------------------------------------------------------------
    # Helper payload builders
    # ------------------------------------------------------------------
    @staticmethod
    def _user_payload(user: Optional[User]) -> Optional[Dict[str, Any]]:
        if user is None:
            return None

        return {
            "id": user.id,
            "username": user.username,
            "name": get_user_display_name(user),
        }

    @staticmethod
    def _subcategory_payload(sub_category) -> Optional[Dict[str, Any]]:
        if sub_category is None:
            return None
        return {
            "id": sub_category.id,
            "name": sub_category.name,
            "category_id": sub_category.category_id,
        }



