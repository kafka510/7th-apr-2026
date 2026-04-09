from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Ticket, TicketMaterial, TicketManpower
from ..services.detail_service import TicketDetailService
from .permissions import HasTicketingAccess
from .serializers import (
    TicketDetailSerializer,
    TicketTimelineSerializer,
    TicketCommentSerializer,
    TicketAttachmentSerializer,
    TicketMaterialSerializer,
    TicketMaterialCreateSerializer,
    TicketManpowerSerializer,
    TicketManpowerCreateSerializer,
)


class TicketDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, HasTicketingAccess]

    def get(self, request, pk):
        ticket = Ticket.objects.filter(pk=pk, is_active=True).select_related(
            "created_by", "updated_by", "assigned_to", "asset_code", "category", "sub_category"
        ).first()
        if not ticket:
            return Response({"detail": "Ticket not found"}, status=404)

        service = TicketDetailService(request.user, ticket)
        payload = service.get_ticket_detail()
        serializer = TicketDetailSerializer(payload)
        return Response(serializer.data)


class TicketTimelineAPIView(APIView):
    permission_classes = [IsAuthenticated, HasTicketingAccess]

    def get(self, request, pk):
        service = TicketDetailService.from_ticket_id(request.user, pk)
        if service is None:
            return Response({"detail": "Ticket not found"}, status=404)

        payload = service.get_timeline()
        serializer = TicketTimelineSerializer(payload, many=True)
        return Response(serializer.data)


