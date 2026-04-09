"""
Engineering Tools views.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.decorators import feature_required


@login_required
@feature_required('engineering_tools')
def index_view(request):
    """Main Engineering Tools page - React app."""
    return render(request, 'engineering_tools/index_react.html')
