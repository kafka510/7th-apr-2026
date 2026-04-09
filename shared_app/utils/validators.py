"""
Common validators used across apps.
"""


def validate_asset_code(value: str) -> bool:
    """Validate asset code format"""
    if not value or len(value) < 3:
        return False
    return True


def validate_date_format(date_string: str, format: str = '%Y-%m-%d') -> bool:
    """Validate date string format"""
    try:
        from datetime import datetime
        datetime.strptime(date_string, format)
        return True
    except ValueError:
        return False

