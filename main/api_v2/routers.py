"""
Router for main app API v2 endpoints.
"""

from rest_framework.routers import DefaultRouter
from .viewsets.kpi_viewsets import KPIViewSet
from .viewsets.yield_viewsets import YieldViewSet
from .viewsets.generation_viewsets import GenerationViewSet
from .viewsets.portfolio_map_viewsets import PortfolioMapViewSet
from .viewsets.sales_viewsets import SalesViewSet
from .viewsets.ic_budget_viewsets import ICBudgetViewSet
from .viewsets.data_upload_viewsets import DataUploadViewSet
from .viewsets.site_onboarding_viewsets import SiteOnboardingViewSet
from .viewsets.user_management_viewsets import UserManagementViewSet
from .viewsets.feedback_viewsets import FeedbackViewSet

router = DefaultRouter()

# Register viewsets
router.register(r'kpi', KPIViewSet, basename='kpi')
router.register(r'yield', YieldViewSet, basename='yield')
router.register(r'generation', GenerationViewSet, basename='generation')
router.register(r'portfolio-map', PortfolioMapViewSet, basename='portfolio-map')
router.register(r'sales', SalesViewSet, basename='sales')
router.register(r'ic-budget', ICBudgetViewSet, basename='ic-budget')
router.register(r'data-upload', DataUploadViewSet, basename='data-upload')
router.register(r'site-onboarding', SiteOnboardingViewSet, basename='site-onboarding')
router.register(r'user-management', UserManagementViewSet, basename='user-management')
router.register(r'feedback', FeedbackViewSet, basename='feedback')
# ... etc

urlpatterns = router.urls

