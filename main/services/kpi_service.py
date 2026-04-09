import math
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from django.utils import timezone

from main.models import AssetList, RealTimeKPI, YieldData
from main.views.shared.utilities import get_user_accessible_asset_numbers


@dataclass
class KPIRealtimeEntry:
    asset_code: str
    asset_number: str
    asset_name: str
    country: str
    portfolio: str
    date: str
    daily_kwh: float
    daily_irr: float
    daily_generation_mwh: float
    daily_irradiation_mwh: float
    daily_ic_mwh: float
    daily_expected_mwh: float
    daily_budget_irradiation_mwh: float
    expect_pr: float
    actual_pr: float
    dc_capacity_mw: float
    last_updated: Optional[str]
    is_frozen: bool
    capacity: float
    timezone: str
    site_state: Optional[str]


@dataclass
class KPIYieldEntry:
    month: str
    country: str
    portfolio: str
    assetno: str
    dc_capacity_mw: float
    ic_approved_budget: float
    expected_budget: float
    weather_loss_or_gain: float
    grid_curtailment: float
    grid_outage: float
    operation_budget: float
    breakdown_loss: float
    unclassified_loss: float
    actual_generation: float
    string_failure: float
    inverter_failure: float
    mv_failure: float
    hv_failure: float
    ac_failure: float
    budgeted_irradiation: float
    actual_irradiation: float
    ac_capacity_mw: float
    bess_capacity_mwh: float
    bess_generation_mwh: float
    expected_pr: float
    actual_pr: float
    pr_gap: float
    pr_gap_observation: str
    pr_gap_action_need_to_taken: str
    revenue_loss: float
    revenue_loss_observation: str
    revenue_loss_action_need_to_taken: str
    ppa_rate: float
    ic_approved_budget_dollar: float
    expected_budget_dollar: float
    actual_generation_dollar: float
    operational_budget_dollar: float
    revenue_loss_op: float
    created_at: Optional[str]
    updated_at: Optional[str]


