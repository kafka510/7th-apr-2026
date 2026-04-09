from django.utils.decorators import method_decorator
from django.views import View

from accounts.decorators import feature_required


class EngineeringToolsProtectedView(View):
    """API views under /engineering-tools/ — require login + engineering_tools feature."""

    @method_decorator(feature_required('engineering_tools'), name='dispatch')
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
