"""
Shared app views
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, FileResponse
from django.conf import settings
from urllib.parse import urlparse
import uuid
import os
import json
import logging

from .tasks import export_dashboard_task, get_task_status, TASK_STATUS_PREFIX, TASK_CACHE_TIMEOUT

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def export_dashboard(request):
    """
    Create async export task for dashboard screenshot
    POST /api/export/dashboard/
    
    Body: {
        "url": "dashboard_url",
        "format": "png" | "pdf",
        "route": "optional route path",
        "activeTab": "optional tab id",
        "filters": {optional filter object}
    }
    
    Returns: {
        "task_id": "uuid",
        "status": "pending"
    }
    
    Security:
    - Requires authentication
    - Same-origin URL validation
    """
    try:
        # ---------------------------------------------------------
        # 1. Parse request body
        # ---------------------------------------------------------
        try:
            body = json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse(
                {"success": False, "error": "Invalid JSON in request body"},
                status=400,
            )

        dashboard_url = body.get("url")
        format_type = body.get("format", "png").lower()
        active_tab = body.get("activeTab", "")
        route_path = body.get("route", "")
        filters = body.get("filters", {})
        
        # Convert filters dict to JSON string
        filters_json = json.dumps(filters) if filters else ""

        if not dashboard_url:
            return JsonResponse(
                {"success": False, "error": "Missing url parameter"},
                status=400,
            )

        if format_type not in ("png", "pdf"):
            return JsonResponse(
                {"success": False, "error": 'Invalid format. Use "png" or "pdf".'},
                status=400,
            )

        # ---------------------------------------------------------
        # 2. Same-origin URL validation
        # ---------------------------------------------------------
        parsed_url = urlparse(dashboard_url)
        current_host = request.get_host()
        current_scheme = request.scheme
        current_hostname = current_host.split(":")[0]

        allowed_hosts = {
            current_host,
            current_hostname,
            "localhost",
            "127.0.0.1",
        }

        url_hostname = parsed_url.hostname
        if (
            not url_hostname
            or url_hostname not in allowed_hosts
            and not any(url_hostname.endswith("." + h) for h in allowed_hosts)
        ):
            logger.warning(
                "Unauthorized dashboard export attempt from %s: %s",
                request.user.username,
                dashboard_url,
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": "Unauthorized URL. Only same-origin URLs are allowed.",
                },
                status=403,
            )

        # Enforce same scheme
        if parsed_url.scheme != current_scheme:
            dashboard_url = f"{current_scheme}://{parsed_url.netloc}{parsed_url.path}"
            if parsed_url.query:
                dashboard_url += f"?{parsed_url.query}"

        # ---------------------------------------------------------
        # 3. Extract auth cookies
        # ---------------------------------------------------------
        sessionid = request.COOKIES.get("sessionid", "")
        csrftoken = request.COOKIES.get("csrftoken", "")

        if not sessionid:
            logger.warning(
                "No session cookie found for user %s",
                request.user.username,
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": "No active session found. Please log in again.",
                },
                status=401,
            )

        # ---------------------------------------------------------
        # 4. Create task and output file
        # ---------------------------------------------------------
        task_id = str(uuid.uuid4())
        file_extension = "pdf" if format_type == "pdf" else "png"
        filename = f"dashboard-{task_id}.{file_extension}"
        output_path = os.path.join(settings.MEDIA_ROOT, filename)

        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

        # ---------------------------------------------------------
        # 5. Set initial "pending" status in cache
        # ---------------------------------------------------------
        from django.core.cache import cache
        cache_key = f'{TASK_STATUS_PREFIX}{task_id}'
        cache.set(cache_key, 'pending', TASK_CACHE_TIMEOUT)

        # ---------------------------------------------------------
        # 6. Start Celery task
        # ---------------------------------------------------------
        try:
            export_dashboard_task.delay(
                task_id=task_id,
                dashboard_url=dashboard_url,
                output_path=output_path,
                format_type=format_type,
                sessionid=sessionid,
                csrftoken=csrftoken,
                active_tab=active_tab,
                route_path=route_path,
                filters_json=filters_json,
            )
        except Exception as celery_error:
            # Handle Celery/REDIS connection errors gracefully
            error_str = str(celery_error).lower()
            error_type = type(celery_error).__name__.lower()
            
            # Check if it's a connection error (Redis/Celery broker unavailable)
            is_connection_error = (
                'connection' in error_str or 
                'redis' in error_str or 
                'broker' in error_str or
                'kombu' in error_type or
                'operationalerror' in error_type or
                'temporary failure' in error_str or
                'name resolution' in error_str
            )
            
            if is_connection_error:
                logger.warning(
                    "Celery broker unavailable for export task: %s. Task queuing failed.",
                    str(celery_error)
                )
                # Update cache status to indicate failure
                try:
                    cache.set(cache_key, 'failed', TASK_CACHE_TIMEOUT)
                except Exception:
                    pass  # Cache might also be unavailable
                
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Export service is temporarily unavailable. Please try again later.",
                        "task_id": task_id,
                        "status": "failed",
                    },
                    status=503,  # Service Unavailable
                )
            else:
                # Re-raise non-connection errors
                raise

        logger.info(
            "Export task created for %s: task_id=%s, url=%s",
            request.user.username,
            task_id,
            dashboard_url,
        )

        return JsonResponse({
            "success": True,
            "task_id": task_id,
            "status": "pending",
        })

    except Exception as e:
        logger.exception("Unexpected error in export_dashboard: %s", str(e))
        return JsonResponse(
            {"success": False, "error": "Unexpected server error"},
            status=500,
        )


@login_required
@require_http_methods(["GET"])
def export_dashboard_status(request, task_id):
    """
    Get status of export task
    GET /api/export/dashboard/status/<task_id>/
    
    Returns: {
        "status": "pending" | "processing" | "completed" | "failed",
        "file_url": "url if completed",
        "error": "error message if failed"
    }
    """
    try:
        task_status = get_task_status(task_id)
        
        if task_status is None:
            return JsonResponse(
                {"success": False, "error": "Task not found"},
                status=404,
            )
        
        return JsonResponse({
            "success": True,
            **task_status,
        })
        
    except Exception as e:
        logger.exception("Unexpected error in export_dashboard_status: %s", str(e))
        return JsonResponse(
            {"success": False, "error": "Unexpected server error"},
            status=500,
        )


@login_required
@require_http_methods(["GET"])
def export_dashboard_download(request, task_id):
    """
    Download completed export file
    GET /api/export/dashboard/download/<task_id>/
    
    Returns: File download (PNG/PDF)
    """
    try:
        task_status = get_task_status(task_id)
        
        if task_status is None:
            return JsonResponse(
                {"success": False, "error": "Task not found"},
                status=404,
            )
        
        if task_status['status'] != 'completed':
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Task is not completed. Current status: {task_status['status']}",
                },
                status=400,
            )
        
        file_url = task_status.get('file_url')
        if not file_url:
            return JsonResponse(
                {"success": False, "error": "File URL not found"},
                status=404,
            )
        
        # Convert URL to file path
        # file_url is like "/media/dashboard-xxx.png"
        filename = os.path.basename(file_url)
        file_path = os.path.join(settings.MEDIA_ROOT, filename)
        
        if not os.path.exists(file_path):
            return JsonResponse(
                {"success": False, "error": "File not found"},
                status=404,
            )
        
        # Determine content type
        format_type = 'pdf' if filename.endswith('.pdf') else 'png'
        content_type = "application/pdf" if format_type == "pdf" else "image/png"
        
        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename=filename,
            content_type=content_type,
        )
        
    except Exception as e:
        logger.exception("Unexpected error in export_dashboard_download: %s", str(e))
        return JsonResponse(
            {"success": False, "error": "Unexpected server error"},
            status=500,
        )
