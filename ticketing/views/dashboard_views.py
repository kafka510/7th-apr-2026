from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.db.models import Count, Q, Sum, F
from django.utils import timezone
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.template.loader import render_to_string
from datetime import timedelta
import json
import csv

from waffle import flag_is_active
from waffle.decorators import waffle_flag

from ..models import Ticket, TicketCategory, LossCategory
from ..services import TicketDashboardService
from ..utils import get_accessible_sites_for_user

try:
    from openpyxl import Workbook
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


@method_decorator(login_required, name='dispatch')
class TicketDashboardView(TemplateView):
    """Dashboard view for ticket statistics and analytics"""
    template_name = 'ticketing/ticket_dashboard.html'
    
    def get_template_names(self):
        if flag_is_active(self.request, 'react_ticket_dashboard'):
            return ['ticketing/ticket_dashboard_react.html']
        return [self.template_name]
    
    def _get_service(self) -> TicketDashboardService:
        if not hasattr(self, '_dashboard_service'):
            self._dashboard_service = TicketDashboardService(self.request.user)
        return self._dashboard_service

    def dispatch(self, request, *args, **kwargs):
        """Check ticketing access before processing request"""
        from ..utils import has_ticketing_access
        from django.http import HttpResponseForbidden
        from django.template.loader import render_to_string
        
        if not has_ticketing_access(request.user):
            return HttpResponseForbidden(
                render_to_string('ticketing/access_denied.html', {
                    'message': 'You do not have access to the ticketing system. Please contact an administrator.'
                })
            )
        return super().dispatch(request, *args, **kwargs)

    def get_filtered_tickets(self, filters=None):
        """Get filtered tickets based on filter parameters"""
        service = self._get_service()
        return service.get_queryset(filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = self._get_service()
        context.update(service.build_template_context())
        return context
    
    def calculate_avg_time_to_close(self, tickets):
        """Calculate average time to close tickets"""
        service = self._get_service()
        result = service.calculate_avg_time_to_close(tickets)
        return result.to_dict() if result else None

    def get_dashboard_data(self, tickets):
        """Get all dashboard data for a given ticket queryset"""
        service = self._get_service()
        return service.serialize_dashboard_payload(tickets)


@login_required
@waffle_flag('react_ticket_dashboard')
def ticket_dashboard_react_view(request):
    """
    Dedicated endpoint for the React ticket dashboard while the rollout is under a feature flag.
    """
    return render(request, 'ticketing/ticket_dashboard_react.html')


@method_decorator(login_required, name='dispatch')
class DashboardAPIView(TemplateView):
    """AJAX endpoint for filtered dashboard data"""
    
    def dispatch(self, request, *args, **kwargs):
        """Check ticketing access before processing request"""
        from ..utils import has_ticketing_access
        from django.http import HttpResponseForbidden
        
        if not has_ticketing_access(request.user):
            return JsonResponse({'error': 'Access denied'}, status=403)
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        """Handle AJAX POST request with filters"""
        try:
            # Parse JSON body
            filters = json.loads(request.body)
            service = TicketDashboardService(request.user)
            tickets = service.get_queryset(filters)
            data = service.serialize_dashboard_payload(tickets)
            
            return JsonResponse(data)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@login_required
def analytics_widget(request):
    """
    AJAX endpoint returning:
      - html: table partial
      - labels: chart labels
      - values: chart values
      - total_count: total rows before pagination
    
    Accepts params:
      view_by: device_tickets | device_loss | category_tickets | category_loss | make_tickets | model_tickets
      top_n: number of items requested per page (per_page)
      page: page number (1-indexed)
      trend_days: 7 or 30 (defaults 7)
    """
    import traceback
    
    try:
        from ..utils import has_ticketing_access

        if not has_ticketing_access(request.user):
            return JsonResponse({'error': 'Access denied'}, status=403)

        view_by = request.GET.get("view_by", "device_tickets")
        per_page = int(request.GET.get("top_n", 10))
        page = int(request.GET.get("page", 1))
        trend_days = int(request.GET.get("trend_days", 7))

        service = TicketDashboardService(request.user)
        if not service.get_accessible_sites().exists():
            return JsonResponse({
                "html": '<div class="p-3 text-muted">No accessible sites found.</div>',
                "labels": [],
                "values": [],
                "total_items": 0,
                "page": page,
                "per_page": per_page
            })

        filters = {
            "status": request.GET.get("status"),
            "priority": request.GET.get("priority"),
            "category": request.GET.get("category"),
            "site": request.GET.get("site"),
            "date_from": request.GET.get("date_from"),
            "date_to": request.GET.get("date_to"),
        }

        dataset = service.get_analytics_dataset(
            raw_filters=filters,
            view_by=view_by,
            page=page,
            per_page=per_page,
            trend_days=trend_days,
        )

        rows = [
            {
                "label": item["label"],
                "sub": item.get("subLabel") or "",
                "val1": item["value"],
                "val2": item["secondary"],
                "trend": item["trend"],
                "entity_type": item["entityType"],
                "entity_key": item["entityKey"],
            }
            for item in dataset["items"]
        ]

        table_html = render_to_string(
            "ticketing/partials/analytics_widget_table.html",
            {"rows": rows, "view_by": view_by},
        )

        return JsonResponse({
            "html": table_html,
            "labels": dataset["labels"],
            "values": dataset["values"],
            "total_items": dataset["pagination"]["totalItems"],
            "page": dataset["pagination"]["page"],
            "per_page": dataset["pagination"]["perPage"],
        })

    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Analytics widget error: {str(e)}\n{error_trace}")

        return JsonResponse({
            'error': str(e),
            'traceback': error_trace
        }, status=500)


@login_required
def ajax_filter_dashboard(request):
    """
    Returns recent tickets partial filtered by provided params.
    Accepts GET: status, priority, category, OR generic 'filter_by' & 'filter_value'
    """
    from ..utils import has_ticketing_access

    if not has_ticketing_access(request.user):
        return JsonResponse({'error': 'Access denied'}, status=403)

    service = TicketDashboardService(request.user)
    filters = {
        "status": request.GET.get("status"),
        "priority": request.GET.get("priority"),
        "category": request.GET.get("category"),
        "site": request.GET.get("site"),
        "date_from": request.GET.get("date_from"),
        "date_to": request.GET.get("date_to"),
    }
    filter_by = request.GET.get("filter_by")
    filter_value = request.GET.get("filter_value")

    tickets = service.get_recent_ticket_queryset_with_filters(
        raw_filters=filters,
        filter_by=filter_by,
        filter_value=filter_value,
        limit=50,
    )

    html = render_to_string("ticketing/partials/recent_tickets_table.html", {
        "recent_tickets": tickets
    })
    
    return JsonResponse({"html": html})


@login_required
def export_widget_csv(request):
    """Export current widget view as CSV"""
    from ..utils import has_ticketing_access
    
    # Check ticketing access
    if not has_ticketing_access(request.user):
        return HttpResponseBadRequest("Access denied")
    
    # Get data from analytics_widget
    resp = analytics_widget(request)
    
    if not isinstance(resp, JsonResponse):
        return HttpResponseBadRequest("Export failed")
    
    # Access data from JsonResponse - it's stored in resp.content as JSON string
    import json
    data = json.loads(resp.content.decode('utf-8'))
    
    # Check if there's an error in the response
    if 'error' in data:
        return HttpResponseBadRequest(f"Export failed: {data.get('error', 'Unknown error')}")
    
    labels = data.get('labels', [])
    values = data.get('values', [])
    
    # Prepare CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="analytics_widget.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Name', 'Value', 'Trend (comma separated)'])
    
    # Export labels & values (trends can be added if needed)
    for i, label in enumerate(labels):
        val = values[i] if i < len(values) else ''
        writer.writerow([label, val, ""])
    
    return response


@login_required
def export_widget_excel(request):
    """Export current widget view as Excel"""
    from ..utils import has_ticketing_access
    import json
    
    # Check ticketing access
    if not has_ticketing_access(request.user):
        return HttpResponseBadRequest("Access denied")
    
    if not HAS_OPENPYXL:
        return HttpResponseBadRequest("Excel export requires openpyxl. Install with: pip install openpyxl")
    
    # Get data from analytics_widget
    resp = analytics_widget(request)
    
    if not isinstance(resp, JsonResponse):
        return HttpResponseBadRequest("Export failed")
    
    # Access data from JsonResponse - it's stored in resp.content as JSON string
    data = json.loads(resp.content.decode('utf-8'))
    
    # Check if there's an error in the response
    if 'error' in data:
        return HttpResponseBadRequest(f"Export failed: {data.get('error', 'Unknown error')}")
    
    labels = data.get('labels', [])
    values = data.get('values', [])
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Analytics"
    
    ws.append(['Name', 'Value'])
    
    for i, label in enumerate(labels):
        ws.append([label, values[i] if i < len(values) else ''])
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="analytics_widget.xlsx"'
    
    wb.save(response)
    return response

