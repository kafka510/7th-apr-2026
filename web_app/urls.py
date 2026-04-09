"""
URL configuration for web_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from main.views.static_file_views import serve_static_file, serve_media_file

urlpatterns = [
    # CRITICAL: Static and media file patterns must come FIRST to override Django's default static file serving
    # Static files: login page assets are public, all others require authentication
    path('static/<path:file_path>', serve_static_file, name='serve_static'),
    # Media files: always require authentication
    path('media/<path:file_path>', serve_media_file, name='serve_media'),
    
    path('admin/', admin.site.urls),
    path('captcha/', include('captcha.urls')),  # django-simple-captcha URLs
    path('', include('main.urls', namespace='main')),
    path('accounts/', include('accounts.urls')),
    # Shared app endpoints (export, etc.) - must come before api.urls to avoid conflicts
    path('api/', include('shared_app.urls', namespace='shared')),
    path('api/', include('api.urls', namespace='api')),  # API endpoints
    path('api/loss/', include('loss_analytics.urls', namespace='loss_analytics')),  # Loss analytics: transpose, task status
    path('api/v1/kpi/', include(('main.api_urls', 'kpi'), namespace='kpi')),
    path('api/v1/yield/', include(('main.api_urls', 'yield'), namespace='yield')),
    path('api/v1/generation/', include(('main.api_urls', 'generation'), namespace='generation')),
    path('api/v1/portfolio-map/', include(('main.api_urls', 'portfolio_map'), namespace='portfolio_map')),
    path('api/v1/sales/', include(('main.api_urls', 'sales'), namespace='sales')),
    path('api/v1/ic-budget/', include(('main.api_urls', 'ic_budget'), namespace='ic_budget')),
    path('api/v1/ticketing/', include(('ticketing.api_urls', 'ticketing_api'), namespace='ticketing_api')),
    path('tickets/', include('ticketing.urls', namespace='ticketing')),  # Ticketing system
    path('energy-revenue-hub/', include('energy_revenue_hub.urls', namespace='energy_revenue_hub')),
    path('engineering-tools/', include('engineering_tools.urls', namespace='engineering_tools')),
    
    # NEW: Standardized APIs for React apps (v2)
    path('api/v2/main/', include(('main.api_v2.routers', 'main_api_v2'), namespace='main_api_v2')),
    
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]