class TicketCommentsAPIView(APIView):
    permission_classes = [IsAuthenticated, HasTicketingAccess]

    def get(self, request, pk):
        service = TicketDetailService.from_ticket_id(request.user, pk)
        if service is None:
            return Response({"detail": "Ticket not found"}, status=404)

        payload = service.get_comments()
        serializer = TicketCommentSerializer(payload, many=True)
        return Response(serializer.data)

    def post(self, request, pk):
        """Add a comment to the ticket"""
        from ..models import TicketComment
        from ..utils import log_ticket_activity, can_user_edit_ticket
        
        ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
        
        # Check permissions - user can comment if they can edit, are assigned, or are a watcher
        can_comment = (
            can_user_edit_ticket(request.user, ticket) or
            ticket.assigned_to == request.user or
            ticket.watchers.filter(id=request.user.id).exists()
        )
        
        if not can_comment:
            return Response({"detail": "You do not have permission to comment on this ticket"}, status=403)
        
        comment_text = request.data.get('comment', '').strip()
        is_internal = request.data.get('is_internal', False)
        
        if not comment_text:
            return Response({"detail": "Comment cannot be empty"}, status=400)
        
        # Create comment
        comment = TicketComment.objects.create(
            ticket=ticket,
            user=request.user,
            comment=comment_text,
            is_internal=is_internal
        )
        
        # Log activity
        log_ticket_activity(
            ticket=ticket,
            user=request.user,
            action_type='commented',
            notes=comment.comment[:100],
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Send notification
        from ..tasks import send_ticket_comment_notification
        send_ticket_comment_notification.delay(str(ticket.id), comment.id)
        
        # Return the created comment
        service = TicketDetailService(request.user, ticket)
        payload = service.get_comments()
        comment_data = next((c for c in payload if c['id'] == comment.id), None)
        if comment_data:
            serializer = TicketCommentSerializer(comment_data)
            return Response(serializer.data, status=201)
        else:
            # Fallback serialization
            return Response({
                "id": comment.id,
                "user": {"id": request.user.id, "username": request.user.username, "name": request.user.get_full_name() or request.user.username},
                "comment": comment.comment,
                "created_at": comment.created_at.isoformat(),
                "is_internal": comment.is_internal,
            }, status=201)


class TicketAttachmentsAPIView(APIView):
    permission_classes = [IsAuthenticated, HasTicketingAccess]

    def get(self, request, pk):
        service = TicketDetailService.from_ticket_id(request.user, pk)
        if service is None:
            return Response({"detail": "Ticket not found"}, status=404)

        payload = service.get_attachments()
        serializer = TicketAttachmentSerializer(payload, many=True)
        return Response(serializer.data)

    def post(self, request, pk):
        """Upload a file attachment to the ticket"""
        from ..models import TicketAttachment
        from ..utils import log_ticket_activity, can_user_edit_ticket
        import mimetypes
        
        ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
        
        # Check permissions - user can upload if they can edit or are assigned
        can_upload = (
            can_user_edit_ticket(request.user, ticket) or
            ticket.assigned_to == request.user
        )
        
        if not can_upload:
            return Response({"detail": "You do not have permission to upload files to this ticket"}, status=403)
        
        # Check if file is provided
        if 'file' not in request.FILES:
            return Response({"detail": "No file provided"}, status=400)
        
        file = request.FILES['file']
        
        # Validate file size (10MB max)
        max_size = 10 * 1024 * 1024  # 10MB
        if file.size > max_size:
            return Response({"detail": f"File size exceeds maximum allowed size of 10MB"}, status=400)
        
        # Create attachment
        attachment = TicketAttachment(
            ticket=ticket,
            uploaded_by=request.user,
            file=file,
            file_name=file.name,
            file_size=file.size,
        )
        
        # Get file type
        file_type, _ = mimetypes.guess_type(file.name)
        attachment.file_type = file_type or 'application/octet-stream'
        
        attachment.save()
        
        # Log activity
        log_ticket_activity(
            ticket=ticket,
            user=request.user,
            action_type='attachment_added',
            notes=f'File uploaded: {attachment.file_name}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Return the created attachment
        service = TicketDetailService(request.user, ticket)
        payload = service.get_attachments()
        attachment_data = next((a for a in payload if a['id'] == attachment.id), None)
        if attachment_data:
            serializer = TicketAttachmentSerializer(attachment_data)
            return Response(serializer.data, status=201)
        else:
            # Fallback serialization
            return Response({
                "id": attachment.id,
                "file_name": attachment.file_name,
                "file_url": attachment.file.url if attachment.file else "",
                "file_size": attachment.file_size,
                "file_type": attachment.file_type,
                "uploaded_by": {
                    "id": request.user.id,
                    "username": request.user.username,
                    "name": request.user.get_full_name() or request.user.username
                },
                "created_at": attachment.uploaded_at.isoformat(),
            }, status=201)


class TicketMaterialsAPIView(APIView):
    permission_classes = [IsAuthenticated, HasTicketingAccess]

    def get(self, request, pk):
        service = TicketDetailService.from_ticket_id(request.user, pk)
        if service is None:
            return Response({"detail": "Ticket not found"}, status=404)

        payload = service.get_materials()
        serializer = TicketMaterialSerializer(payload, many=True)
        return Response(serializer.data)

    def post(self, request, pk):
        from ..utils import can_user_edit_ticket, log_ticket_activity

        serializer = TicketMaterialCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        ticket = get_object_or_404(Ticket, pk=pk, is_active=True)

        can_manage = (
            can_user_edit_ticket(request.user, ticket)
            or ticket.assigned_to == request.user
            or ticket.watchers.filter(id=request.user.id).exists()
        )
        if not can_manage:
            return Response({"detail": "You do not have permission to add materials"}, status=403)

        material = TicketMaterial.objects.create(
            ticket=ticket,
            material_name=serializer.validated_data["material_name"],
            quantity=serializer.validated_data["quantity"],
            unit_price=serializer.validated_data["unit_price"],
        )

        log_ticket_activity(
            ticket=ticket,
            user=request.user,
            action_type='materials_updated',
            new_value={
                "material_name": material.material_name,
                "quantity": str(material.quantity),
                "unit_price": str(material.unit_price),
            },
            field_changed='materials',
            ip_address=request.META.get('REMOTE_ADDR')
        )

        payload = {
            "id": str(material.id),
            "material_name": material.material_name,
            "quantity": str(material.quantity),
            "unit_price": str(material.unit_price),
            "created_at": material.created_at.isoformat(),
            "updated_at": material.updated_at.isoformat(),
        }
        response_serializer = TicketMaterialSerializer(payload)
        return Response(response_serializer.data, status=201)


class TicketMaterialDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, HasTicketingAccess]

    def put(self, request, pk, material_id):
        from ..utils import can_user_edit_ticket, log_ticket_activity

        serializer = TicketMaterialCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
        material = get_object_or_404(TicketMaterial, pk=material_id, ticket=ticket)

        can_manage = (
            can_user_edit_ticket(request.user, ticket)
            or ticket.assigned_to == request.user
            or ticket.watchers.filter(id=request.user.id).exists()
        )
        if not can_manage:
            return Response({"detail": "You do not have permission to update materials"}, status=403)

        material.material_name = serializer.validated_data["material_name"]
        material.quantity = serializer.validated_data["quantity"]
        material.unit_price = serializer.validated_data["unit_price"]
        material.save()

        log_ticket_activity(
            ticket=ticket,
            user=request.user,
            action_type='materials_updated',
            new_value={
                "id": str(material.id),
                "material_name": material.material_name,
                "quantity": str(material.quantity),
                "unit_price": str(material.unit_price),
            },
            field_changed='materials',
            ip_address=request.META.get('REMOTE_ADDR')
        )

        payload = {
            "id": str(material.id),
            "material_name": material.material_name,
            "quantity": str(material.quantity),
            "unit_price": str(material.unit_price),
            "created_at": material.created_at.isoformat(),
            "updated_at": material.updated_at.isoformat(),
        }
        response_serializer = TicketMaterialSerializer(payload)
        return Response(response_serializer.data)

    def delete(self, request, pk, material_id):
        from ..utils import log_ticket_activity

        if not request.user.is_superuser:
            return Response({"detail": "Only superusers can delete materials"}, status=403)

        ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
        material = get_object_or_404(TicketMaterial, pk=material_id, ticket=ticket)

        log_ticket_activity(
            ticket=ticket,
            user=request.user,
            action_type='materials_updated',
            old_value={
                "id": str(material.id),
                "material_name": material.material_name,
            },
            field_changed='materials',
            notes='Material deleted',
            ip_address=request.META.get('REMOTE_ADDR')
        )

        material.delete()
        return Response(status=204)


class TicketManpowerAPIView(APIView):
    permission_classes = [IsAuthenticated, HasTicketingAccess]

    def get(self, request, pk):
        service = TicketDetailService.from_ticket_id(request.user, pk)
        if service is None:
            return Response({"detail": "Ticket not found"}, status=404)

        payload = service.get_manpower()
        serializer = TicketManpowerSerializer(payload, many=True)
        return Response(serializer.data)

    def post(self, request, pk):
        from ..utils import can_user_edit_ticket, log_ticket_activity

        serializer = TicketManpowerCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        ticket = get_object_or_404(Ticket, pk=pk, is_active=True)

        can_manage = (
            can_user_edit_ticket(request.user, ticket)
            or ticket.assigned_to == request.user
            or ticket.watchers.filter(id=request.user.id).exists()
        )
        if not can_manage:
            return Response({"detail": "You do not have permission to add manpower records"}, status=403)

        entry = TicketManpower.objects.create(
            ticket=ticket,
            person_name=serializer.validated_data["person_name"],
            hours_worked=serializer.validated_data["hours_worked"],
            hourly_rate=serializer.validated_data["hourly_rate"],
        )

        log_ticket_activity(
            ticket=ticket,
            user=request.user,
            action_type='manpower_updated',
            new_value={
                "person_name": entry.person_name,
                "hours_worked": str(entry.hours_worked),
                "hourly_rate": str(entry.hourly_rate),
            },
            field_changed='manpower',
            ip_address=request.META.get('REMOTE_ADDR')
        )

        payload = {
            "id": str(entry.id),
            "person_name": entry.person_name,
            "hours_worked": str(entry.hours_worked),
            "hourly_rate": str(entry.hourly_rate),
            "created_at": entry.created_at.isoformat(),
            "updated_at": entry.updated_at.isoformat(),
        }
        response_serializer = TicketManpowerSerializer(payload)
        return Response(response_serializer.data, status=201)


class TicketManpowerDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, HasTicketingAccess]

    def put(self, request, pk, manpower_id):
        from ..utils import can_user_edit_ticket, log_ticket_activity

        serializer = TicketManpowerCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
        entry = get_object_or_404(TicketManpower, pk=manpower_id, ticket=ticket)

        can_manage = (
            can_user_edit_ticket(request.user, ticket)
            or ticket.assigned_to == request.user
            or ticket.watchers.filter(id=request.user.id).exists()
        )
        if not can_manage:
            return Response({"detail": "You do not have permission to update manpower records"}, status=403)

        entry.person_name = serializer.validated_data["person_name"]
        entry.hours_worked = serializer.validated_data["hours_worked"]
        entry.hourly_rate = serializer.validated_data["hourly_rate"]
        entry.save()

        log_ticket_activity(
            ticket=ticket,
            user=request.user,
            action_type='manpower_updated',
            new_value={
                "id": str(entry.id),
                "person_name": entry.person_name,
                "hours_worked": str(entry.hours_worked),
                "hourly_rate": str(entry.hourly_rate),
            },
            field_changed='manpower',
            ip_address=request.META.get('REMOTE_ADDR')
        )

        payload = {
            "id": str(entry.id),
            "person_name": entry.person_name,
            "hours_worked": str(entry.hours_worked),
            "hourly_rate": str(entry.hourly_rate),
            "created_at": entry.created_at.isoformat(),
            "updated_at": entry.updated_at.isoformat(),
        }
        response_serializer = TicketManpowerSerializer(payload)
        return Response(response_serializer.data)

    def delete(self, request, pk, manpower_id):
        from ..utils import log_ticket_activity

        if not request.user.is_superuser:
            return Response({"detail": "Only superusers can delete manpower records"}, status=403)

        ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
        entry = get_object_or_404(TicketManpower, pk=manpower_id, ticket=ticket)

        log_ticket_activity(
            ticket=ticket,
            user=request.user,
            action_type='manpower_updated',
            old_value={
                "id": str(entry.id),
                "person_name": entry.person_name,
            },
            field_changed='manpower',
            notes='Manpower record deleted',
            ip_address=request.META.get('REMOTE_ADDR')
        )

        entry.delete()
        return Response(status=204)


