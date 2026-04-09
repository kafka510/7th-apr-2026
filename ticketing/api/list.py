from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from ..services import TicketListService
from .permissions import HasTicketingAccess
from .serializers import TicketListFiltersSerializer, TicketListItemSerializer


class TicketListPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class TicketListAPIView(APIView):
    """Lists tickets with filtering, sorting, and pagination for the React client."""

    permission_classes = [IsAuthenticated, HasTicketingAccess]
    pagination_class = TicketListPagination

    def get(self, request):
        service = TicketListService(request.user)
        params = self._parse_params(request)

        queryset = service.get_queryset(params)
        summary = service.build_summary(queryset)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)

        serialized_items = service.serialize_ticket_list_items(page)
        serializer = TicketListItemSerializer(serialized_items, many=True)
        response = paginator.get_paginated_response(serializer.data)

        response.data["summary"] = summary
        # Add permissions for current user
        response.data["permissions"] = {
            "canDelete": request.user.is_superuser,
        }

        if request.query_params.get("include_filters") == "1":
            filter_serializer = TicketListFiltersSerializer(service.get_filter_options())
            response.data["filterOptions"] = filter_serializer.data

        return response

    def _parse_params(self, request):
        params = {
            "status": request.query_params.getlist("status"),
            "priority": request.query_params.getlist("priority"),
            "category": request.query_params.getlist("category"),
            "site": request.query_params.getlist("site"),
            "assigned_to": request.query_params.get("assigned_to"),
            "asset_number": request.query_params.getlist("asset_number"),
            "search": request.query_params.get("search"),
            "sort": request.query_params.get("sort"),
            "order": request.query_params.get("order"),
            "date_from": request.query_params.get("date_from"),
            "date_to": request.query_params.get("date_to"),
        }

        return params

    def delete(self, request):
        """Bulk delete tickets (superuser only)"""
        if not request.user.is_superuser:
            return Response({"detail": "Only superusers can delete tickets"}, status=403)
        
        from ..models import Ticket
        from django.db import transaction
        
        ticket_ids = request.data.get('ticket_ids', [])
        if not isinstance(ticket_ids, list) or not ticket_ids:
            return Response({"detail": "ticket_ids must be a non-empty list"}, status=400)
        
        try:
            with transaction.atomic():
                tickets = Ticket.objects.filter(id__in=ticket_ids, is_active=True)
                deleted_count = tickets.count()
                
                # Delete associated files and records
                for ticket in tickets:
                    # Delete attachments
                    from ..models import TicketAttachment
                    attachments = TicketAttachment.objects.filter(ticket=ticket)
                    for attachment in attachments:
                        if attachment.file:
                            try:
                                attachment.file.delete(save=False)
                            except Exception:
                                pass
                    attachments.delete()
                    
                    # Delete comments
                    from ..models import TicketComment
                    TicketComment.objects.filter(ticket=ticket).delete()
                    
                    # Delete activities
                    from ..models import TicketActivity
                    TicketActivity.objects.filter(ticket=ticket).delete()
                    
                    # Delete watchers relationship
                    ticket.watchers.clear()
                
                # Delete tickets
                tickets.delete()
                
                return Response({
                    "success": True,
                    "deleted_count": deleted_count,
                    "message": f"Successfully deleted {deleted_count} ticket(s)"
                })
        except Exception as e:
            return Response({"detail": f"Error deleting tickets: {str(e)}"}, status=500)


