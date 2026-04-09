from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.conf import settings


@login_required
def react_demo_view(request):
    return render(
        request,
        'main/react_demo.html',
        {
            'page_title': 'React Demo',
        },
    )
