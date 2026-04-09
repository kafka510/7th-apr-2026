# Views package for main app
# This file imports all views to maintain backward compatibility with existing URLs

# Import all views from individual page modules
from .home_views import *
from .dashboard_views import *
from .portfolio_map_views import *
from .yield_report_views import *
from .pr_gap_views import *
from .revenue_loss_views import *
from .areas_of_concern_views import *
from .bess_performance_views import *
from .kpi_dashboard_views import *
from .sales_dashboard_views import *
from .generation_report_views import *
from .time_series_views import *
from .data_upload_views import *
from .user_management_views import *
from .site_onboarding_views import *
from .site_onboarding import *
from .feedback_views import *
from .security_views import *
from .minamata_views import *
from .ic_budget_views import *
from .download_views import *
from .api_data_views import *
from .siteonboarding_data_apload_views import *
from .analytics_views import *
from .shared.decorators import *
from accounts.decorators import *
from .api_views import *
from .pv_module_views import *

# Shared utilities are imported through individual modules as needed
from .react_demo_views import *
from .pv_hierarchy_views import *
# loss_calculation_views removed: api/loss-calculation/* handlers live in loss_analytics.views
from .calculation_test_views import *
from .static_file_views import serve_static_file, serve_media_file
from .spare_management_views import *
from .background_jobs_views import *