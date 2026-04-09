"""
ViewSet for IC Budget vs Expected endpoints (React app).
Reuses existing logic from main.api.ic_budget
"""

import math
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from shared_app.permissions.base_permissions import HasFeaturePermission
from ..serializers.ic_budget_serializers import ICBudgetDataResponseSerializer


class HasICBudgetAccess(HasFeaturePermission):
    """Permission class for IC Budget vs Expected access"""
    required_feature = 'ic_budget_vs_expected'


class ICBudgetViewSet(viewsets.ViewSet):
    """
    ViewSet for IC Budget vs Expected endpoints (React app)
    GET /api/v2/main/ic-budget/ic-budget-data/
    """
    permission_classes = [IsAuthenticated, HasICBudgetAccess]

    def safe_val(self, val):
        """Convert None or NaN to None"""
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return None
        return val

    @action(detail=False, methods=['get'], url_path='ic-budget-data')
    def ic_budget_data(self, request):
        """
        Get IC Budget vs Expected data for React app
        GET /api/v2/main/ic-budget/ic-budget-data/
        """
        try:
            # Lazy import to avoid circular dependency
            from main.models import ICVSEXVSCURData, AssetList
            from main.views.shared.utilities import get_user_accessible_sites

            # Get user accessible sites
            accessible_sites = get_user_accessible_sites(request)

            if accessible_sites:
                # Filter by accessible sites - ICVSEXVSCURData uses portfolio
                accessible_portfolios = []
                for site in accessible_sites:
                    try:
                        asset = AssetList.objects.get(asset_number=site)
                        accessible_portfolios.append(asset.portfolio)
                    except AssetList.DoesNotExist:
                        continue

                if accessible_portfolios:
                    icvsexvscur_data = ICVSEXVSCURData.objects.filter(portfolio__in=accessible_portfolios)
                else:
                    icvsexvscur_data = ICVSEXVSCURData.objects.all()
            else:
                icvsexvscur_data = ICVSEXVSCURData.objects.all()

            icvsexvscur_data_list = []
            for record in icvsexvscur_data:
                icvsexvscur_data_list.append({
                    'id': record.id,
                    'country': self.safe_val(record.country),
                    'portfolio': self.safe_val(record.portfolio),
                    'dc_capacity_mwp': self.safe_val(record.dc_capacity_mwp),
                    'month': record.month.strftime('%b %Y') if record.month else None,
                    'month_sort': record.month.isoformat() if record.month else None,
                    'ic_approved_budget_mwh': self.safe_val(record.ic_approved_budget_mwh),
                    'expected_budget_mwh': self.safe_val(record.expected_budget_mwh),
                    'actual_generation_mwh': self.safe_val(record.actual_generation_mwh),
                    'grid_curtailment_budget_mwh': self.safe_val(record.grid_curtailment_budget_mwh),
                    'actual_curtailment_mwh': self.safe_val(record.actual_curtailment_mwh),
                    'budget_irradiation_kwh_m2': self.safe_val(record.budget_irradiation_kwh_m2),
                    'actual_irradiation_kwh_m2': self.safe_val(record.actual_irradiation_kwh_m2),
                    'expected_pr_percent': self.safe_val(record.expected_pr_percent),
                    'actual_pr_percent': self.safe_val(record.actual_pr_percent),
                    'created_at': record.created_at.isoformat() if record.created_at else None,
                    'updated_at': record.updated_at.isoformat() if record.updated_at else None,
                })

            response_data = {
                'success': True,
                'data': icvsexvscur_data_list,
                'count': len(icvsexvscur_data_list)
            }

            serializer = ICBudgetDataResponseSerializer(response_data)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'data': [],
                    'count': 0
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

