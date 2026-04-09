"""
ViewSet for Feedback API v2.
Provides standardized endpoints for Feedback React app.
"""
import json

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import JsonResponse

from shared_app.permissions.base_permissions import HasFeaturePermission


class HasFeedbackAdminAccess(HasFeaturePermission):
    """
    Admins (user_management feature) for managing feedback list / mark-attended / delete.
    """

    required_feature = "user_management"


class FeedbackViewSet(viewsets.ViewSet):
    """
    Standardized v2 endpoints for the Feedback React app.

    - Any authenticated user can submit feedback.
    - Only admins (user_management feature) can list / mark attended / delete.
    """

    def get_permissions(self):
        # Submit: any authenticated user; others: user_management admins
        if getattr(self, "action", None) in {"list_feedback", "mark_attended", "delete"}:
            return [IsAuthenticated(), HasFeedbackAdminAccess()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["get"], url_path="list")
    def list_feedback(self, request):
        """
        Wrap `api_feedback_list` into:
            GET /api/v2/main/feedback/list/
        """
        try:
            from main.views.feedback_views import api_feedback_list

            response = api_feedback_list(request)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode("utf-8"))
                return Response(data, status=response.status_code)
            return response
        except Exception as exc:  # pragma: no cover
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["post"], url_path="submit")
    def submit(self, request):
        """
        Create feedback entry for the current user (JSON-only).

        This mirrors the logic of `feedback_submit_view` but avoids
        template rendering and redirects, returning JSON consistently.
        """
        try:
            from django.utils import timezone
            from main.models import Feedback, FeedbackImage

            subject = (request.data.get("subject") or "").strip()
            message = (request.data.get("message") or "").strip()
            if not subject or not message:
                return Response(
                    {"success": False, "error": "Subject and message are required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            feedback = Feedback.objects.create(
                user=request.user,
                user_email=request.user.email,
                subject=subject,
                message=message,
                created_at=timezone.now(),
            )

            # Handle multiple images
            images = request.FILES.getlist("images")
            for image in images:
                if image:
                    FeedbackImage.objects.create(feedback=feedback, image=image)

            return Response(
                {
                    "success": True,
                    "message": "Thank you for your feedback! It has been submitted successfully.",
                    "close_modal": True,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as exc:  # pragma: no cover
            return Response(
                {"success": False, "error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="mark-attended")
    def mark_attended(self, request, pk=None):
        """
        Wrap `mark_feedback_attended` into:
            POST /api/v2/main/feedback/{id}/mark-attended/
        """
        try:
            from main.views.feedback_views import mark_feedback_attended

            response = mark_feedback_attended(request, pk)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode("utf-8"))
                return Response(data, status=response.status_code)
            return response
        except Exception as exc:  # pragma: no cover
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["post"], url_path="delete")
    def delete(self, request, pk=None):
        """
        Wrap `delete_feedback` into:
            POST /api/v2/main/feedback/{id}/delete/
        """
        try:
            from main.views.feedback_views import delete_feedback

            response = delete_feedback(request, pk)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode("utf-8"))
                return Response(data, status=response.status_code)
            return response
        except Exception as exc:  # pragma: no cover
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

{
  "cells": [],
  "metadata": {
    "language_info": {
      "name": "python"
    }
  },
  "nbformat": 4,
  "nbformat_minor": 2
}