class KPIService:
    """Encapsulates KPI data access used by both legacy views and new APIs."""

    def __init__(self, request):
        self.request = request
        self.accessible_asset_numbers = get_user_accessible_asset_numbers(request)
        self.asset_lookup_number: Dict[str, AssetList] = {}
        self.asset_lookup_code: Dict[str, AssetList] = {}

        if self.accessible_asset_numbers:
            assets = AssetList.objects.filter(asset_number__in=self.accessible_asset_numbers)
            for asset in assets:
                if asset.asset_number:
                    self.asset_lookup_number[str(asset.asset_number)] = asset
                if asset.asset_code:
                    self.asset_lookup_code[str(asset.asset_code)] = asset

        self.combined_asset_codes = set(self.asset_lookup_number.keys()) | set(self.asset_lookup_code.keys())

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _resolve_asset(self, asset_code: str) -> Optional[AssetList]:
        if not asset_code:
            return None
        asset = self.asset_lookup_number.get(asset_code)
        if asset:
            return asset
        return self.asset_lookup_code.get(asset_code)

    @staticmethod
    def _safe_float(value: Optional[float]) -> float:
        if value is None:
            return 0.0
        try:
            if isinstance(value, float) and math.isnan(value):
                return 0.0
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _safe_value(value):
        if value is None:
            return ""
        if isinstance(value, float) and math.isnan(value):
            return ""
        return value

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_realtime_queryset(self, filters: Optional[Dict] = None):
        if not self.combined_asset_codes:
            return RealTimeKPI.objects.none()

        queryset = RealTimeKPI.objects.filter(asset_code__in=self.combined_asset_codes)

        filters = filters or {}
        date_value = filters.get('date')
        if date_value:
            queryset = queryset.filter(date=date_value)

        asset_codes = [code for code in filters.get('asset_codes', []) if code]
        if asset_codes:
            queryset = queryset.filter(asset_code__in=asset_codes)

        countries = [country for country in filters.get('countries', []) if country]
        if countries:
            allowed_codes = {
                code
                for code, asset in self._iter_assets_with_codes()
                if asset.country in countries
            }
            queryset = queryset.filter(asset_code__in=allowed_codes)

        portfolios = [portfolio for portfolio in filters.get('portfolios', []) if portfolio]
        if portfolios:
            allowed_codes = {
                code
                for code, asset in self._iter_assets_with_codes()
                if asset.portfolio in portfolios
            }
            queryset = queryset.filter(asset_code__in=allowed_codes)

        return queryset.order_by('date', 'asset_code')

    def get_realtime_entries(self, filters: Optional[Dict] = None) -> List[Dict]:
        entries: List[Dict] = []
        queryset = self.get_realtime_queryset(filters)

        for record in queryset:
            asset = self._resolve_asset(str(record.asset_code))
            entries.append(asdict(KPIRealtimeEntry(
                asset_code=record.asset_code,
                asset_number=self._safe_value(asset.asset_number) if asset else '',
                asset_name=asset.asset_name if asset else record.asset_code,
                country=asset.country if asset else '',
                portfolio=asset.portfolio if asset else '',
                date=record.date.isoformat(),
                daily_kwh=self._safe_float(record.daily_kwh),
                daily_irr=self._safe_float(record.daily_irr),
                daily_generation_mwh=self._safe_float(record.daily_generation_mwh),
                daily_irradiation_mwh=self._safe_float(record.daily_irradiation_mwh),
                daily_ic_mwh=self._safe_float(record.daily_ic_mwh),
                daily_expected_mwh=self._safe_float(record.daily_expected_mwh),
                daily_budget_irradiation_mwh=self._safe_float(record.daily_budget_irradiation_mwh),
                expect_pr=0.0 if record.asset_code in {'TW1', 'TW2', 'TW3'} else self._safe_float(record.expect_pr),
                actual_pr=0.0 if record.asset_code in {'TW1', 'TW2', 'TW3'} else self._safe_float(record.actual_pr),
                dc_capacity_mw=self._safe_float(record.dc_capacity_mw),
                last_updated=record.last_updated.isoformat() if record.last_updated else None,
                is_frozen=record.is_frozen,
                capacity=self._safe_float(getattr(asset, 'capacity', 0)),
                timezone=getattr(asset, 'timezone', '+00:00'),
                site_state=getattr(record, 'site_state', None),
            )))

        return entries

    def get_yield_entries(self) -> List[Dict]:
        if not self.accessible_asset_numbers:
            return []

        entries: List[Dict] = []
        records = YieldData.objects.filter(assetno__in=self.accessible_asset_numbers)

        for record in records:
            p = KPIYieldEntry(
                month=self._safe_value(record.month),
                country=self._safe_value(record.country),
                portfolio=self._safe_value(record.portfolio),
                assetno=self._safe_value(record.assetno),
                dc_capacity_mw=self._safe_float(record.dc_capacity_mw),
                ic_approved_budget=self._safe_float(record.ic_approved_budget),
                expected_budget=self._safe_float(record.expected_budget),
                weather_loss_or_gain=self._safe_float(record.weather_loss_or_gain),
                grid_curtailment=self._safe_float(record.grid_curtailment),
                grid_outage=self._safe_float(record.grid_outage),
                operation_budget=self._safe_float(record.operation_budget),
                breakdown_loss=self._safe_float(record.breakdown_loss),
                unclassified_loss=self._safe_float(record.unclassified_loss),
                actual_generation=self._safe_float(record.actual_generation),
                string_failure=self._safe_float(getattr(record, 'string_failure', 0)),
                inverter_failure=self._safe_float(getattr(record, 'inverter_failure', 0)),
                mv_failure=self._safe_float(getattr(record, 'mv_failure', 0)),
                hv_failure=self._safe_float(getattr(record, 'hv_failure', 0)),
                ac_failure=self._safe_float(getattr(record, 'ac_failure', 0)),
                budgeted_irradiation=self._safe_float(record.budgeted_irradiation),
                actual_irradiation=self._safe_float(record.actual_irradiation),
                ac_capacity_mw=self._safe_float(record.ac_capacity_mw),
                bess_capacity_mwh=self._safe_float(record.bess_capacity_mwh),
                bess_generation_mwh=self._safe_float(record.bess_generation_mwh),
                expected_pr=0.0 if record.assetno in {'TW1', 'TW2', 'TW3'} else self._safe_float(record.expected_pr),
                actual_pr=0.0 if record.assetno in {'TW1', 'TW2', 'TW3'} else self._safe_float(record.actual_pr),
                pr_gap=self._safe_float(record.pr_gap),
                pr_gap_observation=self._safe_value(record.pr_gap_observation),
                pr_gap_action_need_to_taken=self._safe_value(record.pr_gap_action_need_to_taken),
                revenue_loss=self._safe_float(record.revenue_loss),
                revenue_loss_observation=self._safe_value(record.revenue_loss_observation),
                revenue_loss_action_need_to_taken=self._safe_value(record.revenue_loss_action_need_to_taken),
                ppa_rate=self._safe_float(getattr(record, 'ppa_rate', 0)),
                ic_approved_budget_dollar=self._safe_float(getattr(record, 'ic_approved_budget_dollar', 0)),
                expected_budget_dollar=self._safe_float(getattr(record, 'expected_budget_dollar', 0)),
                actual_generation_dollar=self._safe_float(getattr(record, 'actual_generation_dollar', 0)),
                operational_budget_dollar=self._safe_float(getattr(record, 'operational_budget_dollar', 0)),
                revenue_loss_op=self._safe_float(getattr(record, 'revenue_loss_op', 0)),
                created_at=record.created_at.isoformat() if getattr(record, 'created_at', None) else None,
                updated_at=record.updated_at.isoformat() if getattr(record, 'updated_at', None) else None,
            )
            entries.append(asdict(p))

        return entries

    def get_summary(self) -> Dict:
        if not self.combined_asset_codes:
            return {
                'total_assets': 0,
                'total_daily_kwh': 0,
                'avg_daily_irr': 0,
                'last_updated': None,
            }

        today = timezone.now().date()
        queryset = RealTimeKPI.objects.filter(asset_code__in=self.combined_asset_codes, date=today)

        total_assets = queryset.count()
        total_daily_kwh = sum(self._safe_float(record.daily_kwh) for record in queryset)
        avg_daily_irr = 0.0
        if total_assets:
            avg_daily_irr = sum(self._safe_float(record.daily_irr) for record in queryset) / total_assets

        latest_record = queryset.order_by('-last_updated').first()
        last_updated = latest_record.last_updated.isoformat() if latest_record and latest_record.last_updated else None

        return {
            'total_assets': total_assets,
            'total_daily_kwh': round(total_daily_kwh, 2),
            'avg_daily_irr': round(avg_daily_irr, 3),
            'last_updated': last_updated,
        }

    def get_dashboard_payload(self) -> Dict[str, List[Dict]]:
        return {
            'realtime': self.get_realtime_entries(),
            'yield': self.get_yield_entries(),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _iter_assets_with_codes(self):
        for number, asset in self.asset_lookup_number.items():
            yield number, asset
        for code, asset in self.asset_lookup_code.items():
            yield code, asset
