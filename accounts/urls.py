from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .access_views import (
    CapabilityCreateView,
    CapabilityDeleteView,
    CapabilityListView,
    CapabilityUpdateView,
    FeatureCreateView,
    FeatureDeleteView,
    FeatureListView,
    FeatureUpdateView,
    RoleCreateView,
    RoleDeleteView,
    RoleListView,
    RoleUpdateView,
)

app_name = 'accounts'

urlpatterns = [
    #path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('password-reset/', 
        views.CustomPasswordResetView.as_view(),
        name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url=reverse_lazy('accounts:password_reset_complete')
         ),
         name='password_reset_confirm'),
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ),
         name='password_reset_complete'),

    # Access management
    path("manage/features/", FeatureListView.as_view(), name="feature_list"),
    path("manage/features/new/", FeatureCreateView.as_view(), name="feature_create"),
    path("manage/features/<slug:key>/edit/", FeatureUpdateView.as_view(), name="feature_update"),
    path("manage/features/<slug:key>/delete/", FeatureDeleteView.as_view(), name="feature_delete"),

    path("manage/capabilities/", CapabilityListView.as_view(), name="capability_list"),
    path("manage/capabilities/new/", CapabilityCreateView.as_view(), name="capability_create"),
    path("manage/capabilities/<str:key>/edit/", CapabilityUpdateView.as_view(), name="capability_update"),
    path("manage/capabilities/<str:key>/delete/", CapabilityDeleteView.as_view(), name="capability_delete"),

    path("manage/roles/", RoleListView.as_view(), name="role_list"),
    path("manage/roles/new/", RoleCreateView.as_view(), name="role_create"),
    path("manage/roles/<slug:key>/edit/", RoleUpdateView.as_view(), name="role_update"),
    path("manage/roles/<slug:key>/delete/", RoleDeleteView.as_view(), name="role_delete"),
] 