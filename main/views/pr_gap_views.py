"""
PR Gap analysis views
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from waffle import flag_is_active
from accounts.decorators import feature_required


@feature_required('pr_gap')
@login_required
def pr_gap_view(request):
    """PR Gap view with flag-based React/legacy switching"""
    # Check if React version should be used
    if flag_is_active(request, 'react_pr_gap'):
        return render(request, 'main/PR_Gap_react.html')
    
    # Legacy template
    return render(request, 'main/PR_Gap.html')
