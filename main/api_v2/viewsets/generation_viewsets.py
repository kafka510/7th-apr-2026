"""
ViewSet for Generation Report endpoints (React app).
Reuses existing logic from main.api.generation_report
"""

import math
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from shared_app.permissions.base_permissions import HasFeaturePermission
from ..serializers.generation_serializers import GenerationReportDataSerializer


class HasGenerationAccess(HasFeaturePermission):
    """Permission class for Generation Report access"""
    required_feature = 'generation_report'


class GenerationViewSet(viewsets.ViewSet):
    """
    ViewSet for Generation Report endpoints (React app)
    GET /api/v2/main/generation/data/
    """
    permission_classes = [IsAuthenticated, HasGenerationAccess]

    def safe_val(self, val, is_numeric=False):
        """Convert None or NaN to None for numeric fields, empty string for text fields"""
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return None if is_numeric else ""
        # If it's a string that's empty or just whitespace, convert to None for numeric fields
        if is_numeric and isinstance(val, str) and (not val.strip() or val.strip() == ''):
            return None
        return val

    @action(detail=False, methods=['get'], url_path='data')
    def data(self, request):
        """
        Get generation report data for React app
        GET /api/v2/main/generation/data/
        
        Query Parameters:
        - start_month: Optional start month filter (YYYY-MM)
        - end_month: Optional end month filter (YYYY-MM)
        """
        try:
            # Lazy import to avoid circular dependency
            from main.api.generation_report import generation_report_data_view
            
            # Call the existing function-based view logic
            # We'll extract the logic and adapt it for DRF
            from main.views.shared.utilities import get_user_accessible_sites
            from main.models import (
                YieldData, MapData, ActualGenerationDailyData, ExpectedBudgetDailyData,
                BudgetGIIDailyData, ActualGIIDailyData, ICApprovedBudgetDailyData
            )
            
            # Get user accessible sites
            accessible_sites = get_user_accessible_sites(request)
            
            if not accessible_sites.exists():
                return Response(
                    {'error': 'No accessible sites found for your account.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get asset_number values from accessible_sites
            accessible_asset_numbers = accessible_sites.values_list('asset_number', flat=True)
            
            # 1. YieldData for revenue table
            yield_data_records = YieldData.objects.filter(
                assetno__in=accessible_asset_numbers
            )
            
            yield_data_list = []
            for record in yield_data_records:
                yield_data_list.append({
                    'assetno': self.safe_val(record.assetno),
                    'dc_capacity_mw': self.safe_val(record.dc_capacity_mw, is_numeric=True),
                    'month': self.safe_val(record.month),
                    'country': self.safe_val(record.country),
                    'portfolio': self.safe_val(record.portfolio),
                    'ic_approved_budget_dollar': self.safe_val(record.ic_approved_budget_dollar, is_numeric=True),
                    'expected_budget_dollar': self.safe_val(record.expected_budget_dollar, is_numeric=True),
                    'actual_generation_dollar': self.safe_val(record.actual_generation_dollar, is_numeric=True),
                    'operational_budget_dollar': self.safe_val(record.operational_budget_dollar, is_numeric=True),
                    'revenue_loss_op': self.safe_val(record.revenue_loss_op, is_numeric=True),
                    'ppa_rate': self.safe_val(record.ppa_rate, is_numeric=True),
                })
            
            # 2. IC Approved Budget Daily data (wide format)
            ic_approved_budget_daily_data = ICApprovedBudgetDailyData.objects.filter(
                asset_code__in=accessible_asset_numbers
            )
            
            ic_approved_budget_daily_wide = {}
            for record in ic_approved_budget_daily_data:
                date_key = record.date.isoformat() if record.date else "unknown"
                if date_key not in ic_approved_budget_daily_wide:
                    ic_approved_budget_daily_wide[date_key] = {'Date': date_key}
                asset_key = record.asset_code if record.asset_code else "unknown"
                ic_approved_budget_daily_wide[date_key][asset_key] = self.safe_val(record.ic_approved_budget_kwh, is_numeric=True)
            
            ic_approved_budget_daily_list = list(ic_approved_budget_daily_wide.values())
            
            # 3. Actual Generation Daily data
            actual_gen_data = ActualGenerationDailyData.objects.filter(
                asset_code__in=accessible_asset_numbers
            )
            
            actual_gen_wide = {}
            for record in actual_gen_data:
                date_key = record.date.isoformat() if record.date else "unknown"
                if date_key not in actual_gen_wide:
                    actual_gen_wide[date_key] = {'Date': date_key}
                asset_key = record.asset_code if record.asset_code else "unknown"
                actual_gen_wide[date_key][asset_key] = self.safe_val(record.generation_kwh, is_numeric=True)
            
            actual_gen_list = list(actual_gen_wide.values())
            
            # 4. Expected Budget Daily data
            expected_budget_data = ExpectedBudgetDailyData.objects.filter(
                asset_code__in=accessible_asset_numbers
            )
            
            expected_budget_wide = {}
            for record in expected_budget_data:
                date_key = record.date.isoformat() if record.date else "unknown"
                if date_key not in expected_budget_wide:
                    expected_budget_wide[date_key] = {'Date': date_key}
                asset_key = record.asset_code if record.asset_code else "unknown"
                expected_budget_wide[date_key][asset_key] = self.safe_val(record.expected_budget_kwh, is_numeric=True)
            
            expected_budget_list = list(expected_budget_wide.values())
            
            # 5. Budget GII Daily data
            budget_gii_data = BudgetGIIDailyData.objects.filter(
                asset_code__in=accessible_asset_numbers
            )
            
            budget_gii_wide = {}
            for record in budget_gii_data:
                date_key = record.date.isoformat() if record.date else "unknown"
                if date_key not in budget_gii_wide:
                    budget_gii_wide[date_key] = {'Date': date_key}
                asset_key = record.asset_code if record.asset_code else "unknown"
                budget_gii_wide[date_key][asset_key] = self.safe_val(record.budget_gii_kwh, is_numeric=True)
            
            budget_gii_list = list(budget_gii_wide.values())
            
            # 6. Actual GII Daily data
            actual_gii_data = ActualGIIDailyData.objects.filter(
                asset_code__in=accessible_asset_numbers
            )
            
            actual_gii_wide = {}
            for record in actual_gii_data:
                date_key = record.date.isoformat() if record.date else "unknown"
                if date_key not in actual_gii_wide:
                    actual_gii_wide[date_key] = {'Date': date_key}
                asset_key = record.asset_code if record.asset_code else "unknown"
                actual_gii_wide[date_key][asset_key] = self.safe_val(record.actual_gii_kwh, is_numeric=True)
            
            actual_gii_list = list(actual_gii_wide.values())
            
            # 7. Map data for DC capacity
            map_data = MapData.objects.filter(
                asset_no__in=accessible_asset_numbers
            )
            
            map_data_list = []
            for record in map_data:
                map_data_list.append({
                    'asset_no': self.safe_val(record.asset_no),
                    'dc_capacity_mwp': self.safe_val(record.dc_capacity_mwp, is_numeric=True),
                    'country': self.safe_val(record.country),
                    'portfolio': self.safe_val(record.portfolio),
                })
            
            # Calculate latest report date (80% threshold)
            latest_report_date = self._get_latest_report_date(actual_gen_list)
            
            # Get date range
            date_range = self._get_date_range(actual_gen_list)
            
            response_data = {
                'icApprovedBudgetDaily': ic_approved_budget_daily_list,
                'expectedBudgetDaily': expected_budget_list,
                'actualGenerationDaily': actual_gen_list,
                'budgetGIIDaily': budget_gii_list,
                'actualGIIDaily': actual_gii_list,
                'yieldData': yield_data_list,
                'mapData': map_data_list,
                'latestReportDate': latest_report_date,
                'dateRange': date_range,
            }
            
            # Serialize response
            serializer = GenerationReportDataSerializer(response_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_latest_report_date(self, actual_gen_list):
        """Get latest date where 80% of assets have data"""
        if not actual_gen_list:
            return ""
        
        # Get all asset columns (excluding Date)
        if not actual_gen_list[0]:
            return ""
        
        asset_cols = [k for k in actual_gen_list[0].keys() if k not in ['Date', 'date']]
        total_assets = len(asset_cols)
        if total_assets == 0:
            return ""
        
        threshold = math.ceil(total_assets * 0.8)
        
        # Sort by date descending
        sorted_rows = sorted(
            actual_gen_list,
            key=lambda r: r.get('Date') or r.get('date') or '',
            reverse=True
        )
        
        for row in sorted_rows:
            date_str = row.get('Date') or row.get('date')
            if not date_str:
                continue
            
            # Count assets with data
            filled_assets = 0
            for col in asset_cols:
                val = row.get(col)
                if val is not None and val != '':
                    try:
                        num_val = float(val)
                        if num_val > 0:
                            filled_assets += 1
                    except (ValueError, TypeError):
                        pass
            
            if filled_assets >= threshold:
                return date_str
        
        # Fallback: return most recent date
        if sorted_rows:
            return sorted_rows[0].get('Date') or sorted_rows[0].get('date') or ""
        
        return ""
    
    def _get_date_range(self, actual_gen_list):
        """Get min/max date range from actual generation data"""
        if not actual_gen_list:
            return {'min': '2025-01-01', 'max': '2025-12-31'}
        
        dates = [r.get('Date') or r.get('date') for r in actual_gen_list if r.get('Date') or r.get('date')]
        if not dates:
            return {'min': '2025-01-01', 'max': '2025-12-31'}
        
        dates.sort()
        min_date = dates[0]
        max_date = dates[-1]
        
        # Always return full year range
        if min_date:
            year = int(min_date.split('-')[0])
            return {
                'min': f'{year}-01-01',
                'max': f'{year}-12-31'
            }
        
        return {'min': '2025-01-01', 'max': '2025-12-31'}

