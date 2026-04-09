from django.http import JsonResponse


class APIAuthEnforcementMiddleware:
    """
    Enforce authenticated sessions for all API endpoints.

    This keeps browser routes on normal redirect behavior while returning JSON for API callers.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or ""
        is_api_path = path.startswith("/api/")

        if is_api_path and not request.user.is_authenticated:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Authentication required. Please log in again.",
                    "auth_required": True,
                },
                status=401,
            )

        return self.get_response(request)

