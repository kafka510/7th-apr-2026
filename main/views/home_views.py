"""
Home and landing page views
"""
from django.shortcuts import render, redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test

from main.permissions import user_has_app_access


def home_view(request):
    """
    Default landing page that redirects users based on authentication status:
    - Logged in users -> Unified Operations Dashboard (all authenticated users)
    - Non-logged in users -> Login page
    
    The unified dashboard sidebar will show only pages the user has access to.
    """
    # Ensure session is saved
    if request.user.is_authenticated:
        # Force session save to ensure CSRF token is properly set
        request.session.save()
        # All authenticated users go to unified dashboard
        # Sidebar will show only accessible pages based on permissions
        return redirect('main:unified_operations_dashboard')
    else:
        return redirect('accounts:login')


@ensure_csrf_cookie
def csrf_test_view(request):
    """Simple view to test CSRF token functionality"""
    if request.method == 'POST':
        return JsonResponse({'status': 'success', 'message': 'CSRF token is working!'})
    return render(request, 'main/csrf_test.html')


@login_required
@user_passes_test(lambda u: u.is_superuser)
@ensure_csrf_cookie
def simple_csrf_test_view(request):
    """
    Simple view to test CSRF functionality.
    Secured: Requires superuser authentication.
    """
    if request.method == 'POST':
        return JsonResponse({'status': 'success', 'message': 'Simple CSRF test working!'})
    return render(request, 'main/simple_csrf_test.html')
