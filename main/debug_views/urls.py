from django.urls import path
from . import views

app_name = 'debug'

urlpatterns = [
    path('user-access/', views.debug_user_access, name='debug_user_access'),
    path('data-visibility/', views.debug_data_visibility, name='debug_data_visibility'),
    path('api-endpoints/', views.debug_api_endpoints, name='debug_api_endpoints'),
    path('asset-assignment/', views.debug_asset_assignment, name='debug_asset_assignment'),
    path('fix-user-assignments/', views.fix_user_country_assignments, name='fix_user_country_assignments'),
] 