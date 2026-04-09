"""
Helper functions used across apps.
"""


def parse_list_query_param(request, param_name, separator=','):
    """Parse comma-separated list from query parameter"""
    value = request.query_params.get(param_name, '')
    if not value:
        return []
    return [item.strip() for item in value.split(separator) if item.strip()]


def parse_query_param(request, param_name, default=None):
    """Parse query parameter with default value"""
    value = request.query_params.get(param_name, default)
    if value == '':
        return default
    return value


def format_currency(value, currency='USD'):
    """Format decimal as currency"""
    return f"{currency} {value:,.2f}"


def format_percentage(value):
    """Format decimal as percentage"""
    return f"{value:.2f}%"

