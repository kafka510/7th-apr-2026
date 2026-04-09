"""
Set REMOTE_ADDR from X-Forwarded-For when behind a reverse proxy (e.g. nginx).

When present, the first IP in X-Forwarded-For is the real client; without this
middleware, REMOTE_ADDR would be the proxy IP (e.g. 172.17.0.1). Must run early
in MIDDLEWARE so all code that uses request.META.get('REMOTE_ADDR') sees the
real client IP.
"""


class SetRemoteAddrFromForwardedFor:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # First IP in list is the real client (per proxy chain)
            request.META['REMOTE_ADDR'] = x_forwarded_for.split(',')[0].strip()
        return self.get_response(request)