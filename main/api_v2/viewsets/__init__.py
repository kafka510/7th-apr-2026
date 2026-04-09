"""
ViewSets for main app API v2.
"""

from .kpi_viewsets import KPIViewSet
from .yield_viewsets import YieldViewSet
from .generation_viewsets import GenerationViewSet
from .portfolio_map_viewsets import PortfolioMapViewSet
from .sales_viewsets import SalesViewSet
from .ic_budget_viewsets import ICBudgetViewSet
from .data_upload_viewsets import DataUploadViewSet
from .site_onboarding_viewsets import SiteOnboardingViewSet
from .user_management_viewsets import UserManagementViewSet
from .feedback_viewsets import FeedbackViewSet

__all__ = [
    'KPIViewSet',
    'YieldViewSet',
    'GenerationViewSet',
    'PortfolioMapViewSet',
    'SalesViewSet',
    'ICBudgetViewSet',
    'DataUploadViewSet',
    'SiteOnboardingViewSet',
    'UserManagementViewSet',
    'FeedbackViewSet',
]

