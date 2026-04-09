"""
Main dashboard views
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from accounts.decorators import feature_required
from django.utils import timezone
from waffle import flag_is_active
from main.permissions import user_has_feature, user_has_capability, user_has_app_access
from django.urls import reverse
from main.security.url_encryption import encrypt_url


@login_required
def dashboard_view(request):
    """Basic dashboard view"""
    return render(request, 'main/UNIFIED_OPERATIONS_DASHBOARD.html')


@login_required
@ensure_csrf_cookie
def unified_operations_dashboard_view(request):
    """
    Unified operations dashboard - main dashboard view.
    Accessible to all authenticated users. Sidebar will show only pages
    the user has permission to access.
    """
    # Check if React version should be used
    use_react = flag_is_active(request, 'react_unified_dashboard')
    
    if use_react:
        return render(request, 'main/unified_operations_dashboard_react.html', {
            'timestamp': int(timezone.now().timestamp()),
            'is_superuser': request.user.is_superuser,
        })
    
    return render(request, 'main/UNIFIED_OPERATIONS_DASHBOARD.html', {
        'timestamp': int(timezone.now().timestamp())
    })


@login_required
@require_http_methods(["GET"])
def api_unified_dashboard_data(request):
    """
    API endpoint to provide dashboard menu structure and user info for React frontend.
    """
    from main.models import UserProfile
    
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        role = user_profile.role
    except UserProfile.DoesNotExist:
        role = 'others'
    
    # Helper function to check permission
    def has_permission(feature):
        return user_has_feature(request.user, feature)
    
    def has_cap(capability):
        return user_has_capability(request.user, capability)
    
    def has_app(app_key):
        return user_has_app_access(request.user, app_key)
    
    # Helper to get encrypted URL
    def get_url(url_name, app_name='main'):
        try:
            if app_name == 'ticketing':
                original_url = reverse(f'ticketing:{url_name}')
            elif app_name == 'api':
                original_url = reverse(f'api:{url_name}')
            elif app_name == 'energy_revenue_hub':
                original_url = reverse(f'energy_revenue_hub:{url_name}')
            elif app_name == 'engineering_tools':
                original_url = reverse(f'engineering_tools:{url_name}')
            else:
                original_url = reverse(f'main:{url_name}')
            encrypted_token = encrypt_url(original_url)
            return f"/{encrypted_token}"
        except Exception as e:
            # Fallback to regular URL if encryption fails
            try:
                if app_name == 'ticketing':
                    return reverse(f'ticketing:{url_name}')
                elif app_name == 'api':
                    return reverse(f'api:{url_name}')
                elif app_name == 'energy_revenue_hub':
                    return reverse(f'energy_revenue_hub:{url_name}')
                elif app_name == 'engineering_tools':
                    return reverse(f'engineering_tools:{url_name}')
                else:
                    return reverse(f'main:{url_name}')
            except:
                return '#'
    
    sections = []
    
    # Portfolio Section
    portfolio_items = []
    if has_permission('portfolio_map'):
        portfolio_items.append({
            'id': 'dash-portfolio-map',
            'label': 'Portfolio Map',
            'icon': '🗺️',
            'tabId': 'dash-portfolio-map',
            'url': get_url('portfolio_map'),
        })
    if has_permission('kpi_dashboard'):
        portfolio_items.append({
            'id': 'dash-kpi-dashboard',
            'label': 'KPI Dashboard',
            'icon': '📊',
            'tabId': 'dash-kpi-dashboard',
            'url': get_url('kpi_dashboard'),
        })
    if has_permission('sales'):
        portfolio_items.append({
            'id': 'dash-sales',
            'label': 'Sales',
            'icon': '💰',
            'tabId': 'dash-sales',
            'url': get_url('sales'),
        })
    
    if portfolio_items:
        if len(portfolio_items) > 1:
            sections.append({
                'type': 'group',
                'group': {
                    'id': 'portfolio',
                    'label': 'Portfolio',
                    'icon': '📁',
                    'items': portfolio_items,
                },
            })
        else:
            sections.append({
                'type': 'single',
                'items': portfolio_items,
            })
    
    # Performance Section
    pv_perf_items = []
    if has_permission('yield_report'):
        pv_perf_items.append({
            'id': 'dash-yield-report',
            'label': 'Yield Report',
            'icon': '📊',
            'tabId': 'dash-yield-report',
            'url': get_url('yield_report'),
        })
    if has_permission('pr_gap'):
        pv_perf_items.append({
            'id': 'dash-pr-gap',
            'label': 'PR Gap (%)',
            'icon': '📈',
            'tabId': 'dash-pr-gap',
            'url': get_url('pr_gap'),
        })
    if has_permission('revenue_loss'):
        pv_perf_items.append({
            'id': 'dash-revenue-loss',
            'label': 'Revenue',
            'icon': '💸',
            'tabId': 'dash-revenue-loss',
            'url': get_url('revenue_loss'),
        })
    if has_permission('areas_of_concern'):
        pv_perf_items.append({
            'id': 'dash-areas-of-concern',
            'label': 'Areas of Concern',
            'icon': '⚠️',
            'tabId': 'dash-areas-of-concern',
            'url': get_url('areas_of_concern'),
        })
    
    if pv_perf_items:
        if len(pv_perf_items) > 1:
            sections.append({
                'type': 'group',
                'group': {
                    'id': 'pv-performance',
                    'label': 'PV Performance',
                    'icon': '☀️',
                    'items': pv_perf_items,
                },
            })
        else:
            sections.append({
                'type': 'single',
                'items': pv_perf_items,
            })
    
    # BESS Performance
    if has_permission('bess_performance'):
        sections.append({
            'type': 'single',
            'items': [{
                'id': 'dash-bess-performance',
                'label': 'BESS Performance',
                'icon': '⚡',
                'tabId': 'dash-bess-performance',
                'url': get_url('bess_performance'),
            }],
        })
    
    if has_permission('bess_v1_performance'):
        sections.append({
            'type': 'single',
            'items': [{
                'id': 'dash-bess-v1-performance',
                'label': 'BESS Dashboard',
                'icon': '🔋',
                'tabId': 'dash-bess-v1-performance',
                'url': get_url('bess_v1_performance'),
            }],
        })
    
    # Generic Section
    generic_items = []
    if has_permission('minamata_typhoon_damage'):
        generic_items.append({
            'id': 'dash-minamata-typhoon-damage',
            'label': 'Minamata Typhoon Damage',
            'icon': '🌪️',
            'tabId': 'dash-minamata-typhoon-damage',
            'url': get_url('minamata_typhoon_damage'),
        })
    if has_permission('ic_budget_vs_expected'):
        generic_items.append({
            'id': 'dash-ic-budget-vs-expected',
            'label': 'IC Budget Vs Expected',
            'icon': '📊',
            'tabId': 'dash-ic-budget-vs-expected',
            'url': get_url('ic_budget_vs_expected'),
        })
    
    if generic_items:
        if len(generic_items) > 1:
            sections.append({
                'type': 'group',
                'group': {
                    'id': 'generic',
                    'label': 'Generic',
                    'icon': '📋',
                    'items': generic_items,
                },
            })
        else:
            sections.append({
                'type': 'single',
                'items': generic_items,
            })
    
    # Generation Report
    if has_permission('generation_report'):
        sections.append({
            'type': 'single',
            'items': [{
                'id': 'dash-generation-report',
                'label': 'Generation Report',
                'icon': '📊',
                'tabId': 'dash-generation-report',
                'url': get_url('generation_report'),
            }],
        })
    
    # Energy Monitoring
    if has_permission('time_series_dashboard'):
        sections.append({
            'type': 'single',
            'items': [{
                'id': 'dash-time-series-dashboard',
                'label': 'Energy Monitoring',
                'icon': '📈',
                'tabId': 'dash-time-series-dashboard',
                'url': get_url('time_series_dashboard'),
            }],
        })
    
    # Analytics
    if has_permission('analytics'):
        sections.append({
            'type': 'single',
            'items': [{
                'id': 'dash-analytics',
                'label': 'Analytics Dashboard',
                'icon': '📊',
                'tabId': 'dash-analytics',
                'url': get_url('analytics'),
            }],
        })
    
    # Loss Calculation Test (Admin only)
    # Use the same user_profile already fetched at the top of the function
    is_admin = request.user.is_superuser or role == 'admin'
    
    if is_admin:
        sections.append({
            'type': 'divider',
        })
        sections.append({
            'type': 'single',
            'items': [{
                'id': 'dash-calculation-test',
                'label': 'Loss Calculation Test',
                'icon': '🧪',
                'tabId': 'dash-calculation-test',
                'url': get_url('calculation_test'),
            }],
        })
        # React-based Loss Analytics section (Loss Events)
        sections.append({
            'type': 'group',
            'group': {
                'id': 'loss-analytics',
                'label': 'Loss Analytics',
                'icon': '📉',
                'items': [{
                    'id': 'dash-loss-events',
                    'label': 'Loss Events',
                    'icon': '📋',
                    'tabId': 'dash-loss-events',
                    # No URL => handled fully in React (no iframe)
                }],
            },
        })
    
    # Ticketing System
    if has_cap('ticketing.manage_settings') or has_app('ticketing'):
        ticketing_items = []
        if has_cap('ticketing.manage_settings') or request.user.is_superuser:
            ticketing_items.append({
                'id': 'dash-ticket-list',
                'label': 'All Tickets',
                'icon': '📋',
                'tabId': 'dash-ticket-list',
                'url': get_url('ticket_list', 'ticketing'),
            })
        else:
            ticketing_items.append({
                'id': 'dash-my-tickets',
                'label': 'My Tickets',
                'icon': '📋',
                'tabId': 'dash-my-tickets',
                'url': get_url('my_tickets', 'ticketing'),
            })
        ticketing_items.append({
            'id': 'dash-ticket-create',
            'label': 'Create Ticket',
            'icon': '➕',
            'tabId': 'dash-ticket-create',
            'url': get_url('ticket_create', 'ticketing'),
        })
        ticketing_items.append({
            'id': 'dash-ticket-dashboard',
            'label': 'Dashboard',
            'icon': '📊',
            'tabId': 'dash-ticket-dashboard',
            'url': get_url('ticket_dashboard', 'ticketing'),
        })
        if has_cap('ticketing.manage_settings') or request.user.is_superuser:
            ticketing_items.append({
                'id': 'dash-ticketing-admin',
                'label': 'Ticketing Admin',
                'icon': '⚙️',
                'tabId': 'dash-ticketing-admin',
                'url': get_url('ticketing_admin', 'ticketing'),
            })
        
        sections.append({
            'type': 'divider',
        })
        sections.append({
            'type': 'group',
            'group': {
                'id': 'ticketing',
                'label': 'Ticketing System',
                'icon': '🎫',
                'items': ticketing_items,
            },
        })
    
    # API Section
    try:
        from api.models import APIUser
        api_user = APIUser.objects.filter(user=request.user).first()
        has_api_access = (request.user.is_superuser or 
                         has_cap('core.admin') or 
                         (api_user and api_user.access_level in ['api_only', 'both']))
    except ImportError:
        # APIUser model doesn't exist, only allow superusers and admins
        api_user = None
        has_api_access = (request.user.is_superuser or has_cap('core.admin'))
    
    if has_api_access:
        api_items = []
        if request.user.is_superuser or has_cap('core.admin'):
            api_items.append({
                'id': 'dash-api-config',
                'label': 'API Config',
                'icon': '🔧',
                'tabId': 'dash-api-config',
                'url': get_url('api_config_dashboard', 'api'),
            })
        if api_user and api_user.access_level in ['api_only', 'both']:
            api_items.append({
                'id': 'dash-api-manual',
                'label': 'API Manual',
                'icon': '📖',
                'tabId': 'dash-api-manual',
                'url': get_url('api_manual', 'api'),
            })
        
        if api_items:
            sections.append({
                'type': 'divider',
            })
            sections.append({
                'type': 'group',
                'group': {
                    'id': 'api',
                    'label': 'API',
                    'icon': '🔌',
                    'items': api_items,
                },
            })
    
    # Energy Revenue Hub (feature-based, dropdown group like Ticketing)
    if has_permission('energy_revenue_hub'):
        energy_revenue_items = [
            {
                'id': 'dash-energy-revenue-hub',
                'label': 'Energy Revenue Hub',
                'icon': '💵',
                'tabId': 'dash-energy-revenue-hub',
                'url': get_url('index', 'energy_revenue_hub'),
            },
        ]
        sections.append({
            'type': 'divider',
        })
        sections.append({
            'type': 'group',
            'group': {
                'id': 'energy-revenue-hub',
                'label': 'Energy Revenue Hub',
                'icon': '💵',
                'items': energy_revenue_items,
            },
        })
    
    # Engineering Tools (feature-based, dropdown group like Ticketing)
    if has_permission('engineering_tools'):
        engineering_tools_items = [
            {
                'id': 'dash-engineering-tools',
                'label': 'Engineering Tools',
                'icon': '🔧',
                'tabId': 'dash-engineering-tools',
                'url': get_url('index', 'engineering_tools'),
            },
        ]
        sections.append({
            'type': 'divider',
        })
        sections.append({
            'type': 'group',
            'group': {
                'id': 'engineering-tools',
                'label': 'Engineering Tools',
                'icon': '🔧',
                'items': engineering_tools_items,
            },
        })
    
    # Data Management
    data_items = []
    if has_permission('data_upload') or has_cap('data_upload.manage'):
        data_items.append({
            'id': 'dash-data-upload',
            'label': 'Data Upload',
            'icon': '📤',
            'tabId': 'dash-data-upload',
            'url': get_url('data_upload'),
        })
    if has_permission('data_upload_help') or has_cap('data_upload.manage'):
        data_items.append({
            'id': 'dash-data-upload-help',
            'label': 'Upload Help',
            'icon': '📋',
            'tabId': 'dash-data-upload-help',
            'url': get_url('data_upload_help'),
        })
    if has_cap('site_onboarding.manage'):
        data_items.append({
            'id': 'dash-site-onboarding',
            'label': 'Site Onboarding',
            'icon': '🏗️',
            'tabId': 'dash-site-onboarding',
            'url': get_url('site_onboarding'),
        })
        # Device Onboarding - check if URL exists
        try:
            reverse('main:device_onboarding')
            data_items.append({
                'id': 'dash-device-onboarding',
                'label': 'Device Onboarding',
                'icon': '🔧',
                'tabId': 'dash-device-onboarding',
                'url': get_url('device_onboarding'),
            })
        except:
            # Device onboarding URL doesn't exist, skip it
            pass

    # Background Jobs (superuser-only)
    if request.user.is_superuser:
        data_items.append({
            'id': 'dash-background-jobs',
            'label': 'Background Jobs',
            'icon': '⏱️',
            'tabId': 'dash-background-jobs',
            'url': get_url('background_jobs'),
        })
    
    if data_items:
        if len(data_items) > 1:
            sections.append({
                'type': 'divider',
            })
            sections.append({
                'type': 'group',
                'group': {
                    'id': 'data-management',
                    'label': 'Data Management',
                    'icon': '📁',
                    'items': data_items,
                },
            })
        else:
            sections.append({
                'type': 'divider',
            })
            sections.append({
                'type': 'single',
                'items': data_items,
            })
    
    # User Management
    if has_permission('user_management'):
        sections.append({
            'type': 'divider',
        })
        sections.append({
            'type': 'single',
            'items': [{
                'id': 'dash-user-management',
                'label': 'User Management',
                'icon': '👤',
                'tabId': 'dash-user-management',
                'url': get_url('user_management'),
            }],
        })
    
    # Feedback Section
    feedback_items = []
    if has_permission('feedback_submit'):
        feedback_items.append({
            'id': 'feedback-submit',
            'label': 'Submit Feedback',
            'icon': '💬',
            'url': get_url('feedback_submit'),
            'target': '_blank',
            'rel': 'noopener noreferrer',
        })
    if has_permission('feedback_list'):
        feedback_items.append({
            'id': 'dash-feedback-list',
            'label': 'Manage Feedback',
            'icon': '📋',
            'tabId': 'dash-feedback-list',
            'url': get_url('feedback_list'),
        })
    
    if feedback_items:
        sections.append({
            'type': 'divider',
        })
        sections.append({
            'type': 'sectionTitle',
            'sectionTitle': '💬 Feedback',
        })
        sections.append({
            'type': 'single',
            'items': feedback_items,
        })
    
    # Get user info
    user_info = {
        'username': request.user.username,
        'full_name': request.user.get_full_name() or request.user.username,
        'role': role,
        'is_superuser': request.user.is_superuser,
    }
    
    return JsonResponse({
        'menu': {
            'sections': sections,
        },
        'user': user_info,
        'timestamp': int(timezone.now().timestamp()),
    })