class TicketAssignAPIView(APIView):
    """Assign or unassign a ticket to a user"""
    permission_classes = [IsAuthenticated, HasTicketingAccess]

    def post(self, request, pk):
        from ..utils import can_user_assign_ticket, log_ticket_activity
        from django.contrib.auth.models import User
        
        ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
        
        assigned_to_id = request.data.get('assigned_to')
        old_assigned_to = ticket.assigned_to
        
        # Check permissions based on action
        if assigned_to_id:
            # Assigning: ticket creator or users with assign capability can assign
            can_assign = can_user_assign_ticket(request.user) or ticket.created_by == request.user
            if not can_assign:
                return Response({"detail": "You do not have permission to assign tickets"}, status=403)
        else:
            # Removing assignment: only users with remove_assignee capability can remove
            from main.permissions import user_has_capability
            can_remove = user_has_capability(request.user, 'ticketing.remove_assignee') or request.user.is_superuser
            if not can_remove:
                return Response({"detail": "You do not have permission to remove ticket assignments. You need the 'ticketing.remove_assignee' capability."}, status=403)
        
        if assigned_to_id:
            try:
                assigned_user = User.objects.get(id=assigned_to_id, is_active=True)
                ticket.assigned_to = assigned_user
            except User.DoesNotExist:
                return Response({"detail": "User not found"}, status=400)
        else:
            ticket.assigned_to = None
        
        ticket.save()
        
        # Log activity
        log_ticket_activity(
            ticket=ticket,
            user=request.user,
            action_type='assigned',
            old_value={'assigned_to': str(old_assigned_to) if old_assigned_to else None},
            new_value={'assigned_to': str(ticket.assigned_to) if ticket.assigned_to else None},
            field_changed='assigned_to',
            notes=request.data.get('notes', ''),
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Send notification
        if ticket.assigned_to:
            from ..tasks import send_ticket_assignment_notification
            send_ticket_assignment_notification.delay(str(ticket.id), ticket.assigned_to.id)
        
        # Return updated ticket detail
        service = TicketDetailService(request.user, ticket)
        payload = service.get_ticket_detail()
        serializer = TicketDetailSerializer(payload)
        return Response(serializer.data)


class TicketDeleteAPIView(APIView):
    """Delete a single ticket (superuser only)"""
    permission_classes = [IsAuthenticated, HasTicketingAccess]

    def delete(self, request, pk):
        from django.db import transaction
        
        if not request.user.is_superuser:
            return Response({"detail": "Only superusers can delete tickets"}, status=403)
        
        ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
        
        try:
            with transaction.atomic():
                # Delete associated files
                from ..models import TicketAttachment
                for attachment in ticket.attachments.all():
                    if attachment.file:
                        try:
                            attachment.file.delete(save=False)
                        except Exception:
                            pass
                
                # Cascade delete related objects
                ticket.watchers.clear()
                ticket.comments.all().delete()
                ticket.activities.all().delete()
                ticket.attachments.all().delete()
                
                # Delete the ticket
                ticket.delete()
                
                return Response({
                    "success": True,
                    "message": f"Ticket {ticket.ticket_number} deleted successfully"
                })
        except Exception as e:
            return Response({"detail": f"Error deleting ticket: {str(e)}"}, status=500)


class TicketWatchersAPIView(APIView):
    """Manage watchers for a ticket"""
    permission_classes = [IsAuthenticated, HasTicketingAccess]

    def post(self, request, pk):
        from ..utils import can_user_manage_watchers, log_ticket_activity
        from django.contrib.auth.models import User
        
        ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
        
        watcher_ids = request.data.get('watchers', [])
        
        if not isinstance(watcher_ids, list):
            return Response({"detail": "watchers must be a list"}, status=400)
        
        # Get current and new watchers
        old_watchers = list(ticket.watchers.all())
        old_watcher_ids = {w.id for w in old_watchers}
        new_watcher_ids = {int(wid) for wid in watcher_ids}
        removed_watcher_ids = old_watcher_ids - new_watcher_ids
        
        # Check permissions based on action
        if removed_watcher_ids:
            # Removing watchers: only users with remove_watchers capability can remove
            from main.permissions import user_has_capability
            can_remove = user_has_capability(request.user, 'ticketing.remove_watchers') or request.user.is_superuser
            if not can_remove:
                return Response({"detail": "You do not have permission to remove watchers. You need the 'ticketing.remove_watchers' capability."}, status=403)
        else:
            # Adding watchers: ticket creator or users with manage watchers capability can add
            can_manage = can_user_manage_watchers(request.user) or ticket.created_by == request.user
            if not can_manage:
                return Response({"detail": "You do not have permission to manage watchers"}, status=403)
        
        # Get watcher users
        watchers = User.objects.filter(id__in=watcher_ids, is_active=True)
        ticket.watchers.set(watchers)
        
        # Log activity
        log_ticket_activity(
            ticket=ticket,
            user=request.user,
            action_type='watchers_updated',
            old_value={'watchers': [str(w) for w in old_watchers]},
            new_value={'watchers': [str(w) for w in watchers]},
            field_changed='watchers',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Return updated ticket detail
        service = TicketDetailService(request.user, ticket)
        payload = service.get_ticket_detail()
        serializer = TicketDetailSerializer(payload)
        return Response(serializer.data)


class TicketStatusChangeAPIView(APIView):
    """Change ticket status"""
    permission_classes = [IsAuthenticated, HasTicketingAccess]

    def post(self, request, pk):
        from ..utils import log_ticket_activity, can_user_edit_ticket
        from main.permissions import user_has_capability
        
        ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
        
        # Check if user has access to this ticket
        if not can_user_edit_ticket(request.user, ticket):
            # Allow if user is assigned or is a watcher
            if not (ticket.assigned_to == request.user or ticket.watchers.filter(id=request.user.id).exists()):
                return Response({"detail": "You do not have permission to change status for this ticket"}, status=403)
        
        new_status = request.data.get('status')
        notes = request.data.get('notes', '').strip()
        
        if not new_status:
            return Response({"detail": "Status is required"}, status=400)
        
        # Validate status
        valid_statuses = [choice[0] for choice in Ticket.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response({"detail": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}, status=400)
        
        old_status = ticket.status
        
        # Check permissions for closing tickets
        can_close_any = user_has_capability(request.user, 'ticketing.close_any') or request.user.is_superuser
        if new_status == 'closed' and not can_close_any:
            return Response({"detail": "Only administrators can close tickets"}, status=403)
        
        # Don't do anything if status hasn't changed
        if old_status == new_status:
            service = TicketDetailService(request.user, ticket)
            payload = service.get_ticket_detail()
            serializer = TicketDetailSerializer(payload)
            return Response(serializer.data)
        
        # Update status
        ticket.status = new_status
        
        # Set closed_at if closing
        if new_status == 'closed' and not ticket.closed_at:
            from django.utils import timezone
            ticket.closed_at = timezone.now()
            ticket.closed_by = request.user
        elif new_status != 'closed':
            ticket.closed_at = None
            ticket.closed_by = None
        
        ticket.save()
        
        # Log activity
        log_ticket_activity(
            ticket=ticket,
            user=request.user,
            action_type='status_changed',
            old_value={'status': old_status},
            new_value={'status': new_status},
            field_changed='status',
            notes=notes,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Send notification
        from ..tasks import send_ticket_status_changed_notification
        send_ticket_status_changed_notification.delay(str(ticket.id), old_status, new_status)
        
        # Return updated ticket detail
        service = TicketDetailService(request.user, ticket)
        payload = service.get_ticket_detail()
        serializer = TicketDetailSerializer(payload)
        return Response(serializer.data)




