from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from main.permissions import user_has_feature
from main.services.kpi_service import KPIService


class HasKPIFeaturePermission(BasePermission):
    message = 'You do not have access to the KPI dashboard.'

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and user_has_feature(request.user, 'kpi_dashboard')


class KPIMetricsView(APIView):
    permission_classes = [IsAuthenticated, HasKPIFeaturePermission]

    def get(self, request):
        filters = {
            'date': request.query_params.get('date'),
            'asset_codes': [code for code in request.query_params.get('asset_codes', '').split(',') if code],
            'countries': [country for country in request.query_params.get('countries', '').split(',') if country],
            'portfolios': [portfolio for portfolio in request.query_params.get('portfolios', '').split(',') if portfolio],
        }
        service = KPIService(request)
        entries = service.get_realtime_entries(filters)
        return Response({
            'count': len(entries),
            'results': entries,
        })


class KPISummaryView(APIView):
    permission_classes = [IsAuthenticated, HasKPIFeaturePermission]

    def get(self, request):
        service = KPIService(request)
        summary = service.get_summary()
        return Response(summary)
